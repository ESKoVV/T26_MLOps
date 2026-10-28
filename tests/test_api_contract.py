"""LR7 contract: request ID, error format for 404/422/500, OpenAPI references, docs."""

from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

from mlops_flight_delay.api import create_app
from mlops_flight_delay.train import train_model


@pytest.fixture
def client(sample_data_path: Path, model_path: Path):
    train_model(sample_data_path, model_path)
    with TestClient(create_app(model_path)) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("payload", "location"),
    [
        ({"dep_hour": 24, "is_weekend": 0}, ["body", "dep_hour"]),
        ({"dep_hour": -1, "is_weekend": 0}, ["body", "dep_hour"]),
        ({"dep_hour": 9, "is_weekend": 2}, ["body", "is_weekend"]),
        ({"dep_hour": 9.5, "is_weekend": 0}, ["body", "dep_hour"]),
        ({"dep_hour": 9, "is_weekend": 0, "arr_delay": 30}, ["body", "arr_delay"]),
    ],
    ids=["hour-24", "hour-negative", "weekend-2", "hour-float", "future-field-arr-delay"],
)
def test_invalid_request_returns_error_response(client, payload, location) -> None:
    response = client.post("/predict", json=payload, headers={"X-Request-ID": "case-1"})
    body = response.json()
    assert response.status_code == 422
    assert body["error_code"] == "validation_error"
    assert body["request_id"] == "case-1" == response.headers["X-Request-ID"]
    assert any(item["location"] == location for item in body["details"])


@pytest.mark.parametrize(
    "header",
    ["", "x" * 129, "id with spaces", "a\tb", "user@example.com"],
    ids=["empty", "too-long", "spaces", "tab", "email-like"],
)
def test_unsafe_request_id_is_replaced_by_uuid(client, header: str) -> None:
    response = client.post(
        "/predict", json={"dep_hour": 9, "is_weekend": 0}, headers={"X-Request-ID": header}
    )
    request_id = response.headers["X-Request-ID"]
    assert request_id != header
    assert len(request_id) == 36  # uuid4
    assert response.json()["request_id"] == request_id


def test_unknown_endpoint_returns_404_error_response(client) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error_code"] == "http_error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


class BrokenModel:
    def predict_proba(self, frame):
        raise RuntimeError("secret internal detail /home/user/model")


def test_internal_error_returns_500_without_stack_trace(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(
        {"model": BrokenModel(), "features": ["DepHour", "IsWeekend"], "version": "x"}, model_path
    )
    with TestClient(create_app(model_path), raise_server_exceptions=False) as client:
        response = client.post(
            "/predict", json={"dep_hour": 9, "is_weekend": 0}, headers={"X-Request-ID": "boom-1"}
        )
    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "internal_error"
    assert body["request_id"] == "boom-1" == response.headers["X-Request-ID"]
    assert "secret" not in response.text and "Traceback" not in response.text


def test_openapi_references_response_and_error_models(client) -> None:
    schema = client.get("/openapi.json").json()
    responses = schema["paths"]["/predict"]["post"]["responses"]
    ref = lambda code: responses[code]["content"]["application/json"]["schema"]["$ref"]
    assert ref("200").endswith("/PredictionResponse")
    assert ref("422").endswith("/ErrorResponse")
    assert ref("503").endswith("/ErrorResponse")
    body = schema["paths"]["/predict"]["post"]["requestBody"]["content"]["application/json"]
    assert body["schema"]["$ref"].endswith("/PredictionRequest")


def test_docs_and_health_do_not_need_prediction(client) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
