from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def predict(base_url: str, request_id: str, index: int) -> tuple[bool, float]:
    payload = json.dumps({"dep_hour": index % 24, "is_weekend": index % 2}).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/predict",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "X-Request-ID": request_id},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
            success = response.status == 200
    except (urllib.error.URLError, TimeoutError):
        success = False
    return success, time.perf_counter() - started


def run_stage(
    base_url: str,
    student_id: str,
    name: str,
    requests: int,
    concurrency: int,
) -> dict[str, object]:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(predict, base_url, f"lr15-{student_id}-{name}-{i:04d}", i)
            for i in range(requests)
        ]
        results = [future.result() for future in futures]
    duration = time.perf_counter() - started
    successes = sum(1 for success, _ in results if success)
    return {
        "requests": requests,
        "successes": successes,
        "errors": requests - successes,
        "duration_seconds": duration,
        "latency_seconds": [latency for _, latency in results],
        "concurrency": concurrency,
    }


def readiness_recovery(base_url: str, timeout: float = 30.0) -> float:
    started = time.perf_counter()
    consecutive = 0
    while time.perf_counter() - started <= timeout:
        try:
            with urllib.request.urlopen(f"{base_url.rstrip('/')}/readyz", timeout=2) as response:
                consecutive = consecutive + 1 if response.status == 200 else 0
        except (urllib.error.URLError, TimeoutError):
            consecutive = 0
        if consecutive >= 3:
            return time.perf_counter() - started
        time.sleep(0.5)
    return timeout


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LR15 steady and burst load profile")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--student-id", required=True)
    parser.add_argument("--requests-per-stage", type=int, default=40)
    parser.add_argument("--steady-concurrency", type=int, default=2)
    parser.add_argument("--burst-concurrency", type=int, default=10)
    parser.add_argument("--service-version", default="1.1.0")
    parser.add_argument("--image-ref", default="flight-delay-api:1.1.0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.requests_per_stage < 20 or args.steady_concurrency < 1:
        raise ValueError("Нужно минимум 20 запросов и положительная concurrency")
    if args.burst_concurrency <= args.steady_concurrency:
        raise ValueError("Burst concurrency должна быть выше steady concurrency")

    for index in range(5):
        predict(args.base_url, f"lr15-{args.student_id}-warmup-{index}", index)
    report = {
        "schema_version": "1.0.0",
        "service_version": args.service_version,
        "image_ref": args.image_ref,
        "student_id": args.student_id,
        "scenarios": {
            "steady": run_stage(
                args.base_url,
                args.student_id,
                "steady",
                args.requests_per_stage,
                args.steady_concurrency,
            ),
            "burst": run_stage(
                args.base_url,
                args.student_id,
                "burst",
                args.requests_per_stage,
                args.burst_concurrency,
            ),
        },
        "recovery_seconds": readiness_recovery(args.base_url),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
