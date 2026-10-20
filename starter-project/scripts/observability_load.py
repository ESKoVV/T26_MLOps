from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def request_json(url: str, payload: dict[str, object], request_id: str) -> tuple[int, float]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-Request-ID": request_id},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        error.read()
        status = error.code
    return status, time.perf_counter() - started


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction) - 1))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reproducible LR11 HTTP load")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--invalid-every", type=int, default=10)
    parser.add_argument("--student-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.requests < 1 or args.invalid_every < 2:
        raise ValueError("requests must be positive and invalid-every must be at least 2")

    statuses: dict[str, int] = {}
    durations: list[float] = []
    for index in range(args.requests):
        invalid = (index + 1) % args.invalid_every == 0
        payload = (
            {"dep_hour": 99, "is_weekend": 0}
            if invalid
            else {"dep_hour": index % 24, "is_weekend": index % 2}
        )
        status, duration = request_json(
            f"{args.base_url.rstrip('/')}/predict",
            payload,
            f"lr11-{args.student_id}-{index + 1:04d}",
        )
        statuses[str(status)] = statuses.get(str(status), 0) + 1
        durations.append(duration)

    report = {
        "schema_version": "1.0.0",
        "student_id": args.student_id,
        "base_url": args.base_url,
        "request_count": args.requests,
        "invalid_every": args.invalid_every,
        "statuses": statuses,
        "latency_seconds": {
            "mean": statistics.fmean(durations),
            "p50": percentile(durations, 0.50),
            "p95": percentile(durations, 0.95),
            "max": max(durations),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

