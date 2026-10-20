from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

LOGGER = logging.getLogger("mlops_flight_delay.observability")
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests processed by the service",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
PREDICTIONS = Counter(
    "prediction_outcomes_total",
    "Prediction outcomes produced by the model",
    ["outcome", "model_version"],
)
MODEL_INFO = Gauge(
    "model_info",
    "Resolved model identity",
    ["model_name", "model_version", "source_commit"],
)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={"examples": [{"dep_hour": 9, "is_weekend": 0}]},
    )

    dep_hour: int = Field(ge=0, le=23)
    is_weekend: int = Field(ge=0, le=1)


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delay_probability: float
    delayed: bool
    threshold: float
    model_version: str
    request_id: str


class StatusResponse(BaseModel):
    status: str


class ErrorItem(BaseModel):
    location: list[str | int]
    message: str
    error_type: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    request_id: str
    details: list[ErrorItem] = Field(default_factory=list)


def error_payload(
    request: Request,
    *,
    error_code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return ErrorResponse(
        error_code=error_code,
        message=message,
        request_id=request.state.request_id,
        details=[
            ErrorItem(
                location=list(item.get("loc", [])),
                message=str(item.get("msg", "Ошибка валидации")),
                error_type=str(item.get("type", "validation_error")),
            )
            for item in (details or [])
        ],
    ).model_dump()


def create_app(model_path: Path | None = None) -> FastAPI:
    resolved_path = model_path or Path(os.getenv("MODEL_PATH", "models/model.joblib"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.model_bundle = None
        if resolved_path.exists():
            app.state.model_bundle = joblib.load(resolved_path)
        bundle = app.state.model_bundle or {}
        app.state.model_metadata = {
            "model_name": os.getenv("MODEL_NAME", "flight-delay-classifier"),
            "model_version": os.getenv(
                "MODEL_VERSION", str(bundle.get("version", "unavailable"))
            ),
            "source_commit": os.getenv("SOURCE_COMMIT", "unknown"),
        }
        MODEL_INFO.labels(**app.state.model_metadata).set(1)
        yield

    api = FastAPI(
        title="Flight Delay Predictor",
        version="1.1.0",
        description=(
            "Учебный API прогноза задержки рейса не менее чем на 15 минут "
            "за 60 минут до планового отправления."
        ),
        lifespan=lifespan,
    )

    @api.middleware("http")
    async def observability_middleware(request: Request, call_next):
        started = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id or len(request_id) > 128:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        status = 500
        response = None
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            route_object = request.scope.get("route")
            route = getattr(route_object, "path", "unmatched")
            HTTP_REQUESTS.labels(
                method=request.method,
                route=route,
                status=str(status),
            ).inc()
            HTTP_LATENCY.labels(method=request.method, route=route).observe(elapsed)
            metadata = getattr(api.state, "model_metadata", {})
            LOGGER.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "route": route,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 3),
                        "model_name": metadata.get("model_name", "unknown"),
                        "model_version": metadata.get("model_version", "unknown"),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )

    @api.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                request,
                error_code="validation_error",
                message="Запрос не соответствует контракту",
                details=exception.errors(),
            ),
        )

    @api.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exception: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exception.status_code,
            content=error_payload(
                request,
                error_code="not_ready" if exception.status_code == 503 else "http_error",
                message=str(exception.detail),
            ),
            headers=exception.headers,
        )

    @api.get("/healthz", response_model=StatusResponse, tags=["service"])
    def health() -> StatusResponse:
        return StatusResponse(status="ok")

    @api.get(
        "/readyz",
        response_model=StatusResponse,
        responses={503: {"model": ErrorResponse}},
        tags=["service"],
    )
    def ready() -> StatusResponse:
        if api.state.model_bundle is None:
            raise HTTPException(status_code=503, detail="Модель не загружена")
        return StatusResponse(status="ready")

    @api.post(
        "/predict",
        response_model=PredictionResponse,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
        tags=["prediction"],
        summary="Получить вероятность задержки рейса",
    )
    def predict(payload: PredictionRequest, request: Request) -> PredictionResponse:
        bundle = api.state.model_bundle
        if bundle is None:
            PREDICTIONS.labels(outcome="not_ready", model_version="unavailable").inc()
            raise HTTPException(status_code=503, detail="Модель не загружена")
        try:
            frame = pd.DataFrame(
                [{"DepHour": payload.dep_hour, "IsWeekend": payload.is_weekend}]
            )
            probability = float(bundle["model"].predict_proba(frame[bundle["features"]])[:, 1][0])
            threshold = 0.5
            model_version = api.state.model_metadata["model_version"]
            PREDICTIONS.labels(
                outcome="delayed" if probability >= threshold else "on_time",
                model_version=model_version,
            ).inc()
            return PredictionResponse(
                delay_probability=probability,
                delayed=probability >= threshold,
                threshold=threshold,
                model_version=model_version,
                request_id=request.state.request_id,
            )
        except Exception:
            PREDICTIONS.labels(
                outcome="error",
                model_version=api.state.model_metadata["model_version"],
            ).inc()
            raise

    @api.get("/metrics", tags=["service"])
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return api


app = create_app()
