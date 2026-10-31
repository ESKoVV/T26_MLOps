"""LR9: retry policy and idempotency of the Prefect flow."""

import json
from pathlib import Path

import pandas as pd
import pytest
from prefect import flow
from prefect.testing.utilities import prefect_test_harness

from mlops_flight_delay.orchestration import (
    preprocess_stage,
    preprocess_task,
    retry_only_transient,
    training_flow,
)


class _State:
    def __init__(self, error: Exception | None) -> None:
        self.error = error

    def result(self):
        if self.error:
            raise self.error
        return {}


@pytest.mark.parametrize(
    ("error", "expected"),
    [(OSError("disk busy"), True), (ValueError("missing column"), False), (None, False)],
    ids=["oserror-retried", "valueerror-not-retried", "success-not-retried"],
)
def test_retry_condition(error, expected) -> None:
    assert retry_only_transient(None, None, _State(error)) is expected


@pytest.fixture(scope="module", autouse=True)
def prefect_backend():
    with prefect_test_harness():
        yield


def test_deterministic_preprocess_error_is_not_retried(tmp_path: Path, caplog) -> None:
    broken = tmp_path / "broken.csv"
    pd.DataFrame({"FlightDate": ["2026-01-01"], "DepHour": [9]}).to_csv(broken, index=False)

    @flow
    def only_preprocess():
        preprocess_task(
            broken,
            tmp_path / "prepared.csv",
            simulate_transient_failure=False,
            retry_marker=tmp_path / ".retry-once",
        )

    state = only_preprocess(return_state=True)
    assert state.is_failed()
    assert "missing columns" in caplog.text
    assert "Retry 1/2" not in caplog.text


def test_transient_failure_is_retried_and_flow_completes(
    sample_data_path: Path, contract_path: Path, tmp_path: Path
) -> None:
    run_dir = tmp_path / "retry"
    summary = training_flow(
        sample_data_path,
        contract_path,
        run_dir,
        tmp_path / "model.joblib",
        minimum_roc_auc=0.0,
        simulate_transient_failure=True,
    )
    assert (run_dir / ".retry-once").exists()
    assert summary["passed"] is True


def test_preprocess_is_idempotent(sample_data_path: Path, tmp_path: Path) -> None:
    first = preprocess_stage(sample_data_path, tmp_path / "a.csv")
    second = preprocess_stage(sample_data_path, tmp_path / "b.csv")
    assert first["sha256"] == second["sha256"]
    assert first["rows"] == second["rows"]


def test_summary_links_inputs_and_metrics(
    sample_data_path: Path, contract_path: Path, tmp_path: Path
) -> None:
    run_dir = tmp_path / "ok"
    training_flow(
        sample_data_path, contract_path, run_dir, tmp_path / "m.joblib", minimum_roc_auc=0.0
    )
    summary = json.loads((run_dir / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["stages"] == ["validate", "preprocess", "train", "evaluate"]
    reports = sorted(path.name for path in run_dir.glob("0*.json"))
    assert reports == [
        "01-validation.json",
        "02-preprocess.json",
        "03-training.json",
        "04-evaluation.json",
    ]
