from datetime import UTC, datetime

import pandas as pd

from mlops_flight_delay.monitoring import (
    build_delayed_quality_report,
    build_drift_report,
    monitoring_decision,
)

POLICY = {
    "minimum_window_rows": 8,
    "psi_warning": 0.1,
    "psi_alert": 0.25,
    "expected_label_delay_hours": 24,
    "minimum_labeled_rows": 4,
    "minimum_label_coverage": 0.75,
    "minimum_roc_auc": 0.7,
    "minimum_f1": 0.6,
}


def test_drift_report_uses_reference_and_current_windows() -> None:
    reference = pd.DataFrame({"DepHour": range(8, 16), "IsWeekend": [0, 1] * 4})
    current = pd.DataFrame({"DepHour": range(16, 24), "IsWeekend": [1] * 8})
    report = build_drift_report(reference, current, POLICY)
    assert report["status"] == "alert"
    assert set(report["features"]) == {"DepHour", "IsWeekend"}


def test_delayed_quality_excludes_predictions_with_immature_labels() -> None:
    predictions = pd.DataFrame(
        {
            "request_id": [f"r{i}" for i in range(6)],
            "event_time": [
                "2026-10-17T10:00:00Z",
                "2026-10-17T11:00:00Z",
                "2026-10-17T12:00:00Z",
                "2026-10-17T13:00:00Z",
                "2026-10-20T09:00:00Z",
                "2026-10-20T10:00:00Z",
            ],
            "prediction_probability": [0.1, 0.2, 0.8, 0.9, 0.4, 0.6],
            "model_version": ["3"] * 6,
        }
    )
    labels = pd.DataFrame(
        {
            "request_id": ["r0", "r1", "r2", "r3"],
            "label_time": ["2026-10-18T10:00:00Z"] * 4,
            "ArrDelay": [0, 5, 20, 30],
        }
    )
    report = build_delayed_quality_report(
        predictions,
        labels,
        POLICY,
        as_of=datetime(2026, 10, 20, 12, tzinfo=UTC),
    )
    assert report["eligible_predictions"] == 4
    assert report["matched_labels"] == 4
    assert report["label_coverage"] == 1.0
    assert report["status"] == "ok"


def test_missing_mature_labels_blocks_automatic_decision() -> None:
    decision = monitoring_decision(
        {"status": "alert"},
        {"status": "insufficient_evidence"},
    )
    assert decision["action"] == "hold"


def test_retraining_requires_drift_and_quality_breach() -> None:
    decision = monitoring_decision(
        {"status": "alert"},
        {"status": "quality_breach"},
    )
    assert decision["action"] == "retraining_review"
