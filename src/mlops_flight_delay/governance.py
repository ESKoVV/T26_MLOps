from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

REQUIRED_COLUMNS = {"y_true", "prediction_probability"}


def _heading_key(value: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", " ", value.lower()).strip()


def audit_model_card(path: Path, required_sections: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    headings = {
        _heading_key(match.group(1))
        for match in re.finditer(r"^#{2,3}\s+(.+?)\s*$", text, flags=re.MULTILINE)
    }
    missing = [section for section in required_sections if _heading_key(section) not in headings]
    return {
        "path": path.as_posix(),
        "required_sections": required_sections,
        "missing_sections": missing,
        "status": "pass" if not missing else "fail",
    }


def _metrics(frame: pd.DataFrame, threshold: float) -> dict[str, Any]:
    labels = frame["y_true"].astype(int)
    scores = frame["prediction_probability"].astype(float)
    predictions = (scores >= threshold).astype(int)
    result: dict[str, Any] = {
        "rows": len(frame),
        "positive_rate": float(labels.mean()),
        "predicted_positive_rate": float(predictions.mean()),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": None,
    }
    if labels.nunique() == 2:
        result["roc_auc"] = float(roc_auc_score(labels, scores))
    return result


def build_governance_report(
    evaluation: pd.DataFrame,
    policy: dict[str, Any],
    model_card: Path,
) -> dict[str, Any]:
    group_column = str(policy["group_column"])
    missing = (REQUIRED_COLUMNS | {group_column}) - set(evaluation.columns)
    if missing:
        raise ValueError(f"Отсутствуют обязательные столбцы: {sorted(missing)}")
    if evaluation.empty:
        raise ValueError("Evaluation dataset не должен быть пустым")
    if not evaluation["y_true"].isin([0, 1]).all():
        raise ValueError("y_true должен содержать только 0 и 1")
    scores = evaluation["prediction_probability"]
    if scores.isna().any() or not scores.between(0.0, 1.0).all():
        raise ValueError("prediction_probability должен быть числом от 0 до 1")

    threshold = float(policy["classification_threshold"])
    minimum_rows = int(policy["minimum_group_rows"])
    overall = _metrics(evaluation, threshold)
    groups: dict[str, Any] = {}
    eligible_f1: list[float] = []
    for value, frame in evaluation.groupby(group_column, dropna=False):
        key = str(value)
        if len(frame) < minimum_rows:
            groups[key] = {
                "rows": len(frame),
                "status": "insufficient_sample",
                "reason": f"минимум {minimum_rows} строк для публикации метрик",
            }
            continue
        metrics = _metrics(frame, threshold)
        metrics["status"] = "reported"
        groups[key] = metrics
        eligible_f1.append(float(metrics["f1"]))

    f1_gap = max(eligible_f1) - min(eligible_f1) if len(eligible_f1) >= 2 else None
    checks = {
        "minimum_overall_f1": overall["f1"] >= float(policy["minimum_overall_f1"]),
        "maximum_f1_gap": f1_gap is not None and f1_gap <= float(policy["maximum_f1_gap"]),
        "enough_groups": len(eligible_f1) >= 2,
    }
    card = audit_model_card(model_card, list(policy["required_model_card_sections"]))
    checks["model_card_complete"] = card["status"] == "pass"
    status = "pass" if all(checks.values()) else "review"
    return {
        "policy_version": policy["policy_version"],
        "status": status,
        "scope": {
            "group_column": group_column,
            "statement": (
                "IsWeekend — учебный операционный сегмент; результат не является "
                "доказательством справедливости для защищённых или уязвимых групп."
            ),
        },
        "threshold": threshold,
        "overall": overall,
        "groups": groups,
        "f1_gap": f1_gap,
        "checks": checks,
        "model_card": card,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit responsible-ML release evidence")
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--model-card", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    report = build_governance_report(pd.read_csv(args.evaluation), policy, args.model_card)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
