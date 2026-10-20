from pathlib import Path

import joblib
import pytest

from mlops_flight_delay.train import train_model


def test_training_pipeline_smoke(sample_data_path: Path, model_path: Path) -> None:
    score = train_model(sample_data_path, model_path)
    bundle = joblib.load(model_path)

    assert model_path.is_file()
    assert score == pytest.approx(bundle["validation_metrics"]["roc_auc"])
    assert set(bundle["validation_metrics"]) == {"roc_auc", "precision", "recall", "f1"}


def test_training_is_deterministic(sample_data_path: Path, tmp_path: Path) -> None:
    first_path = tmp_path / "first.joblib"
    second_path = tmp_path / "second.joblib"

    first_score = train_model(sample_data_path, first_path, random_state=17)
    second_score = train_model(sample_data_path, second_path, random_state=17)
    first = joblib.load(first_path)
    second = joblib.load(second_path)

    assert first_score == pytest.approx(second_score)
    assert first["validation_metrics"] == pytest.approx(second["validation_metrics"])
    assert first["model"].predict_proba([[9, 0]]) == pytest.approx(
        second["model"].predict_proba([[9, 0]])
    )
