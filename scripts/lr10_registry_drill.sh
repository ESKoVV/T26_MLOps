#!/bin/bash
# LR10 registry drill: run from the repo root with the venv active.
set -u
SHA=$(git rev-parse HEAD); M=team-3-flight-delay-classifier; U=http://127.0.0.1:5000
R() { python -m mlops_flight_delay.registry "$@" > /tmp/step.log 2>&1; echo "exit $?"; }
REG="--tracking-uri $U --experiment mlops-tmo41-team-3-registry --model-name $M --owner-team team-3 --registered-by ESKoVV --source-commit $SHA"
mkdir -p reports/registry reports/releases
echo "== register A";  R register $REG --model models/lr10-a.joblib --data reports/prefect/lr10-run-a/prepared.csv --summary reports/prefect/lr10-run-a/run-summary.json --minimum-roc-auc 0.55 --output reports/registry/lr10-candidate-a.json
echo "== promote A by author (expect reject)"; R promote --tracking-uri $U --model-name $M --data reports/prefect/lr10-run-a/prepared.csv --approved-by ESKoVV --output reports/releases/lr10-self-approval-rejected.json
echo "== promote A drill"; R promote --tracking-uri $U --model-name $M --data reports/prefect/lr10-run-a/prepared.csv --approved-by ESKoVV --drill --output reports/releases/lr10-release-v1.json
echo "== register B";  R register $REG --model models/lr10-b.joblib --data reports/prefect/lr10-run-b/prepared.csv --summary reports/prefect/lr10-run-b/run-summary.json --minimum-roc-auc 0.55 --output reports/registry/lr10-candidate-b.json
echo "== register B with gate 0.65 (expect reject)"; R register $REG --model models/lr10-b.joblib --data reports/prefect/lr10-run-b/prepared.csv --summary reports/prefect/lr10-run-b/run-summary.json --minimum-roc-auc 0.65 --output reports/registry/lr10-rejected-gate.json
echo "== promote B drill"; R promote --tracking-uri $U --model-name $M --data reports/prefect/lr10-run-b/prepared.csv --approved-by ESKoVV --drill --output reports/releases/lr10-release-v2.json
echo "== rollback to v1"; R rollback --tracking-uri $U --model-name $M --target-version 1 --data reports/prefect/lr10-run-a/prepared.csv --reason controlled-drill --approved-by ESKoVV --output reports/releases/lr10-rollback.json
