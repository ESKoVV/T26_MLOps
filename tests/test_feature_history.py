"""LR13: carrier history built from BTS-shaped data is point-in-time safe."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from mlops_flight_delay.features import build_feature_audit, naive_latest_join, point_in_time_join

ROOT = Path(__file__).parents[1]


def test_history_is_available_only_after_the_day_closes(tmp_path: Path) -> None:
    rows = [
        {
            "FlightDate": f"2026-02-0{day}",
            "Carrier": "DL",
            "FlightNumber": 100 + hour,
            "DepHour": hour,
            "IsWeekend": 0,
            "ArrDelay": 30 if hour % 2 else 0,
        }
        for day in range(1, 6)
        for hour in (5, 9, 18)
    ]
    data = tmp_path / "bts.csv"
    pd.DataFrame(rows).to_csv(data, index=False)
    out = tmp_path / "features"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_feature_history.py"),
            str(data),
            str(out),
            "--event-start",
            "2026-02-03",
            "--event-end",
            "2026-02-05",
        ],
        check=True,
        capture_output=True,
    )
    history = pd.read_csv(out / "history.csv")
    entities = pd.read_csv(out / "entities.csv")
    assert (pd.to_datetime(history.available_time) > pd.to_datetime(history.feature_time)).all()

    contract = json.loads((ROOT / "features" / "feature_contract_bts.json").read_text("utf-8"))
    correct = point_in_time_join(entities, history, contract)
    naive = naive_latest_join(entities, history, contract)
    audit = build_feature_audit(entities, naive, correct, contract)
    assert audit["point_in_time_leakage_rows"] == 0
    assert audit["naive_leakage_rows"] > 0
    # 04:00 prediction on 02-03: day 02-02 is not available until 06:00 -> uses day 02-01
    early = correct[correct.request_id == "bts-20260203-DL105-h5"].iloc[0]
    assert early.feature_time == pd.Timestamp("2026-02-02T00:00:00Z")
    assert early.feature_age_hours == 28.0
