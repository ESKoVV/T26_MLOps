import json
from pathlib import Path

import pandas as pd

from mlops_flight_delay.governance import audit_model_card, build_governance_report

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "governance/responsible_ai_policy.json").read_text(encoding="utf-8"))


def test_governance_report_contains_overall_and_group_metrics() -> None:
    data = pd.read_csv(ROOT / "data/governance/evaluation.csv")
    report = build_governance_report(data, POLICY, ROOT / "docs/model-card.md")
    assert report["status"] == "pass"
    assert set(report["groups"]) == {"0", "1"}
    assert report["f1_gap"] is not None
    assert report["checks"]["maximum_f1_gap"] is True


def test_small_group_is_suppressed_instead_of_overinterpreted() -> None:
    data = pd.read_csv(ROOT / "data/governance/evaluation.csv").iloc[:7]
    report = build_governance_report(data, POLICY, ROOT / "docs/model-card.md")
    assert report["groups"]["1"]["status"] == "insufficient_sample"
    assert report["status"] == "review"


def test_model_card_audit_detects_missing_heading(tmp_path: Path) -> None:
    card = tmp_path / "card.md"
    card.write_text("## Краткое описание\nТест.\n", encoding="utf-8")
    result = audit_model_card(card, ["Краткое описание", "Назначение"])
    assert result["status"] == "fail"
    assert result["missing_sections"] == ["Назначение"]


def test_report_does_not_claim_fairness_proof() -> None:
    data = pd.read_csv(ROOT / "data/governance/evaluation.csv")
    report = build_governance_report(data, POLICY, ROOT / "docs/model-card.md")
    assert "не является доказательством справедливости" in report["scope"]["statement"]
