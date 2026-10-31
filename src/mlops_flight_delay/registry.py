from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from mlops_flight_delay.train import FEATURES

FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

SKOPS_TRUSTED_TYPES = ["sklearn.tree._tree.Tree"]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_commit_sha(source_commit: str) -> str:
    if not FULL_SHA.fullmatch(source_commit):
        raise ValueError("source_commit must be a full 40-character Git SHA")
    return source_commit.lower()


def validate_candidate_inputs(
    summary: dict[str, Any],
    data_path: Path,
    *,
    minimum_roc_auc: float,
) -> dict[str, Any]:
    if not summary.get("passed"):
        raise ValueError("Upstream flow did not pass")
    metrics = summary.get("metrics")
    if not isinstance(metrics, dict) or "roc_auc" not in metrics:
        raise ValueError("Upstream summary has no metrics.roc_auc")
    roc_auc = float(metrics["roc_auc"])
    if roc_auc < minimum_roc_auc:
        raise ValueError(f"Quality gate failed: ROC AUC {roc_auc:.3f} < {minimum_roc_auc:.3f}")
    actual_hash = sha256_file(data_path)
    expected_hash = summary.get("prepared_sha256")
    if actual_hash != expected_hash:
        raise ValueError("Prepared data SHA256 does not match upstream summary")
    return {
        "passed": True,
        "roc_auc": roc_auc,
        "minimum_roc_auc": minimum_roc_auc,
        "data_sha256": actual_hash,
    }


def check_independent_approval(registered_by: str, approved_by: str, *, drill: bool) -> str:
    """Return the review kind; refuse self-approval unless it is an explicit training drill."""
    if not approved_by.strip():
        raise ValueError("approved_by must name the reviewer")
    if approved_by.strip().lower() != registered_by.strip().lower():
        return "independent"
    if drill:
        return "self-drill"
    raise ValueError(
        f"approver {approved_by!r} registered this candidate; an independent reviewer is required"
    )


def build_release_manifest(
    *,
    model_name: str,
    model_version: str,
    previous_champion_version: str | None,
    run_id: str,
    source_commit: str,
    data_sha256: str,
    minimum_roc_auc: float,
    roc_auc: float,
    status: str,
    approved_by: str,
    review: str = "independent",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "created_at": datetime.now(UTC).isoformat(),
        "model_name": model_name,
        "model_version": str(model_version),
        "previous_champion_version": (
            str(previous_champion_version) if previous_champion_version is not None else None
        ),
        "mlflow_run_id": run_id,
        "source_commit": validate_commit_sha(source_commit),
        "data_sha256": data_sha256,
        "resolved_model_uri": f"models:/{model_name}/{model_version}",
        "quality_gate": {
            "passed": True,
            "minimum_roc_auc": minimum_roc_auc,
            "roc_auc": roc_auc,
        },
        "decision": {"status": status, "approved_by": approved_by, "review": review},
    }


def _smoke_bundle(model_path: Path, data_path: Path) -> None:
    bundle = joblib.load(model_path)
    data = pd.read_csv(data_path)
    probabilities = bundle["model"].predict_proba(data[bundle["features"]].head(5))[:, 1]
    if len(probabilities) == 0 or not all(0.0 <= float(value) <= 1.0 for value in probabilities):
        raise ValueError("Model smoke prediction did not return valid probabilities")


def _smoke_registry_model(model_uri: str, data_path: Path) -> None:
    import mlflow.pyfunc

    data = pd.read_csv(data_path)
    model = mlflow.pyfunc.load_model(model_uri)
    probabilities = np.asarray(model.predict(data[FEATURES].head(5)), dtype=float)
    check_probability_output(probabilities, rows=min(5, len(data)))


def check_probability_output(probabilities: np.ndarray, *, rows: int) -> None:
    """Registry models must return class probabilities: shape (rows, 2), finite, in [0, 1]."""
    if probabilities.shape != (rows, 2):
        raise ValueError(f"Expected probabilities of shape ({rows}, 2), got {probabilities.shape}")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Registry model returned probabilities outside [0, 1]")


