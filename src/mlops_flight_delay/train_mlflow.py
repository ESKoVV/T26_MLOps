from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import joblib
import mlflow
import mlflow.data
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from mlops_flight_delay.split import SPLIT_POLICY, chronological_bounds, sort_by_event_time
from mlops_flight_delay.train import FEATURES, train_model
from mlops_flight_delay.validate_data import validate_dataset


def _git(args: list[str], default: str = "unknown") -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return default


def _dvc_hash(data_path: Path) -> str:
    metafile = data_path.with_suffix(data_path.suffix + ".dvc")
    if not metafile.exists():
        return "not-tracked"
    for line in metafile.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("md5:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def run_experiment(
    data_path: Path,
    contract_path: Path,
    experiment: str,
    n_estimators: int,
    max_depth: int,
    random_state: int,
    *,
    team_code: str = "team-3",
    hypothesis: str = "",
) -> str:
    validation = validate_dataset(data_path, contract_path)
    if not validation["passed"]:
        raise ValueError("Набор не прошёл контракт данных")

    frame = sort_by_event_time(pd.read_csv(data_path))
    train_end, validation_end = chronological_bounds(frame["FlightDate"])
    train_frame = frame.iloc[:train_end].copy()
    validation_frame = frame.iloc[train_end:validation_end].copy()
    validation_target = (validation_frame["ArrDelay"] >= 15).astype(int)
    if validation_target.nunique() < 2:
        raise ValueError("Validation-период должен содержать оба класса")

    mlflow.set_experiment(experiment)
    with tempfile.TemporaryDirectory(prefix="mlops-lr4-") as temp_dir:
        temp = Path(temp_dir)
        model_path = temp / "model.joblib"
        train_model(
            data_path,
            model_path,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
        )
        bundle = joblib.load(model_path)
        probabilities = bundle["model"].predict_proba(validation_frame[FEATURES])[:, 1]
        predictions = (probabilities >= 0.5).astype(int)
        metrics = {
            "validation_roc_auc": float(roc_auc_score(validation_target, probabilities)),
            "validation_precision": float(
                precision_score(validation_target, predictions, zero_division=0)
            ),
            "validation_recall": float(
                recall_score(validation_target, predictions, zero_division=0)
            ),
            "validation_f1": float(f1_score(validation_target, predictions, zero_division=0)),
        }
        split_manifest = {
            "policy": SPLIT_POLICY,
            "rows": len(frame),
            "train_rows": train_end,
            "validation_rows": validation_end - train_end,
            "test_rows": len(frame) - validation_end,
            "train_end": str(frame.iloc[train_end - 1]["FlightDate"].date()),
            "validation_end": str(frame.iloc[validation_end - 1]["FlightDate"].date()),
            "test_end": str(frame.iloc[-1]["FlightDate"].date()),
        }
        run_name = f"rf-depth-{max_depth}-n{n_estimators}"
        summary_path = temp / "run_summary.md"
        summary_path.write_text(
            "\n".join(
                [
                    f"# {run_name}",
                    "",
                    f"- data: `{data_path.as_posix()}`, rows {len(frame)}",
                    (
                        f"- split: {split_manifest['train_end']} | "
                        f"{split_manifest['validation_end']} | {split_manifest['test_end']}"
                        f" ({SPLIT_POLICY})"
                    ),
                    f"- validation ROC AUC: {metrics['validation_roc_auc']:.4f}",
                    f"- validation F1: {metrics['validation_f1']:.4f}",
                    "",
                    f"Гипотеза: {hypothesis or 'не указана'}",
                    "",
                    "Test-период в этом run не используется.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        split_path = temp / "split_manifest.json"
        metrics_path = temp / "metrics.json"
        validation_path = temp / "validation_report.json"
        split_path.write_text(
            json.dumps(split_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        validation_path.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        training_input = mlflow.data.from_pandas(
            train_frame.assign(target=(train_frame["ArrDelay"] >= 15).astype(int)),
            source=data_path.as_posix(),
            name="flight-delay-train",
            targets="target",
        )
        validation_input = mlflow.data.from_pandas(
            validation_frame.assign(target=validation_target),
            source=data_path.as_posix(),
            name="flight-delay-validation",
            targets="target",
        )

        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(
                {
                    "algorithm": "RandomForestClassifier",
                    "n_estimators": n_estimators,
                    "max_depth": max_depth,
                    "random_state": random_state,
                    "target_threshold_minutes": 15,
                    "split_policy": SPLIT_POLICY,
                }
            )
            mlflow.log_metrics(metrics)
            mlflow.log_input(training_input, context="training")
            mlflow.log_input(validation_input, context="validation")
            mlflow.set_tags(
                {
                    "git.commit": _git(["rev-parse", "HEAD"]),
                    "git.dirty": str(bool(_git(["status", "--porcelain"], ""))).lower(),
                    "data.dvc_hash": _dvc_hash(data_path),
                    "data.sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
                    "data.contract_version": validation["contract_version"],
                    "split.policy": SPLIT_POLICY,
                    "validation.status": "candidate",
                    "team.code": team_code,
                }
            )
            mlflow.log_artifact(str(model_path), artifact_path="model")
            mlflow.log_artifact(str(split_path), artifact_path="reports")
            mlflow.log_artifact(str(metrics_path), artifact_path="reports")
            mlflow.log_artifact(str(validation_path), artifact_path="reports")
            mlflow.log_artifact(str(summary_path), artifact_path="reports")
            lock = Path("requirements.lock")
            if lock.exists():
                mlflow.log_artifact(str(lock), artifact_path="environment")
            return run.info.run_id


def main() -> None:
    parser = argparse.ArgumentParser(description="MLflow Tracking для учебного проекта")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--n-estimators", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--team-code", default="team-3")
    parser.add_argument("--hypothesis", default="")
    args = parser.parse_args()
    run_id = run_experiment(
        args.data,
        args.contract,
        args.experiment,
        args.n_estimators,
        args.max_depth,
        args.random_state,
        team_code=args.team_code,
        hypothesis=args.hypothesis,
    )
    print(f"MLflow run_id: {run_id}")


if __name__ == "__main__":
    main()
