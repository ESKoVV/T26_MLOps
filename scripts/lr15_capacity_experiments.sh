#!/bin/bash
# LR15: recovery after restart and bottleneck experiments. Run from repo root, venv active.
set -u
SHORT=$(git rev-parse --short HEAD)
wait_ready() { local port=$1; for _ in $(seq 1 300); do curl -s -m 1 "http://127.0.0.1:$port/readyz" >/dev/null && return 0; sleep 0.1; done; return 1; }
profile() { python scripts/load_profile.py --base-url "http://127.0.0.1:$1" --student-id "$2" --requests-per-stage 200 --steady-concurrency 2 --burst-concurrency 10 --image-ref "uvicorn-local:$SHORT" --output "reports/capacity/lr15-$2-raw.json" >/dev/null && python -m mlops_flight_delay.capacity --results "reports/capacity/lr15-$2-raw.json" --policy capacity/load_policy.json --output "reports/capacity/lr15-$2.json" >/dev/null; }

# 1) recovery: stop the running single-worker service and start it again
OLD=$(pgrep -x -f ".*uvicorn mlops_flight_delay.api:app --host 127.0.0.1 --port 8080 --workers 1" | head -1)
T0=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ); S0=$(date +%s.%N)
[ -n "$OLD" ] && kill "$OLD"; sleep 0.5
MODEL_VERSION=1 uvicorn mlops_flight_delay.api:app --host 127.0.0.1 --port 8080 --workers 1 >/tmp/uvicorn-8080.log 2>&1 & NEW=$!
wait_ready 8080; T1=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ); S1=$(date +%s.%N)
python3 -c "import json,sys;print(json.dumps({'stopped_at':sys.argv[1],'ready_at':sys.argv[2],'recovery_seconds':round(float(sys.argv[4])-float(sys.argv[3]),3)}))" "$T0" "$T1" "$S0" "$S1" > reports/capacity/lr15-recovery.json
cat reports/capacity/lr15-recovery.json

# 2) two workers, same model
MODEL_VERSION=1 uvicorn mlops_flight_delay.api:app --host 127.0.0.1 --port 8081 --workers 2 >/tmp/uvicorn-8081.log 2>&1 & W2=$!
wait_ready 8081 && profile 8081 eskov-workers2; kill $W2

# 3) one worker, smaller model (registry v2: 60 trees, depth 5)
MODEL_PATH=models/lr10-b.joblib MODEL_VERSION=2 uvicorn mlops_flight_delay.api:app --host 127.0.0.1 --port 8082 --workers 1 >/tmp/uvicorn-8082.log 2>&1 & SM=$!
wait_ready 8082 && profile 8082 eskov-small-model; kill $SM
kill $NEW
