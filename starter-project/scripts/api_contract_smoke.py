from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def call(base_url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any], str]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/predict",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Request-ID": "lr7-smoke"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
                response.headers.get("X-Request-ID", ""),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
            error.headers.get("X-Request-ID", ""),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = [
        ("valid", {"dep_hour": 9, "is_weekend": 0}, 200),
        ("hour_out_of_range", {"dep_hour": 24, "is_weekend": 0}, 422),
        ("unknown_field", {"dep_hour": 9, "is_weekend": 0, "actual_delay": 42}, 422),
        ("wrong_type", {"dep_hour": "9", "is_weekend": 0}, 422),
    ]
    results = []
    for name, payload, expected_status in cases:
        status, body, request_id = call(args.base_url, payload)
        if status != expected_status:
            raise RuntimeError(f"{name}: ожидался {expected_status}, получен {status}")
        if not request_id or body.get("request_id") != request_id:
            raise RuntimeError(f"{name}: request ID в header и body не совпадают")
        results.append(
            {
                "case": name,
                "request": payload,
                "expected_status": expected_status,
                "actual_status": status,
                "response": body,
                "x_request_id": request_id,
            }
        )

    report = {"base_url": args.base_url, "passed": len(results), "cases": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
