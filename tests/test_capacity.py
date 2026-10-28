import copy
import json
from pathlib import Path

import pytest

from mlops_flight_delay.capacity import build_capacity_report, percentile

ROOT = Path(__file__).resolve().parents[1]
RESULTS = json.loads((ROOT / "data/capacity/lr15_sample.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "capacity/load_policy.json").read_text(encoding="utf-8"))


def test_nearest_rank_percentile_is_deterministic() -> None:
    assert percentile([0.1, 0.2, 0.3, 0.4], 0.95) == 0.4


def test_baseline_passes_and_keeps_capacity() -> None:
    report = build_capacity_report(RESULTS, POLICY)
    assert report["status"] == "pass"
    assert report["decision"]["action"] == "keep_baseline"
    assert report["scenarios"]["burst"]["throughput_rps"] == 10.0


def test_slo_failure_requires_investigation_before_scaling() -> None:
    failed = copy.deepcopy(RESULTS)
    failed["scenarios"]["burst"]["latency_seconds"][-2:] = [0.8, 0.9]
    report = build_capacity_report(failed, POLICY)
    assert report["status"] == "review"
    assert report["decision"]["action"] == "investigate_then_scale"
    assert "не является автоматическим" in report["decision"]["statement"]


def test_missing_scenario_is_rejected() -> None:
    incomplete = copy.deepcopy(RESULTS)
    incomplete["scenarios"].pop("burst")
    with pytest.raises(ValueError, match="сценарии"):
        build_capacity_report(incomplete, POLICY)
