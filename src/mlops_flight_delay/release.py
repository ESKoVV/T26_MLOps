from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST_REF = re.compile(r"@sha256:[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_evidence_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError(f"Evidence path выходит за корень проекта: {relative}")
    if not candidate.is_file():
        raise ValueError(f"Evidence file не найден: {relative}")
    return candidate


def _validate_image_ref(image_ref: str, source_commit: str) -> None:
    if image_ref.endswith(":latest"):
        raise ValueError("Плавающий tag latest запрещён")
    if DIGEST_REF.search(image_ref):
        return
    tag = image_ref.rsplit(":", maxsplit=1)[-1]
    if tag != source_commit:
        raise ValueError("Image ref должен содержать digest либо tag, равный source commit SHA")


def build_release_manifest(
    spec: dict[str, Any],
    policy: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    source_commit = str(spec["source_commit"]).lower()
    if not FULL_SHA.fullmatch(source_commit):
        raise ValueError("source_commit должен быть полным 40-символьным SHA")
    _validate_image_ref(str(spec["image"]["ref"]), source_commit)
    if spec["model"]["alias"] != "champion":
        raise ValueError("Release должен ссылаться на проверенный alias champion")
    if not str(spec["model"]["resolved_uri"]).endswith(f"/{spec['model']['version']}"):
        raise ValueError("resolved_uri должен ссылаться на точную model version")

    gates_by_name = {gate["name"]: gate for gate in spec["gates"]}
    required = list(policy["required_gates"])
    missing = [name for name in required if name not in gates_by_name]
    if missing:
        raise ValueError(f"Отсутствуют обязательные release gates: {missing}")

    evidence: list[dict[str, Any]] = []
    has_exception = False
    evaluation_date = date.fromisoformat(spec["evaluation_date"])
    for name in required:
        gate = gates_by_name[name]
        status = gate["status"]
        if status not in policy["allowed_gate_statuses"]:
            raise ValueError(f"Недопустимый статус gate {name}: {status}")
        item: dict[str, Any] = {
            "name": name,
            "status": status,
            "path": gate["path"],
            "sha256": sha256_file(_safe_evidence_path(root, gate["path"])),
        }
        if status == "accepted_with_investigation":
            exception = gate.get("exception") or {}
            required_fields = {"owner", "expires_at", "reason"}
            if not required_fields.issubset(exception):
                raise ValueError(f"Gate {name} требует owner, expires_at и reason")
            if date.fromisoformat(exception["expires_at"]) <= evaluation_date:
                raise ValueError(f"Срок исключения gate {name} уже истёк")
            item["exception"] = exception
            has_exception = True
        evidence.append(item)

    approvals = spec["approvals"]
    independent_approval = bool(approvals.get("approved_by")) and (
        approvals.get("approved_by") != approvals.get("prepared_by")
    )
    ci_success = spec["ci"]["status"] == "success" and bool(spec["ci"].get("run_url"))
    if ci_success and independent_approval:
        release_status = "ready_with_exception" if has_exception else "ready"
    else:
        release_status = "draft"

    return {
        "schema_version": "1.0.0",
        "release_status": release_status,
        "release_version": spec["release_version"],
        "evaluation_date": spec["evaluation_date"],
        "source_commit": source_commit,
        "data": spec["data"],
        "model": spec["model"],
        "image": spec["image"],
        "api": spec["api"],
        "ci": spec["ci"],
        "evidence": evidence,
        "approvals": approvals,
        "rollback": spec["rollback"],
        "limitations": spec["limitations"],
    }


def verify_release_manifest(
    manifest: dict[str, Any],
    policy: dict[str, Any],
    root: Path,
) -> None:
    names = {item["name"] for item in manifest["evidence"]}
    missing = set(policy["required_gates"]) - names
    if missing:
        raise ValueError(f"Manifest потерял release gates: {sorted(missing)}")
    for item in manifest["evidence"]:
        actual = sha256_file(_safe_evidence_path(root, item["path"]))
        if actual != item["sha256"]:
            raise ValueError(f"SHA256 evidence изменился: {item['name']}")
    _validate_image_ref(manifest["image"]["ref"], manifest["source_commit"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or verify an end-to-end release manifest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--spec", type=Path, required=True)
    build.add_argument("--policy", type=Path, required=True)
    build.add_argument("--root", type=Path, default=Path("."))
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--require-ready", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--policy", type=Path, required=True)
    verify.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if args.command == "build":
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        manifest = build_release_manifest(spec, policy, args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if args.require_ready and manifest["release_status"] not in {
            "ready",
            "ready_with_exception",
        }:
            raise SystemExit("Release manifest остаётся draft")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        verify_release_manifest(manifest, policy, args.root)
        print("release-manifest: verified")


if __name__ == "__main__":
    main()
