import json
from pathlib import Path

import pandas as pd
import pytest

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
    assert any(
        item["name"] == "DepHour.maximum" and not item["passed"] for item in result["checks"]
    )


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


def _valid_frame(rows: int = 20) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "FlightDate": pd.date_range("2026-01-01", periods=rows).strftime("%Y-%m-%d"),
            "DepHour": [hour % 24 for hour in range(rows)],
            "IsWeekend": [0, 1] * (rows // 2),
            "ArrDelay": [0, 30] * (rows // 2),
        }
    )


@pytest.mark.parametrize(
    ("mutation", "failed_check"),
    [
        (lambda frame: frame.assign(IsWeekend=[2] + [0] * 19), "IsWeekend.allowed_values"),
        (lambda frame: frame.assign(DepHour=[9.5] + [9] * 19), "DepHour.integer"),
        (lambda frame: frame.assign(DepHour=[None] + [9] * 19), "DepHour.nullable"),
        (lambda frame: frame.assign(ArrDelay=[2000] + [0] * 19), "ArrDelay.maximum"),
        (lambda frame: frame.assign(Gate=["A1"] * 20), "extra_columns"),
        (lambda frame: pd.concat([frame, frame.tail(1)]), "duplicate_rows"),
        (lambda frame: frame.head(10), "minimum_rows"),
        (
            lambda frame: frame.assign(FlightDate=["2026-13-01"] + list(frame.FlightDate[1:])),
            "FlightDate.date",
        ),
    ],
    ids=[
        "weekend-2",
        "fractional-hour",
        "null-hour",
        "delay-above-max",
        "unknown-column",
        "duplicate",
        "too-few-rows",
        "bad-date",
    ],
)
def test_contract_violation_is_detected(tmp_path: Path, mutation, failed_check: str) -> None:
    path = tmp_path / "broken.csv"
    mutation(_valid_frame()).to_csv(path, index=False)
    result = validate_dataset(path, CONTRACT)
    assert result["passed"] is False
    assert any(item["name"] == failed_check and not item["passed"] for item in result["checks"])
    assert result["split"] is None


def test_report_contains_chronological_split() -> None:
    result = validate_dataset(ROOT / "data" / "flights_sample.csv", CONTRACT)
    split = result["split"]
    assert split["policy"] == "chronological-60-20-20"
    assert [split[part]["rows"] for part in ("train", "validation", "test")] == [14, 5, 5]
    assert split["train"]["end"] < split["validation"]["start"]
    assert split["validation"]["end"] < split["test"]["start"]
    assert split["ordered"] is True


def test_overlapping_periods_fail_split_check(tmp_path: Path) -> None:
    frame = _valid_frame()
    frame["FlightDate"] = ["2026-01-01"] * 14 + ["2026-01-02"] * 6
    path = tmp_path / "overlap.csv"
    frame.to_csv(path, index=False)
    result = validate_dataset(path, CONTRACT)
    assert result["split"]["ordered"] is False
    assert result["passed"] is False
