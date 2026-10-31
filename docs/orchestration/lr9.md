# ЛР9 Оркестрация обучения и обработка отказов

Flow `flight-delay-training` (Prefect 3.9.0, локальный временный сервер): `validate → preprocess → train → evaluate`
→ `run-summary.json`. Данные — BTS ATL v2 (`data/bts/atl_2026.csv`, SHA-256 `78721daf…1fcace`), контракт `contract_bts.json`,
RandomForest `n_estimators=120`, `max_depth=8` (candidate из ЛР4), `random_state=42`.

```bash
python -m mlops_flight_delay.orchestration --data data/bts/atl_2026.csv --contract data/contract_bts.json \
  --n-estimators 120 --max-depth 8 --random-state 42 --minimum-roc-auc 0.55 \
  --run-dir reports/prefect/lr9-success --model models/lr9-model.joblib
# + --simulate-transient-failure -> lr9-retry;  --minimum-roc-auc 1.1 -> lr9-quality-fail
```

| Run directory | Итог flow | Первая failed task | Исключение | Test ROC AUC | Gate |
|---|---|---|---|---:|---|
| `reports/prefect/lr9-success` | Completed | — | — | 0.6313 | passed (≥ 0.55) |
| `reports/prefect/lr9-retry` | Completed | `preprocess`, попытка 1 → Retrying → Completed | `OSError` (учебный marker `.retry-once`) | 0.6313 | passed |
| `reports/prefect/lr9-quality-fail` | Failed | `evaluate` | `ValueError: Quality gate failed: test ROC AUC 0.631 < 1.100` | 0.6313 | failed, без retry |

В каждом каталоге: `01-validation.json`, `02-preprocess.json`, `03-training.json`, `04-evaluation.json`, `flow.log`;
`run-summary.json` — только у завершённых run. В quality-fail `04-evaluation.json` записан с `passed: false`
до исключения. `prepared.csv` (1.2 МБ) в Git не хранится — воспроизводится flow, hash в `02-preprocess.json`.

## Retry policy

- `preprocess`: `retries=2`, `retry_delay_seconds=1`, `retry_condition_fn=retry_only_transient` — повтор только
  при `OSError`. До ЛР9 повторялось любое исключение, и отсутствующий столбец (`ValueError`) выполнялся трижды.
  Тест `test_deterministic_preprocess_error_is_not_retried` падает, если условие убрать (проверено).
- `validate`, `train`, `evaluate`: `retries=0`. Нарушение контракта, недопустимый параметр и недостаточная метрика —
  детерминированные ошибки: retry их не исправит, а только удлинит run.

## Идемпотентность и происхождение

Три run с одинаковыми входами дали одинаковые prepared hash и метрики (ROC AUC 0.6313). `prepared_sha256`
совпал с SHA-256 исходного CSV: файл уже отсортирован по дате, а `preprocess` теперь использует ту же стабильную
сортировку `sort_by_event_time`, что и train, и не переставляет рейсы внутри дня.

Test-период здесь используется только как gate выпуска; модель выбрана в ЛР4 по validation (depth 8).
F1 = 0 при пороге 0.5 — то же наблюдение, что в ЛР4 (доля задержек в test 0.26).
