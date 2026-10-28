from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from prefect import flow, get_run_logger, task

from mlops_flight_delay.evaluate import classification_metrics
from mlops_flight_delay.split import sort_by_event_time
from mlops_flight_delay.train import FEATURES, delay_target, train_model
from mlops_flight_delay.validate_data import validate_dataset


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_stage(data_path: Path, contract_path: Path, report_path: Path) -> dict[str, Any]:
    result = validate_dataset(data_path, contract_path)
    _write_json(report_path, result)
    if not result["passed"]:
        raise ValueError(f"Data contract failed; see {report_path}")
    return result


def preprocess_stage(data_path: Path, output_path: Path) -> dict[str, Any]:
    data = pd.read_csv(data_path)
    required = set(FEATURES + ["FlightDate", "ArrDelay"])
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Preprocess input is missing columns: {missing}")
    data = sort_by_event_time(data)
    if data[list(required)].isna().any().any():
        raise ValueError("Preprocess input contains nulls in required columns")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return {
        "path": output_path.as_posix(),
        "rows": len(data),
        "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }


def train_stage(
    data_path: Path,
    model_path: Path,
    *,
    n_estimators: int,
    max_depth: int,
    random_state: int,
    report_path: Path,
) -> dict[str, Any]:
    validation_roc_auc = train_model(
        data_path,
        model_path,
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
    )
    result = {
        "model_path": model_path.as_posix(),
        "validation_roc_auc": validation_roc_auc,
        "parameters": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "random_state": random_state,
        },
    }
    _write_json(report_path, result)
    return result


def evaluate_stage(
    data_path: Path,
    model_path: Path,
    report_path: Path,
    *,
    threshold: float,
    minimum_roc_auc: float,
) -> dict[str, Any]:
    bundle = joblib.load(model_path)
    data = pd.read_csv(data_path)
    split = bundle["split"]
    test = data.iloc[int(split["validation_end"]) :]
    y_test = delay_target(test["ArrDelay"]).to_numpy()
    probabilities = bundle["model"].predict_proba(test[bundle["features"]])[:, 1]
    metrics = classification_metrics(y_test, probabilities, threshold=threshold)
    result = {
        "model_path": model_path.as_posix(),
        "rows": len(test),
        "threshold": threshold,
        "minimum_roc_auc": minimum_roc_auc,
        "metrics": metrics,
        "passed": metrics["roc_auc"] >= minimum_roc_auc,
    }
    _write_json(report_path, result)
    if not result["passed"]:
        raise ValueError(
            f"Quality gate failed: test ROC AUC {metrics['roc_auc']:.3f} "
            f"< {minimum_roc_auc:.3f}; see {report_path}"
        )
    return result


@task(name="validate", retries=0)
def validate_task(data_path: Path, contract_path: Path, report_path: Path) -> dict[str, Any]:
    result = validate_stage(data_path, contract_path, report_path)
    get_run_logger().info("Data contract passed for %s rows", result["rows"])
    return result


def retry_only_transient(task, task_run, state) -> bool:
    """Retry an I/O hiccup (OSError); never retry a deterministic error such as ValueError."""
    try:
        state.result()
    except OSError:
        return True
    except Exception:  # noqa: BLE001 - any other failure is deterministic here
        return False
    return False


@task(
    name="preprocess",
    retries=2,
    retry_delay_seconds=1,
    retry_condition_fn=retry_only_transient,
)
def preprocess_task(
    data_path: Path,
    output_path: Path,
    *,
    simulate_transient_failure: bool,
    retry_marker: Path,
) -> dict[str, Any]:
    if simulate_transient_failure and not retry_marker.exists():
        retry_marker.parent.mkdir(parents=True, exist_ok=True)
        retry_marker.write_text("first attempt failed as designed\n", encoding="utf-8")
        raise OSError("Controlled transient input failure for retry demonstration")
    result = preprocess_stage(data_path, output_path)
    get_run_logger().info("Prepared %s rows; sha256=%s", result["rows"], result["sha256"])
    return result


@task(name="train", retries=0)
def train_task(
    data_path: Path,
    model_path: Path,
    *,
    n_estimators: int,
    max_depth: int,
    random_state: int,
    report_path: Path,
) -> dict[str, Any]:
    result = train_stage(
        data_path,
        model_path,
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        report_path=report_path,
    )
    get_run_logger().info("Model trained; validation ROC AUC=%.3f", result["validation_roc_auc"])
    return result


@task(name="evaluate", retries=0)
def evaluate_task(
    data_path: Path,
    model_path: Path,
    report_path: Path,
    *,
    threshold: float,
    minimum_roc_auc: float,
) -> dict[str, Any]:
    result = evaluate_stage(
        data_path,
        model_path,
        report_path,
        threshold=threshold,
        minimum_roc_auc=minimum_roc_auc,
    )
    get_run_logger().info("Test ROC AUC=%.3f", result["metrics"]["roc_auc"])
    return result


@flow(
    name="flight-delay-training",
    flow_run_name="flight-delay-rs-{random_state}",
    log_prints=True,
    retries=0,
)
def training_flow(
    data_path: Path,
    contract_path: Path,
    run_dir: Path,
    model_path: Path,
    *,
    n_estimators: int = 80,
    max_depth: int = 4,
    random_state: int = 42,
    threshold: float = 0.5,
    minimum_roc_auc: float = 0.5,
    simulate_transient_failure: bool = False,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    validation = validate_task(data_path, contract_path, run_dir / "01-validation.json")
    prepared_path = run_dir / "prepared.csv"
    prepared = preprocess_task(
        data_path,
        prepared_path,
        simulate_transient_failure=simulate_transient_failure,
        retry_marker=run_dir / ".retry-once",
    )
    _write_json(run_dir / "02-preprocess.json", prepared)
    training = train_task(
        prepared_path,
        model_path,
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        report_path=run_dir / "03-training.json",
    )
    evaluation = evaluate_task(
        prepared_path,
        model_path,
        run_dir / "04-evaluation.json",
        threshold=threshold,
        minimum_roc_auc=minimum_roc_auc,
    )
    summary = {
        "flow": "flight-delay-training",
        "stages": ["validate", "preprocess", "train", "evaluate"],
        "data_sha256": validation["sha256"],
        "prepared_sha256": prepared["sha256"],
        "model_path": training["model_path"],
        "parameters": training["parameters"],
        "metrics": evaluation["metrics"],
        "passed": True,
    }
    _write_json(run_dir / "run-summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prefect flow обучения модели задержки рейса")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--n-estimators", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--minimum-roc-auc", type=float, default=0.5)
    parser.add_argument("--simulate-transient-failure", action="store_true")
    args = parser.parse_args()
    result = training_flow(
        data_path=args.data,
        contract_path=args.contract,
        run_dir=args.run_dir,
        model_path=args.model,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.random_state,
        threshold=args.threshold,
        minimum_roc_auc=args.minimum_roc_auc,
        simulate_transient_failure=args.simulate_transient_failure,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
