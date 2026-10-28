from pathlib import Path

import mlflow
import pytest

from mlops_flight_delay.train_mlflow import run_experiment

ROOT = Path(__file__).parents[1]

REQUIRED_TAGS = {
    "git.commit",
    "git.dirty",
    "data.dvc_hash",
    "data.sha256",
    "data.contract_version",
    "split.policy",
    "team.code",
    "validation.status",
}


@pytest.fixture
def tracking(tmp_path: Path):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    yield
    mlflow.set_tracking_uri(None)


def test_run_has_course_tags_and_artifacts(tracking, contract_path: Path) -> None:
    run_id = run_experiment(
        ROOT / "data" / "flights_sample.csv",
        contract_path,
        "test-flight-delay",
        n_estimators=10,
        max_depth=2,
        random_state=1,
        hypothesis="smoke",
    )
    run = mlflow.get_run(run_id)
    assert run.info.status == "FINISHED"
    assert REQUIRED_TAGS <= set(run.data.tags)
    assert run.data.tags["team.code"] == "team-3"
    assert run.data.params["max_depth"] == "2"
    assert 0.0 <= run.data.metrics["validation_roc_auc"] <= 1.0
    artifacts = {item.path for item in mlflow.MlflowClient().list_artifacts(run_id, "reports")}
    assert {
        "reports/run_summary.md",
        "reports/split_manifest.json",
        "reports/metrics.json",
    } <= artifacts


def test_contract_violation_stops_run(tracking, tmp_path: Path, contract_path: Path) -> None:
    broken = tmp_path / "broken.csv"
    broken.write_text("FlightDate,DepHour\n2026-01-01,25\n", encoding="utf-8")
    with pytest.raises(ValueError, match="контракт"):
        run_experiment(broken, contract_path, "test-flight-delay", 10, 2, 1)
