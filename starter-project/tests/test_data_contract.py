import json
from pathlib import Path

import pandas as pd

from mlops_flight_delay.validate_data import validate_dataset

ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "data" / "contract.json"


def test_course_sample_matches_contract() -> None:
    result = validate_dataset(ROOT / "data" / "flights_sample.csv", CONTRACT)
    assert result["passed"] is True
    assert result["rows"] == 24
    assert len(result["sha256"]) == 64


def test_range_violation_is_detected(tmp_path: Path) -> None:
    bad_data = pd.DataFrame(
        {
            "FlightDate": pd.date_range("2026-01-01", periods=20).strftime("%Y-%m-%d"),
            "DepHour": [25] * 20,
            "IsWeekend": [0] * 20,
            "ArrDelay": range(20),
        }
    )
    path = tmp_path / "bad_range.csv"
    bad_data.to_csv(path, index=False)
    result = validate_dataset(path, CONTRACT)
    assert result["passed"] is False
    assert any(item["name"] == "DepHour.maximum" and not item["passed"] for item in result["checks"])


def test_schema_violation_is_detected(tmp_path: Path) -> None:
    rows = [
        {"FlightDate": f"2026-01-{day:02d}", "DepHour": day % 24, "IsWeekend": 0}
        for day in range(1, 21)
    ]
    path = tmp_path / "missing_target.csv"
    path.write_text(pd.DataFrame(rows).to_csv(index=False), encoding="utf-8")
    result = validate_dataset(path, CONTRACT)
    assert result["passed"] is False
    required = next(item for item in result["checks"] if item["name"] == "required_columns")
    assert "ArrDelay" in required["details"]


def test_contract_is_valid_json() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["contract_version"] == "2.0.0"


def test_non_chronological_rows_are_detected(tmp_path: Path) -> None:
    data = pd.read_csv(ROOT / "data" / "flights_sample.csv")
    data.iloc[[0, 1]] = data.iloc[[1, 0]].to_numpy()
    path = tmp_path / "shuffled.csv"
    data.to_csv(path, index=False)
    result = validate_dataset(path, CONTRACT)
    assert result["passed"] is False
    assert any(
        item["name"] == "FlightDate.chronological_order" and not item["passed"]
        for item in result["checks"]
    )
