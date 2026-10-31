# Контракт API и совместимость изменений

Сервис: FastAPI `Flight Delay Predictor`, OpenAPI `info.version` 1.1.0, схема — `reports/openapi/lr7-openapi.json`.
Request принимает только признаки, известные за 60 минут до вылета: `dep_hour` (0–23), `is_weekend` (0/1).
Поля из будущего (`arr_delay`, `actual_delay`) отклоняются как неизвестные (422, `extra_forbidden`).

| Status | Когда | Тело |
|---:|---|---|
| 200 | прогноз выполнен | `PredictionResponse` |
| 404 | нет такого endpoint | `ErrorResponse`, `http_error` |
| 422 | JSON не соответствует схеме | `ErrorResponse`, `validation_error`, `details[].location` |
| 500 | необработанная ошибка (дефект) | `ErrorResponse`, `internal_error`, без текста исключения |
| 503 | процесс жив, модель не загружена | `ErrorResponse`, `not_ready` |

`X-Request-ID`: принимается значение `[A-Za-z0-9._:-]{1,128}`, иначе сервис создаёт UUID. Значение
возвращается в header и в `request_id` тела — и в успешных ответах, и в ошибках, включая 500.

## Таблица совместимости

| Изменение | Тип | Почему | Что делать |
|---|---|---|---|
| новое необязательное поле в response | совместимое | клиенты игнорируют лишние поля ответа | minor-версия API |
| новый endpoint | совместимое | старые вызовы не меняются | minor |
| новое **обязательное** поле в request | ломающее | старые клиенты получат 422 | major или поле с default |
| новое необязательное поле в request | совместимое только с default | без default старые запросы ломаются | minor + тест на старый payload |
| сужение диапазона (`dep_hour` 0–22) | ломающее | ранее валидные запросы дают 422 | major |
| расширение диапазона | совместимое для клиентов | но модель не видела таких значений | minor + проверка модели |
| переименование поля (`delay_probability` → `p`) | ломающее | клиенты не найдут поле | major, период двойной выдачи |
| смена смысла `threshold` или порога 0.5 | ломающее по смыслу | `delayed` меняется без смены схемы | major + release notes |
| изменение текста `message` | совместимое | клиенты завязаны на `error_code` и status | patch |
| новый `error_code` | условно совместимое | клиент должен обрабатывать неизвестный код | minor |
| 200 с полем `error` вместо 4xx/5xx | запрещено | status — часть контракта | — |

## HTTP smoke (2026-10-28)

Запуск на локальном uvicorn (Docker на машине тимлида временно недоступен, проверка в контейнере — в ЛР6):

```bash
python -m mlops_flight_delay.train --data data/bts/atl_2026.csv --model models/model.joblib --max-depth 8
uvicorn mlops_flight_delay.api:app --host 127.0.0.1 --port 8080
python scripts/export_openapi.py --output reports/openapi/lr7-openapi.json
python scripts/api_contract_smoke.py --base-url http://127.0.0.1:8080 --output reports/api/lr7-contract-smoke.json
```

Результат `reports/api/lr7-contract-smoke.json`: passed 4 из 4 — `valid` 200, `hour_out_of_range` 422,
`unknown_field` 422, `wrong_type` 422; `X-Request-ID` совпал во всех ответах.

Ограничение: `model_version` берётся из формата bundle (`0.2.0`) и одинаков для моделей на образце и на BTS.
Идентичность конкретной модели (registry version, commit) появится в ЛР10.
