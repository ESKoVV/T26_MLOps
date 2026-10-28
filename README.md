# Flight Delay MLOps starter

Базовый проект для последовательного выполнения лабораторных работ курса MLOps 2026–2027.

## Быстрый старт

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
python -m mlops_flight_delay.train --data data/flights_sample.csv --model models/model.joblib
uvicorn mlops_flight_delay.api:app --host 0.0.0.0 --port 8080
```

Перед установкой активируйте окружение: `.venv\Scripts\Activate.ps1` в Windows PowerShell или `source .venv/bin/activate` в Linux и macOS.

Проверка:

```bash
pytest -q
curl http://localhost:8080/healthz
curl -X POST http://localhost:8080/predict -H "Content-Type: application/json" -d "{\"dep_hour\": 9, \"is_weekend\": 0}"
```

## Учебный контракт

- данные проверяются по контракту 2.0.0 и сортируются по `FlightDate`;
- train, validation и test образуют последовательные временные части 60/20/20 без перемешивания;
- `ArrDelay >= 15` формирует отложенную цель и не входит в признаки;
- модель загружается из пути `MODEL_PATH`, по умолчанию `models/model.joblib`;
- `/healthz` подтверждает работу процесса;
- `/readyz` возвращает успешный ответ только после загрузки модели;
- `/predict` валидирует вход и возвращает вероятность, версию модели и `request_id`;
- `/metrics` публикует счетчик запросов и latency;
- контейнер работает от непривилегированного пользователя;
- CI запускает ruff и pytest, а затем собирает образ.

Проект намеренно остается небольшим. Команды расширяют его в лабораторных работах, но сохраняют интерфейсы запуска и проверки.

Для ЛР3, ЛР4 и ЛР9 установите дополнительные наборы зависимостей:

```bash
python -m pip install -e ".[dev,data,tracking,orchestration]"
```

MLflow-запуск выполняется после старта локального Tracking Server:

```bash
python -m mlops_flight_delay.train_mlflow --data data/flights_sample.csv --contract data/contract.json --experiment mlops-group-team-flight-delay --n-estimators 80 --max-depth 3
```

Для ЛР5 модуль `mlops_flight_delay.evaluate` проверяет предусловия и вычисляет ROC AUC,
precision, recall и F1. Положительный и отрицательный отчёты формируются командами:

```bash
python -m pytest -q --junitxml=reports/tests/lr5-pass.xml
python -m pytest tests/test_evaluate.py -q
```

Намеренно внесённый дефект демонстрируется только в отдельной ветке или незакоммиченной
копии; в принимаемую версию он не попадает.

Для ЛР6 соберите и запустите проверенный контейнер:

```bash
export IMAGE_TAG="lr6-$(git rev-parse --short HEAD)"
docker compose up --build --detach
docker compose ps
python scripts/container_smoke.py --base-url http://127.0.0.1:8080 --output reports/container/lr6-smoke.json
docker compose down
```

В PowerShell используйте `$env:IMAGE_TAG = "lr6-$(git rev-parse --short HEAD)"`. Runtime
работает от UID/GID 10001, использует read-only filesystem и считается готовым только после
успешного `/readyz`.

Для ЛР7 экспортируйте OpenAPI и выполните контрактные HTTP-сценарии:

```bash
python scripts/export_openapi.py --output reports/openapi/lr7-openapi.json
python scripts/api_contract_smoke.py --base-url http://127.0.0.1:8080 --output reports/api/lr7-contract-smoke.json
```

`PredictionRequest` использует строгие integer-типы и запрещает неизвестные поля. Успешный
ответ и ошибки содержат `request_id`, совпадающий с заголовком `X-Request-ID`.

Для ЛР9 запустите локальный Prefect flow:

```bash
python -m mlops_flight_delay.orchestration \
  --data data/flights_sample.csv \
  --contract data/contract.json \
  --run-dir reports/prefect/lr9-success \
  --model models/lr9-model.joblib
