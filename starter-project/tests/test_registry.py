import json
from pathlib import Path

import pytest

from mlops_flight_delay.registry import (
    build_release_manifest,
    sha256_file,
    validate_candidate_inputs,
    validate_commit_sha,
)


def _summary(data_path: Path, *, passed: bool = True, roc_auc: float = 0.75) -> dict:
    return {
        "passed": passed,
        "prepared_sha256": sha256_file(data_path),
        "metrics": {"roc_auc": roc_auc},
    }


def test_candidate_gate_accepts_matching_evidence(tmp_path: Path) -> None:
    data_path = tmp_path / "prepared.csv"
    data_path.write_text("x\n1\n", encoding="utf-8")
    result = validate_candidate_inputs(_summary(data_path), data_path, minimum_roc_auc=0.7)
    assert result["passed"] is True
    assert result["data_sha256"] == sha256_file(data_path)


@pytest.mark.parametrize(
    ("passed", "roc_auc", "minimum"),
    [(False, 0.9, 0.7), (True, 0.6, 0.7)],
)
def test_candidate_gate_rejects_failed_evidence(
    tmp_path: Path, passed: bool, roc_auc: float, minimum: float
) -> None:
    data_path = tmp_path / "prepared.csv"
    data_path.write_text("x\n1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_candidate_inputs(
            _summary(data_path, passed=passed, roc_auc=roc_auc),
            data_path,
            minimum_roc_auc=minimum,
        )


def test_candidate_gate_rejects_hash_mismatch(tmp_path: Path) -> None:
    data_path = tmp_path / "prepared.csv"
    data_path.write_text("x\n1\n", encoding="utf-8")
    summary = _summary(data_path)
    data_path.write_text("x\n2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        validate_candidate_inputs(summary, data_path, minimum_roc_auc=0.7)


def test_commit_requires_full_sha() -> None:
    assert validate_commit_sha("a" * 40) == "a" * 40
    with pytest.raises(ValueError, match="40-character"):
        validate_commit_sha("abc123")


def test_release_manifest_uses_exact_version_and_previous_champion() -> None:
    manifest = build_release_manifest(
        model_name="team-03-flight-delay-classifier",
        model_version="2",
        previous_champion_version="1",
        run_id="run-123",
        source_commit="b" * 40,
        data_sha256="c" * 64,
        minimum_roc_auc=0.7,
        roc_auc=0.8,
        status="approved",
        approved_by="reviewer",
    )
    assert manifest["resolved_model_uri"].endswith("/2")
    assert manifest["previous_champion_version"] == "1"
    assert manifest["decision"] == {"status": "approved", "approved_by": "reviewer"}
    json.dumps(manifest)

