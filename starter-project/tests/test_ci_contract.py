from pathlib import Path

WORKFLOW = Path(".github/workflows/ci.yml")


def test_ci_workflow_contains_required_quality_gates() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    required_fragments = (
        "permissions:",
        "contents: read",
        "concurrency:",
        "cancel-in-progress: true",
        "actions/checkout@v7",
        "actions/setup-python@v7",
        "actions/upload-artifact@v4",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "--junitxml=reports/tests/ci.xml",
        "scripts/export_openapi.py",
        "needs: quality",
        "mlops-flight-delay:${{ github.sha }}",
    )

    for fragment in required_fragments:
        assert fragment in workflow, f"CI contract is missing: {fragment}"


def test_ci_workflow_avoids_unsafe_or_mutable_defaults() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request_target" not in workflow
    assert "mlops-flight-delay:latest" not in workflow
    assert "persist-credentials: false" in workflow
