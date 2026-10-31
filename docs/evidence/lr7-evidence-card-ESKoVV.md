# Evidence card ЛР7 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР7: API contract (в ЛР5 — quality)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/11
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/12
- Контрольная версия: tag `lr7-v1` (ставится после review и merge)

## Личный вклад

1. Строгий `X-Request-ID` (`[A-Za-z0-9._:-]{1,128}`), иначе UUID.
2. Необработанная ошибка отдавала текст без `request_id` → 500 `ErrorResponse`.
3. Contract tests, OpenAPI и HTTP smoke 4/4, таблица совместимости.

## Инженерное решение

Request ID — непрозрачный короткий токен: он попадает в логи и заголовки.

## Риск или ошибка

Stack trace или PII в ответе; ловит `test_internal_error_returns_500_without_stack_trace`.

## Воспроизведение

`python scripts/api_contract_smoke.py --base-url http://127.0.0.1:8080 --output reports/api/lr7-contract-smoke.json`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
