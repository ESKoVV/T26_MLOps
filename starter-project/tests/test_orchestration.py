from pathlib import Path

import joblib
import pytest

from mlops_flight_delay.orchestration import (
    evaluate_stage,
    preprocess_stage,
    preprocess_task,
    train_stage,
    validate_stage,
)


def test_orchestration_stages_create_traceable_artifacts(
    sample_data_path: Path,
    contract_path: Path,
    tmp_path: Path,
) -> None:
    validation_path = tmp_path / "01-validation.json"
    prepared_path = tmp_path / "prepared.csv"
    model_path = tmp_path / "model.joblib"
    training_path = tmp_path / "03-training.json"
    evaluation_path = tmp_path / "04-evaluation.json"

    validation = validate_stage(sample_data_path, contract_path, validation_path)
    prepared = preprocess_stage(sample_data_path, prepared_path)
    training = train_stage(
        prepared_path,
        model_path,
        n_estimators=20,
        max_depth=3,
        random_state=17,
        report_path=training_path,
    )
    evaluation = evaluate_stage(
        prepared_path,
        model_path,
        evaluation_path,
        threshold=0.5,
        minimum_roc_auc=0.5,
    )

    assert validation["passed"] is True
    assert prepared["rows"] == validation["rows"]
    assert training["model_path"] == model_path.as_posix()
    assert evaluation["passed"] is True
    assert set(evaluation["metrics"]) == {"roc_auc", "precision", "recall", "f1"}
    artifacts = (validation_path, prepared_path, training_path, evaluation_path)
    assert all(path.is_file() for path in artifacts)
    assert joblib.load(model_path)["parameters"]["random_state"] == 17


def test_evaluation_gate_writes_report_before_failure(
    sample_data_path: Path,
    tmp_path: Path,
) -> None:
    prepared_path = tmp_path / "prepared.csv"
    model_path = tmp_path / "model.joblib"
    report_path = tmp_path / "failed-evaluation.json"
    preprocess_stage(sample_data_path, prepared_path)
    train_stage(
        prepared_path,
        model_path,
        n_estimators=20,
        max_depth=3,
        random_state=17,
        report_path=tmp_path / "training.json",
    )

    with pytest.raises(ValueError, match="Quality gate failed"):
        evaluate_stage(
            prepared_path,
            model_path,
            report_path,
            threshold=0.5,
            minimum_roc_auc=1.1,
        )

    assert report_path.is_file()
    assert preprocess_task.retries == 2
