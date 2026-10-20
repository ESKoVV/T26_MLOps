from pathlib import Path

import joblib

from mlops_flight_delay.train import train_model


def test_train_creates_versioned_bundle(tmp_path: Path) -> None:
    data = Path(__file__).parents[1] / "data" / "flights_sample.csv"
    model_path = tmp_path / "model.joblib"
    score = train_model(data, model_path)
    bundle = joblib.load(model_path)
    assert 0.0 <= score <= 1.0
    assert bundle["features"] == ["DepHour", "IsWeekend"]
    assert bundle["version"] == "0.2.0"
    assert bundle["split"] == {"train_end": 14, "validation_end": 19}
    assert 0.0 <= bundle["validation_roc_auc"] <= 1.0
    assert set(bundle["validation_metrics"]) == {"roc_auc", "precision", "recall", "f1"}
    assert bundle["validation_roc_auc"] == bundle["validation_metrics"]["roc_auc"]
    assert bundle["parameters"] == {
        "n_estimators": 80,
        "max_depth": 4,
        "random_state": 42,
    }