def register_candidate(args: argparse.Namespace) -> dict[str, Any]:
    source_commit = validate_commit_sha(args.source_commit)
    summary = _read_json(args.summary)
    gate = validate_candidate_inputs(
        summary,
        args.data,
        minimum_roc_auc=args.minimum_roc_auc,
    )
    _smoke_bundle(args.model, args.data)

    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient
    from mlflow.models import infer_signature

    bundle = joblib.load(args.model)
    data = pd.read_csv(args.data)
    input_example = data[bundle["features"]].head(5)
    output_example = bundle["model"].predict_proba(input_example)
    signature = infer_signature(input_example, output_example)

    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment)
    with mlflow.start_run() as run:
        mlflow.log_params(bundle.get("parameters", {}))
        mlflow.log_metric("test_roc_auc", gate["roc_auc"])
        mlflow.set_tags(
            {
                "source_commit": source_commit,
                "data_sha256": gate["data_sha256"],
                "owner_team": args.owner_team,
            }
        )
        mlflow.sklearn.log_model(
            sk_model=bundle["model"],
            name="model",
            signature=signature,
            input_example=input_example,
            # pyfunc must serve what the signature declares: probabilities, not class labels.
            pyfunc_predict_fn="predict_proba",
            # MLflow 3.17 serializes sklearn models with skops and refuses to load tree nodes
            # unless they are trusted explicitly. The model is trained by this pipeline, so the
            # single reviewed type is trusted instead of switching back to pickle.
            skops_trusted_types=SKOPS_TRUSTED_TYPES,
        )
        run_id = run.info.run_id

    version = mlflow.register_model(f"runs:/{run_id}/model", args.model_name)
    client = MlflowClient()
    version_id = str(version.version)
    tags = {
        "validation_status": "passed",
        "source_commit": source_commit,
        "data_sha256": gate["data_sha256"],
        "quality_report": args.output.as_posix(),
        "owner_team": args.owner_team,
        "registered_by": args.registered_by,
        "release_status": "candidate",
        "test_roc_auc": str(gate["roc_auc"]),
        "minimum_roc_auc": str(gate["minimum_roc_auc"]),
    }
    for key, value in tags.items():
        client.set_model_version_tag(args.model_name, version_id, key, value)
    client.set_registered_model_alias(args.model_name, "candidate", version_id)
    resolved = client.get_model_version_by_alias(args.model_name, "candidate")
    if str(resolved.version) != version_id:
        raise RuntimeError("candidate alias did not resolve to the new version")

    result = {
        "schema_version": "1.0.0",
        "status": "candidate",
        "model_name": args.model_name,
        "model_version": version_id,
        "model_uri": f"models:/{args.model_name}/{version_id}",
        "mlflow_run_id": run_id,
        "source_commit": source_commit,
        "data_sha256": gate["data_sha256"],
        "quality_gate": gate,
        "tags": tags,
    }
    _write_json(args.output, result)
    return result


def _alias_or_none(client: Any, model_name: str, alias: str) -> Any | None:
    try:
        return client.get_model_version_by_alias(model_name, alias)
    except Exception as error:
        if "alias" in str(error).lower() or "not found" in str(error).lower():
            return None
        raise


