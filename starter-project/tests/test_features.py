import json
from pathlib import Path

import pandas as pd
import pytest

from mlops_flight_delay.features import (
    build_feature_audit,
    naive_latest_join,
    point_in_time_join,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "features/feature_contract.json").read_text(encoding="utf-8"))


def sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    entities = pd.read_csv(ROOT / "data/features/entities.csv")
    history = pd.read_csv(ROOT / "data/features/history.csv")
    return entities, history


def test_point_in_time_join_never_uses_future_or_unavailable_features() -> None:
    entities, history = sample_data()
    result = point_in_time_join(entities, history, CONTRACT)
    event_time = pd.to_datetime(result["event_time"], utc=True)
    feature_time = pd.to_datetime(result["feature_time"], utc=True)
    available_time = pd.to_datetime(result["available_time"], utc=True)
    assert (feature_time <= event_time).all()
    assert (available_time <= event_time).all()


def test_available_time_blocks_feature_that_was_not_observable() -> None:
    entities, history = sample_data()
    result = point_in_time_join(entities, history, CONTRACT).set_index("request_id")
    assert result.loc["pit-003", "trailing_delay_rate"] == 0.35


def test_naive_join_is_detected_as_leaking() -> None:
    entities, history = sample_data()
    naive = naive_latest_join(entities, history, CONTRACT)
    correct = point_in_time_join(entities, history, CONTRACT)
    audit = build_feature_audit(entities, naive, correct, CONTRACT)
    assert audit["naive_leakage_rows"] > 0
    assert audit["point_in_time_leakage_rows"] == 0
    assert audit["status"] == "pass"


def test_duplicate_request_id_is_rejected() -> None:
    entities, history = sample_data()
    duplicated = pd.concat([entities, entities.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="request_id"):
        point_in_time_join(duplicated, history, CONTRACT)
