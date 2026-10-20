from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("Список latency не должен быть пустым")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("Квантиль должен быть от 0 до 1")
    ordered = sorted(float(value) for value in values)
    if any(value < 0 or not math.isfinite(value) for value in ordered):
        raise ValueError("Latency должна содержать конечные неотрицательные значения")
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def _scenario_metrics(scenario: dict[str, Any]) -> dict[str, float | int]:
    requests = int(scenario["requests"])
    successes = int(scenario["successes"])
    errors = int(scenario["errors"])
    duration = float(scenario["duration_seconds"])
    latencies = [float(value) for value in scenario["latency_seconds"]]
    if requests <= 0 or successes < 0 or errors < 0 or successes + errors != requests:
        raise ValueError("requests должно быть положительным и равно successes + errors")
    if duration <= 0 or len(latencies) != requests:
        raise ValueError("Нужны положительная duration и одна latency на каждый запрос")
    return {
        "requests": requests,
        "successes": successes,
        "errors": errors,
        "throughput_rps": requests / duration,
        "error_rate": errors / requests,
        "p50_seconds": percentile(latencies, 0.50),
        "p95_seconds": percentile(latencies, 0.95),
        "max_seconds": max(latencies),
    }


def build_capacity_report(results: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    scenarios = results.get("scenarios", {})
    required = list(policy["required_scenarios"])
    missing = [name for name in required if name not in scenarios]
    if missing:
        raise ValueError(f"Отсутствуют обязательные сценарии: {missing}")

    metrics = {name: _scenario_metrics(scenarios[name]) for name in required}
    minimum = int(policy["minimum_requests_per_scenario"])
    checks: dict[str, bool] = {}
    for name, values in metrics.items():
        checks[f"{name}_sample_size"] = int(values["requests"]) >= minimum
        checks[f"{name}_error_rate"] = float(values["error_rate"]) <= float(
            policy["maximum_error_rate"]
        )
        checks[f"{name}_p95"] = float(values["p95_seconds"]) <= float(
            policy["maximum_p95_seconds"][name]
        )

    recovery_seconds = float(results["recovery_seconds"])
    checks["recovery_time"] = recovery_seconds <= float(policy["maximum_recovery_seconds"])
    passed = all(checks.values())
    decision = "keep_baseline" if passed else "investigate_then_scale"

    baseline_replicas = int(policy["baseline_replicas"])
    candidate_replicas = min(
        int(policy["maximum_replicas"]),
        baseline_replicas if passed else baseline_replicas + 1,
    )
    unit_cost = float(policy["estimated_replica_hour_cost"])
    hours = float(policy["monthly_hours"])
    return {
        "schema_version": "1.0.0",
        "status": "pass" if passed else "review",
        "service_version": results["service_version"],
        "image_ref": results["image_ref"],
        "student_id": results["student_id"],
        "scenarios": metrics,
        "recovery_seconds": recovery_seconds,
        "checks": checks,
        "decision": {
            "action": decision,
            "baseline_replicas": baseline_replicas,
            "candidate_replicas": candidate_replicas,
            "statement": (
                "Сначала подтвердить bottleneck профилированием; увеличение replicas не является "
                "автоматическим следствием одного превышенного p95."
            ),
        },
        "illustrative_cost": {
            "currency": policy["cost_currency"],
            "assumption": "Учебная оценка, не коммерческое предложение облачного провайдера.",
            "baseline_monthly": baseline_replicas * unit_cost * hours,
            "candidate_monthly": candidate_replicas * unit_cost * hours,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze load, recovery and capacity evidence")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    report = build_capacity_report(results, policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.enforce and report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