```

Демонстрация контролируемого retry использует новый каталог запуска:

```bash
python -m mlops_flight_delay.orchestration \
  --data data/flights_sample.csv \
  --contract data/contract.json \
  --run-dir reports/prefect/lr9-retry \
  --model models/lr9-retry.joblib \
  --simulate-transient-failure
```

Flow выполняет `validate -> preprocess -> train -> evaluate`, сохраняет отдельные JSON-отчёты
и итоговый `run-summary.json`. Детерминированный quality-gate отказ не следует маскировать retry:
для него задайте, например, `--minimum-roc-auc 1.1` и сохраните неуспешный run как evidence.

Для ЛР10 запустите MLflow с database-backed backend:

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
```

Зарегистрируйте успешно проверенную модель как `candidate`:

```bash
python -m mlops_flight_delay.registry register \
  --tracking-uri http://127.0.0.1:5000 \
  --model-name team-03-flight-delay-classifier \
  --owner-team team-03 \
  --model models/lr9-model.joblib \
  --data reports/prefect/lr9-success/prepared.csv \
  --summary reports/prefect/lr9-success/run-summary.json \
  --source-commit 0123456789abcdef0123456789abcdef01234567 \
  --output reports/registry/lr10-candidate.json
```

После review перенесите alias `champion`, а затем отдельно отработайте rollback:

```bash
python -m mlops_flight_delay.registry promote --tracking-uri http://127.0.0.1:5000 --model-name team-03-flight-delay-classifier --data reports/prefect/lr9-success/prepared.csv --approved-by reviewer-login --output reports/releases/lr10-release.json
python -m mlops_flight_delay.registry rollback --tracking-uri http://127.0.0.1:5000 --model-name team-03-flight-delay-classifier --target-version 1 --data reports/prefect/lr9-success/prepared.csv --reason controlled-drill --approved-by operator-login --output reports/releases/lr10-rollback.json
```

Registry workflow использует aliases `candidate` и `champion`, version tags и exact model
versions. Deprecated stages `Staging` и `Production` в курсе не применяются.

Для ЛР11 подготовьте локальную конфигурацию и запустите наблюдаемый контур:

```bash
cp .env.example .env
# замените GRAFANA_ADMIN_PASSWORD и SOURCE_COMMIT
docker compose up --build --detach
docker compose ps
```

Prometheus доступен только локально на `http://127.0.0.1:9090`, Grafana — на
`http://127.0.0.1:3000`. Datasource, dashboard и alert rules загружаются из файлов в
`observability/`; ручное создание панелей не требуется.

Создайте персональный воспроизводимый профиль нагрузки:

```bash
python scripts/observability_load.py \
  --base-url http://127.0.0.1:8080 \
  --requests 100 \
  --invalid-every 10 \
  --student-id student-01 \
  --output reports/observability/lr11-student-01.json
```

HTTP-метрики используют только ограниченные labels `method`, route template и status.
`request_id`, сырые URL, пользовательские идентификаторы и признаки не являются labels.
Приложение пишет JSON-событие запроса с `request_id`, resolved model name/version и latency,
но не логирует входные признаки. Порядок реакции на alerts описан в
`docs/runbooks/flight-delay-api.md`.

Для ЛР12 сформируйте drift-отчёт и оценку качества по созревшим отложенным меткам:

```bash
python -m mlops_flight_delay.monitoring \
  --reference data/monitoring/reference.csv \
  --current data/monitoring/current.csv \
  --predictions data/monitoring/predictions.csv \
  --labels data/monitoring/labels.csv \
  --policy monitoring/drift_policy.json \
  --as-of 2026-10-20T12:00:00Z \
  --output reports/monitoring/lr12-report.json
```

Обязательный путь реализован прозрачно на pandas и NumPy. Границы числовых bins строятся
только по reference-окну; coverage считает лишь прогнозы, для которых метка уже должна была
появиться. Drift без подтверждённого падения качества приводит к расследованию, а не к
автоматическому переобучению. Для дополнительного сравнения можно установить
`python -m pip install -e ".[monitoring]"` и построить Evidently Report, сохранив версию и JSON.

