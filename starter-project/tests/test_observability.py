import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from mlops_flight_delay.api import create_app
from mlops_flight_delay.train import train_model


def _client(tmp_path: Path) -> TestClient:
    data = Path(__file__).parents[1] / "data" / "flights_sample.csv"
    model_path = tmp_path / "model.joblib"
    train_model(data, model_path)
    return TestClient(create_app(model_path))


def test_metrics_expose_bounded_route_status_and_model_identity(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            "/predict",
            json={"dep_hour": 9, "is_weekend": 0},
            headers={"X-Request-ID": "lr11-metrics-test"},
        )
        assert response.status_code == 200
        metrics = client.get("/metrics").text

    assert 'http_requests_total{method="POST",route="/predict",status="200"}' in metrics
    bucket = (
        'http_request_duration_seconds_bucket{le="0.5",method="POST",route="/predict"}'
    )
    assert bucket in metrics
    assert 'model_info{model_name="flight-delay-classifier",model_version="0.2.0"' in metrics
    assert "lr11-metrics-test" not in metrics


def test_structured_log_correlates_request_without_payload(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.INFO, logger="mlops_flight_delay.observability")
    with _client(tmp_path) as client:
        response = client.post(
            "/predict",
            json={"dep_hour": 7, "is_weekend": 1},
            headers={"X-Request-ID": "lr11-log-test"},
        )
    assert response.status_code == 200
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.message.startswith("{")
    ]
    event = next(record for record in records if record["request_id"] == "lr11-log-test")
    assert event["route"] == "/predict"
    assert event["status"] == 200
    assert event["model_version"] == "0.2.0"
    assert "dep_hour" not in event
    assert "is_weekend" not in event


def test_validation_failure_has_bounded_route_label(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/predict", json={"dep_hour": 99, "is_weekend": 0})
        metrics = client.get("/metrics").text
    assert response.status_code == 422
    assert 'http_requests_total{method="POST",route="/predict",status="422"}' in metrics

