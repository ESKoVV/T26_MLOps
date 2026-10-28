import copy
import json
from pathlib import Path

import pytest

from mlops_flight_delay.release import build_release_manifest, verify_release_manifest

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "release/release_spec.example.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "release/release_policy.json").read_text(encoding="utf-8"))


def test_example_is_honestly_draft_and_hashes_all_evidence() -> None:
    manifest = build_release_manifest(SPEC, POLICY, ROOT)
    assert manifest["release_status"] == "draft"
    assert len(manifest["evidence"]) == len(POLICY["required_gates"])
    assert all(len(item["sha256"]) == 64 for item in manifest["evidence"])
    verify_release_manifest(manifest, POLICY, ROOT)


def test_successful_ci_and_independent_approval_make_ready_with_exception() -> None:
    spec = copy.deepcopy(SPEC)
    spec["ci"] = {"status": "success", "run_url": "https://github.com/acme/repo/actions/runs/1"}
    spec["approvals"] = {
        "prepared_by": "student-author",
        "approved_by": "student-reviewer",
        "approved_at": "2026-10-20T12:00:00Z",
    }
    manifest = build_release_manifest(spec, POLICY, ROOT)
    assert manifest["release_status"] == "ready_with_exception"


def test_latest_image_is_rejected() -> None:
    spec = copy.deepcopy(SPEC)
    spec["image"]["ref"] = "flight-delay-api:latest"
    with pytest.raises(ValueError, match="latest"):
        build_release_manifest(spec, POLICY, ROOT)


def test_changed_evidence_breaks_verification() -> None:
    manifest = build_release_manifest(SPEC, POLICY, ROOT)
    manifest["evidence"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA256"):
        verify_release_manifest(manifest, POLICY, ROOT)


def test_gate_cannot_claim_pass_over_failing_evidence(tmp_path: Path) -> None:
    root = tmp_path
    for gate in SPEC["gates"]:
        target = root / gate["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / gate["path"]).read_bytes())
    (root / "reports/governance/lr14-example.json").write_text(
        json.dumps({"status": "review"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="status=review"):
        build_release_manifest(SPEC, POLICY, root)


@pytest.mark.parametrize("approver", ["Student-Author", " student-author "], ids=["case", "spaces"])
def test_self_approval_with_different_case_stays_draft(approver: str) -> None:
    spec = copy.deepcopy(SPEC)
    spec["ci"] = {"status": "success", "run_url": "https://github.com/acme/repo/actions/runs/1"}
    spec["approvals"] = {
        "prepared_by": "student-author",
        "approved_by": approver,
        "approved_at": None,
    }
    assert build_release_manifest(spec, POLICY, ROOT)["release_status"] == "draft"
