from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def request_json(url: str, payload: dict[str, int] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        if response.status != 200:
            raise RuntimeError(f"Неожиданный HTTP status: {response.status}")
        return json.loads(response.read().decode("utf-8"))


def wait_until_ready(base_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            body = request_json(f"{base_url}/readyz")
            if body.get("status") == "ready":
                return
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = error
        time.sleep(0.5)
    raise TimeoutError(f"Сервис не стал ready за {timeout:.1f} с: {last_error}")


def run_smoke(base_url: str, timeout: float) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    wait_until_ready(base_url, timeout)
    prediction = request_json(f"{base_url}/predict", {"dep_hour": 9, "is_weekend": 0})
    probability = prediction.get("delay_probability")
    if not isinstance(probability, (int, float)) or not 0.0 <= probability <= 1.0:
        raise RuntimeError("delay_probability отсутствует или находится вне [0, 1]")
    if not prediction.get("model_version") or not prediction.get("request_id"):
        raise RuntimeError("Ответ не содержит model_version или request_id")
    return {
        "base_url": base_url,
        "ready": True,
        "request": {"dep_hour": 9, "is_weekend": 0},
        "response": prediction,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run_smoke(args.base_url, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