def promote_candidate(args: argparse.Namespace) -> dict[str, Any]:
    import mlflow
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()
    candidate = client.get_model_version_by_alias(args.model_name, "candidate")
    if candidate.tags.get("validation_status") != "passed":
        raise ValueError("candidate does not have validation_status=passed")
    reviewed_version = str(candidate.version)
    review = check_independent_approval(
        candidate.tags.get("registered_by", "unknown"), args.approved_by, drill=args.drill
    )
    champion = _alias_or_none(client, args.model_name, "champion")
    previous = str(champion.version) if champion is not None else None

    candidate_again = client.get_model_version_by_alias(args.model_name, "candidate")
    if str(candidate_again.version) != reviewed_version:
        raise RuntimeError("candidate changed during promotion; repeat review")
    _smoke_registry_model(f"models:/{args.model_name}/{reviewed_version}", args.data)
    client.set_registered_model_alias(args.model_name, "champion", reviewed_version)
    resolved = client.get_model_version_by_alias(args.model_name, "champion")
    if str(resolved.version) != reviewed_version:
        raise RuntimeError("champion alias verification failed")
    client.set_model_version_tag(args.model_name, reviewed_version, "release_status", "approved")
    client.set_model_version_tag(args.model_name, reviewed_version, "approved_by", args.approved_by)
    client.set_model_version_tag(args.model_name, reviewed_version, "review", review)

    manifest = build_release_manifest(
        model_name=args.model_name,
        model_version=reviewed_version,
        previous_champion_version=previous,
        run_id=resolved.run_id,
        source_commit=resolved.tags["source_commit"],
        data_sha256=resolved.tags["data_sha256"],
        minimum_roc_auc=float(resolved.tags["minimum_roc_auc"]),
        roc_auc=float(resolved.tags["test_roc_auc"]),
        status="approved",
        approved_by=args.approved_by,
        review=review,
    )
    _write_json(args.output, manifest)
    return manifest


def rollback_champion(args: argparse.Namespace) -> dict[str, Any]:
    import mlflow
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()
    current = client.get_model_version_by_alias(args.model_name, "champion")
    target = client.get_model_version(args.model_name, str(args.target_version))
    _smoke_registry_model(f"models:/{args.model_name}/{target.version}", args.data)
    client.set_registered_model_alias(args.model_name, "champion", str(target.version))
    resolved = client.get_model_version_by_alias(args.model_name, "champion")
    if str(resolved.version) != str(target.version):
        raise RuntimeError("rollback alias verification failed")
    client.set_model_version_tag(
        args.model_name,
        str(current.version),
        "release_status",
        "rolled_back",
    )
    result = {
        "schema_version": "1.0.0",
        "created_at": datetime.now(UTC).isoformat(),
        "model_name": args.model_name,
        "from_version": str(current.version),
        "target_version": str(target.version),
        "resolved_model_uri": f"models:/{args.model_name}/{target.version}",
        "reason": args.reason,
        "approved_by": args.approved_by,
        "smoke_passed": True,
    }
    _write_json(args.output, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MLflow Registry release workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register")
    register.add_argument("--tracking-uri", required=True)
    register.add_argument("--experiment", default="mlops-flight-delay-registry")
    register.add_argument("--model-name", required=True)
    register.add_argument("--owner-team", required=True)
    register.add_argument("--model", type=Path, required=True)
    register.add_argument("--data", type=Path, required=True)
    register.add_argument("--summary", type=Path, required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--minimum-roc-auc", type=float, default=0.5)
    register.add_argument("--registered-by", default="unknown", help="GitHub login автора")
    register.add_argument("--output", type=Path, required=True)
    register.set_defaults(handler=register_candidate)

    promote = subparsers.add_parser("promote")
    promote.add_argument("--tracking-uri", required=True)
    promote.add_argument("--model-name", required=True)
    promote.add_argument("--data", type=Path, required=True)
    promote.add_argument("--approved-by", required=True)
    promote.add_argument(
        "--drill",
        action="store_true",
        help="учебная отработка: разрешить одобрение автором, отметить review=self-drill",
    )
    promote.add_argument("--output", type=Path, required=True)
    promote.set_defaults(handler=promote_candidate)

    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--tracking-uri", required=True)
    rollback.add_argument("--model-name", required=True)
    rollback.add_argument("--target-version", required=True)
    rollback.add_argument("--data", type=Path, required=True)
    rollback.add_argument("--reason", required=True)
    rollback.add_argument("--approved-by", required=True)
    rollback.add_argument("--output", type=Path, required=True)
    rollback.set_defaults(handler=rollback_champion)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        result = args.handler(args)
    except Exception as error:
        failure = {
            "schema_version": "1.0.0",
            "created_at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "command": args.command,
            "error_type": type(error).__name__,
            "message": str(error),
        }
        if hasattr(args, "output"):
            _write_json(args.output, failure)
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
