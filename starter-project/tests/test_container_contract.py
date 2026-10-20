from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_dockerfile_has_quality_and_runtime_contract() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "AS quality" in dockerfile
    assert "AS runtime" in dockerfile
    assert "python -m pytest -q" in dockerfile
    assert "python -m mlops_flight_delay.validate_data" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/readyz" in dockerfile
    assert ":latest" not in dockerfile


def test_compose_applies_runtime_restrictions() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert not compose.lstrip().startswith("version:")
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:" in compose and "- ALL" in compose
    assert "tmpfs:" in compose
    assert "/readyz" in compose
    assert ":latest" not in compose


def test_dockerignore_excludes_sensitive_and_generated_content() -> None:
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {".git", ".env", "models", "reports", "mlruns"} <= ignored
    assert "src" not in ignored
    assert "tests" not in ignored
    assert "data" not in ignored
