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
