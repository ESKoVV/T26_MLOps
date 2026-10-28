"""Model layer and integration: target, bundle invariants, validate -> train -> load -> predict."""

from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from mlops_flight_delay.api import create_app
from mlops_flight_delay.train import FEATURES, delay_target, train_model
from mlops_flight_delay.validate_data import validate_dataset


def test_delay_of_exactly_15_minutes_is_positive() -> None:
    target = delay_target(pd.Series([-5, 14, 15, 16, 300]))
    assert target.tolist() == [0, 0, 1, 1, 1]


def test_bundle_predicts_one_row_with_two_class_probabilities(
    sample_data_path: Path, model_path: Path
) -> None:
    train_model(sample_data_path, model_path, random_state=7)
    bundle = joblib.load(model_path)

    assert bundle["features"] == FEATURES == ["DepHour", "IsWeekend"]
    assert bundle["parameters"]["random_state"] == 7
    assert bundle["split"]["train_end"] < bundle["split"]["validation_end"]
    probabilities = bundle["model"].predict_proba(
        pd.DataFrame([{"DepHour": 9, "IsWeekend": 0}])[bundle["features"]]
    )
    assert probabilities.shape == (1, 2)
    assert 0.0 <= probabilities[0, 1] <= 1.0
    assert probabilities[0].sum() == pytest.approx(1.0)


def test_api_reports_the_bundle_version(sample_data_path: Path, model_path: Path) -> None:
    train_model(sample_data_path, model_path)
    bundle = joblib.load(model_path)
    with TestClient(create_app(model_path)) as client:
        body = client.post("/predict", json={"dep_hour": 9, "is_weekend": 0}).json()
    assert body["model_version"] == bundle["version"]


def test_validate_train_load_predict(
    valid_frame: pd.DataFrame, csv_factory, contract_path: Path, model_path: Path
) -> None:
    data_path = csv_factory(valid_frame, "flights.csv")
    assert validate_dataset(data_path, contract_path)["passed"] is True

    train_model(data_path, model_path)
    bundle = joblib.load(model_path)
    rows = valid_frame.tail(3)[bundle["features"]]
    probabilities = bundle["model"].predict_proba(rows)[:, 1]

    assert probabilities.shape == (3,)
    assert ((probabilities >= 0.0) & (probabilities <= 1.0)).all()
    assert model_path.parent == csv_factory(valid_frame).parent  # artifacts stay in tmp_path


@pytest.mark.parametrize(
    "content",
    [b"not a joblib file", b""],
    ids=["garbage-bytes", "empty-file"],
)
def test_damaged_model_file_keeps_service_not_ready(tmp_path: Path, content: bytes) -> None:
    damaged = tmp_path / "model.joblib"
    damaged.write_bytes(content)
    with TestClient(create_app(damaged)) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 503
        response = client.post("/predict", json={"dep_hour": 9, "is_weekend": 0})
    assert response.status_code == 503
    assert response.json()["error_code"] == "not_ready"


def test_bundle_without_version_is_rejected(tmp_path: Path) -> None:
    incomplete = tmp_path / "model.joblib"
    joblib.dump({"model": object(), "features": FEATURES}, incomplete)
    with TestClient(create_app(incomplete)) as client:
        assert client.get("/readyz").status_code == 503
