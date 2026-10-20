from pathlib import Path

from fastapi.testclient import TestClient

from mlops_flight_delay.api import create_app
from mlops_flight_delay.train import train_model


def client_with_model(tmp_path: Path) -> TestClient:
    data = Path(__file__).parents[1] / "data" / "flights_sample.csv"
    model_path = tmp_path / "model.joblib"
    train_model(data, model_path)
    return TestClient(create_app(model_path))


def test_predict_contract(tmp_path: Path) -> None:
    with client_with_model(tmp_path) as client:
        response = client.post(
            "/predict",
            json={"dep_hour": 9, "is_weekend": 0},
            headers={"X-Request-ID": "lr7-contract-test"},
        )
        assert response.status_code == 200
        body = response.json()
        assert 0.0 <= body["delay_probability"] <= 1.0
        assert body["delayed"] is (body["delay_probability"] >= body["threshold"])
        assert body["threshold"] == 0.5
        assert body["model_version"] == "0.2.0"
        assert body["request_id"] == "lr7-contract-test"
        assert response.headers["X-Request-ID"] == "lr7-contract-test"


def test_predict_rejects_invalid_hour(tmp_path: Path) -> None:
    with client_with_model(tmp_path) as client:
        response = client.post("/predict", json={"dep_hour": 25, "is_weekend": 0})
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "validation_error"
        assert body["request_id"] == response.headers["X-Request-ID"]
        assert body["details"]


def test_predict_rejects_unknown_field(tmp_path: Path) -> None:
    with client_with_model(tmp_path) as client:
        response = client.post(
            "/predict",
            json={"dep_hour": 9, "is_weekend": 0, "actual_delay": 42},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "validation_error"


def test_predict_rejects_missing_required_field(tmp_path: Path) -> None:
    with client_with_model(tmp_path) as client:
        response = client.post("/predict", json={"dep_hour": 9})
        assert response.status_code == 422
        assert response.json()["error_code"] == "validation_error"


def test_predict_rejects_implicit_type_conversion(tmp_path: Path) -> None:
    with client_with_model(tmp_path) as client:
        response = client.post("/predict", json={"dep_hour": "9", "is_weekend": 0})
        assert response.status_code == 422


def test_not_ready_without_model(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "missing.joblib")) as client:
        assert client.get("/readyz").status_code == 503
        response = client.post("/predict", json={"dep_hour": 9, "is_weekend": 0})
        assert response.status_code == 503
        assert response.json()["error_code"] == "not_ready"
        assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_openapi_documents_request_response_and_errors(tmp_path: Path) -> None:
    with client_with_model(tmp_path) as client:
        schema = client.get("/openapi.json").json()

    request_schema = schema["components"]["schemas"]["PredictionRequest"]
    operation = schema["paths"]["/predict"]["post"]
    assert schema["info"]["version"] == "1.1.0"
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {"dep_hour", "is_weekend"}
    assert operation["responses"]["200"]["content"]["application/json"]
    assert operation["responses"]["422"]["content"]["application/json"]
    assert operation["responses"]["503"]["content"]["application/json"]