Для ЛР13 сравните намеренно ошибочный latest join с point-in-time корректной выборкой:

```bash
python -m mlops_flight_delay.features \
  --entities data/features/entities.csv \
  --history data/features/history.csv \
  --contract features/feature_contract.json \
  --output-dir reports/features/lr13
```

Аудит сохраняет `naive.csv`, `point-in-time.csv` и `audit.json`. Корректный join требует, чтобы
`feature_time` и `available_time` не превышали `event_time`, а возраст признака не выходил за TTL.
Обязательная часть использует pandas. Для необязательной демонстрации Feast установите
`python -m pip install -e ".[feature_store]"` и используйте definitions из `feature_repo/`.
Историческая обучающая выборка строится через historical retrieval, а не online lookup.

Для ЛР14 выполните аудит документации и групповых метрик:

```bash
python -m mlops_flight_delay.governance \
  --evaluation data/governance/evaluation.csv \
  --policy governance/responsible_ai_policy.json \
  --model-card docs/model-card.md \
  --output reports/governance/lr14-report.json
```

Отчёт содержит общие и групповые метрики, объём каждой группы, F1 gap, результаты policy checks и
проверку обязательных разделов model card. Малые группы получают статус `insufficient_sample` и не
используются для громких выводов. `IsWeekend` — безопасный учебный операционный сегмент, а не
доказательство fairness для защищённых групп. Security, threat model, data/model cards и лицензии
являются version-controlled release evidence, а не приложением после выпуска.

Для ЛР15 сначала получите собственный профиль steady/burst на запущенном API:

```bash
python scripts/load_profile.py \
  --student-id student-01 \
  --requests-per-stage 40 \
  --steady-concurrency 2 \
  --burst-concurrency 10 \
  --output reports/capacity/lr15-student-01-raw.json
```

Затем примените общую policy:

```bash
python -m mlops_flight_delay.capacity \
  --results reports/capacity/lr15-student-01-raw.json \
  --policy capacity/load_policy.json \
  --output reports/capacity/lr15-student-01.json
```

Скрипт сохраняет сырые latency каждого запроса, concurrency, длительность, ошибки и recovery time.
Анализ использует nearest-rank p50/p95, проверяет SLO и формирует решение с учебной оценкой
стоимости. Один превышенный p95 не запускает масштабирование автоматически. `k8s/hpa.yaml` и
`k8s/pdb.yaml` предназначены для обзора/демонстрации; локальный Kubernetes не требуется. LLMOps
рассматривается через `llmops/eval_cases.json` без обращения к внешней модели или публикации ключа.

Для ЛР16 скопируйте `release/release_spec.example.json`, замените учебные identities и соберите
итоговый manifest:

```bash
python -m mlops_flight_delay.release build \
  --spec release/release_spec.json \
  --policy release/release_policy.json \
  --output reports/releases/lr16-manifest.json \
  --require-ready
python -m mlops_flight_delay.release verify \
  --manifest reports/releases/lr16-manifest.json \
  --policy release/release_policy.json
```

Manifest связывает full commit SHA, data contract, exact MLflow model version, alias `champion`,
immutable image identity, API version, CI, hashes evidence, approvals и rollback. Пример намеренно
остаётся `draft`: у него нет реального CI run и независимого approval. Gate со статусом
`accepted_with_investigation` требует причину, владельца и срок пересмотра.

## Командная работа

- задачи оформляются через `.github/ISSUE_TEMPLATE/lab-task.yml`;
- pull request заполняется по `.github/pull_request_template.md`;
- правила находятся в `CONTRIBUTING.md`;
- состав и роли фиксируются в `docs/team-roles.md`;
- решения оформляются в `docs/adr/`;
- каждый участник заполняет собственную evidence card в `docs/evidence/`.

Скопируйте `CODEOWNERS.example` в `CODEOWNERS`, заменив заполнители реальными GitHub-логинами команды.
