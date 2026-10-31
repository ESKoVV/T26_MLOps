from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mlops_flight_delay.evaluate import classification_metrics

FEATURES = ("DepHour", "IsWeekend")


def _shares(counts: np.ndarray, epsilon: float = 1e-6) -> np.ndarray:
    values = counts.astype(float) + epsilon
    return values / values.sum()


def numeric_psi(reference: pd.Series, current: pd.Series, *, bins: int = 10) -> float:
    """Calculate PSI using bin boundaries learned only from the reference window."""
    ref = pd.to_numeric(reference, errors="raise").dropna().to_numpy(dtype=float)
    cur = pd.to_numeric(current, errors="raise").dropna().to_numpy(dtype=float)
    if len(ref) < 2 or len(cur) < 2:
        raise ValueError("Для PSI нужны минимум два значения в каждом окне")
    if not np.isfinite(ref).all() or not np.isfinite(cur).all():
        raise ValueError("PSI не принимает бесконечные значения")

    quantiles = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.quantile(ref, quantiles))
    if len(edges) < 2:
        center = float(edges[0])
        edges = np.array([center - 0.5, center + 0.5])
    edges[0], edges[-1] = -np.inf, np.inf
    ref_share = _shares(np.histogram(ref, bins=edges)[0])
    cur_share = _shares(np.histogram(cur, bins=edges)[0])
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def categorical_psi(reference: pd.Series, current: pd.Series) -> float:
    ref = reference.dropna().astype(str)
    cur = current.dropna().astype(str)
    if ref.empty or cur.empty:
        raise ValueError("Категориальный PSI требует непустые окна")
    categories = sorted(set(ref) | set(cur))
    ref_share = _shares(ref.value_counts().reindex(categories, fill_value=0).to_numpy())
    cur_share = _shares(cur.value_counts().reindex(categories, fill_value=0).to_numpy())
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def _status(score: float, warning: float, alert: float) -> str:
    if score >= alert:
        return "alert"
    if score >= warning:
        return "warning"
    return "ok"


def build_drift_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    policy: dict[str, Any],
) -> dict[str, Any]:
    missing = set(FEATURES) - set(reference.columns) | (set(FEATURES) - set(current.columns))
    if missing:
        raise ValueError(f"В окнах отсутствуют признаки: {sorted(missing)}")
    minimum = int(policy["minimum_window_rows"])
    if len(reference) < minimum or len(current) < minimum:
        return {
            "status": "insufficient_evidence",
            "reference_rows": len(reference),
            "current_rows": len(current),
            "features": {},
        }

    warning = float(policy["psi_warning"])
    alert = float(policy["psi_alert"])
    scores = {
        "DepHour": numeric_psi(reference["DepHour"], current["DepHour"]),
        "IsWeekend": categorical_psi(reference["IsWeekend"], current["IsWeekend"]),
    }
    features = {
        name: {
            "method": "psi_reference_bins" if name == "DepHour" else "psi_categories",
            "score": round(score, 6),
            "status": _status(score, warning, alert),
        }
        for name, score in scores.items()
    }
    states = {item["status"] for item in features.values()}
    overall = "alert" if "alert" in states else "warning" if "warning" in states else "ok"
    return {
        "status": overall,
        "reference_rows": len(reference),
        "current_rows": len(current),
        "features": features,
    }


def build_delayed_quality_report(
    predictions: pd.DataFrame,
    labels: pd.DataFrame,
    policy: dict[str, Any],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    prediction_columns = {
        "request_id",
        "event_time",
        "prediction_probability",
        "model_version",
    }
    label_columns = {"request_id", "label_time", "ArrDelay"}
    missing = prediction_columns - set(predictions.columns) | (label_columns - set(labels.columns))
    if missing:
        raise ValueError(f"В журналах отсутствуют столбцы: {sorted(missing)}")
    if predictions["request_id"].duplicated().any() or labels["request_id"].duplicated().any():
        raise ValueError("request_id должен быть уникален в каждом журнале")

    prepared = predictions.copy()
    prepared["event_time"] = pd.to_datetime(prepared["event_time"], utc=True, errors="raise")
    prepared["prediction_probability"] = pd.to_numeric(
        prepared["prediction_probability"], errors="raise"
    )
    prepared_labels = labels.copy()
    prepared_labels["label_time"] = pd.to_datetime(
        prepared_labels["label_time"], utc=True, errors="raise"
    )
    prepared_labels["ArrDelay"] = pd.to_numeric(prepared_labels["ArrDelay"], errors="raise")
    prepared_labels = prepared_labels[prepared_labels["label_time"] <= as_of.astimezone(UTC)]

    delay = timedelta(hours=float(policy["expected_label_delay_hours"]))
    cutoff = as_of.astimezone(UTC) - delay
    eligible = prepared[prepared["event_time"] <= cutoff].copy()
    joined = eligible.merge(prepared_labels, on="request_id", how="left", validate="one_to_one")
    matched = joined[joined["label_time"].notna()].copy()
    coverage = 1.0 if eligible.empty else len(matched) / len(eligible)
    minimum = int(policy["minimum_labeled_rows"])
    minimum_coverage = float(policy["minimum_label_coverage"])

    result: dict[str, Any] = {
        "as_of": as_of.astimezone(UTC).isoformat(),
        "eligible_cutoff": cutoff.isoformat(),
        "eligible_predictions": len(eligible),
        "matched_labels": len(matched),
        "label_coverage": round(coverage, 6),
        "metrics": {},
    }
    if len(matched) < minimum or coverage < minimum_coverage:
        result["status"] = "insufficient_evidence"
        return result

    targets = (matched["ArrDelay"] >= 15).astype(int)
    if targets.nunique() < 2:
        result["status"] = "insufficient_evidence"
        result["reason"] = "Для ROC AUC нужны фактические метки обоих классов"
        return result
    metrics = classification_metrics(targets, matched["prediction_probability"])
    result["metrics"] = {name: round(value, 6) for name, value in metrics.items()}
    breached = [
        name for name in ("roc_auc", "f1") if metrics[name] < float(policy[f"minimum_{name}"])
    ]
    result["status"] = "quality_breach" if breached else "ok"
    result["breached_metrics"] = breached
    return result


def monitoring_decision(drift: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    if quality["status"] == "insufficient_evidence":
        return {"action": "hold", "reason": "Недостаточно зрелых и сопоставленных меток"}
    if quality["status"] == "quality_breach" and drift["status"] == "alert":
        return {"action": "retraining_review", "reason": "Drift подтверждён деградацией качества"}
    if quality["status"] == "quality_breach":
        return {
            "action": "incident_review",
            "reason": "Качество снизилось без подтверждённого drift",
        }
    if drift["status"] == "alert":
        return {"action": "investigate", "reason": "Drift есть, но качество пока не деградировало"}
    return {"action": "no_action", "reason": "Пороговые условия не нарушены"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--as-of", type=str, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    as_of = datetime.fromisoformat(args.as_of)
    if as_of.tzinfo is None:
        raise ValueError("--as-of должен содержать часовой пояс")
    drift = build_drift_report(pd.read_csv(args.reference), pd.read_csv(args.current), policy)
    quality = build_delayed_quality_report(
        pd.read_csv(args.predictions), pd.read_csv(args.labels), policy, as_of=as_of
    )
    report = {
        "schema_version": "1.0.0",
        "policy_version": policy["policy_version"],
        "drift": drift,
        "delayed_quality": quality,
        "decision": monitoring_decision(drift, quality),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
