"""LR12: monitoring logs built from a BTS-shaped fragment."""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from mlops_flight_delay.train import train_model

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "build_monitoring_window.py"


@pytest.fixture
def bts_like(tmp_path: Path) -> tuple[Path, Path]:
    days = pd.date_range("2026-01-01", periods=40)
    rows = [
        {
            "FlightDate": day.strftime("%Y-%m-%d"),
            "Carrier": "DL",
            "FlightNumber": 100 + hour,
            "DepHour": hour,
            "IsWeekend": int(day.dayofweek >= 5),
            "ArrDelay": 40 if hour >= 17 else 0,
        }
        for day in days
        for hour in range(6, 22)
    ]
    data = tmp_path / "bts.csv"
    pd.DataFrame(rows).to_csv(data, index=False)
    model = tmp_path / "model.joblib"
    train_model(data, model, n_estimators=10, max_depth=3)
    return data, model


def _build(bts_like, out: Path, *extra: str) -> None:
    data, model = bts_like
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(data),
            str(model),
            str(out),
            "--reference-end",
            "2026-01-25",
            "--current-start",
            "2026-01-31",
            *extra,
        ],
        check=True,
        capture_output=True,
    )


def test_logs_are_joinable_and_labels_arrive_later(bts_like, tmp_path: Path) -> None:
    out = tmp_path / "window"
    _build(bts_like, out)
    predictions = pd.read_csv(out / "predictions.csv")
    labels = pd.read_csv(out / "labels.csv")
    assert predictions["request_id"].is_unique
    joined = predictions.merge(labels, on="request_id", validate="one_to_one")
    assert len(joined) == len(predictions)
    assert (pd.to_datetime(joined.label_time) > pd.to_datetime(joined.event_time)).all()
    assert predictions["prediction_probability"].between(0, 1).all()
    assert "ArrDelay" not in pd.read_csv(out / "current.csv").columns


def test_missing_label_share_drops_labels(bts_like, tmp_path: Path) -> None:
    out = tmp_path / "late"
    _build(bts_like, out, "--missing-label-share", "0.25")
    predictions = pd.read_csv(out / "predictions.csv")
    labels = pd.read_csv(out / "labels.csv")
    assert len(labels) == round(len(predictions) * 0.75)


def test_weekends_only_window(bts_like, tmp_path: Path) -> None:
    out = tmp_path / "weekend"
    _build(bts_like, out, "--weekends-only")
    assert set(pd.read_csv(out / "current.csv")["IsWeekend"]) == {1}
