# Evidence card ЛР9 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР9: Orchestration (в ЛР8 — CI)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/15
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/16
- Контрольная версия: tag `lr9-v1` (ставится после review и merge)

## Личный вклад

1. Retry `preprocess` только при `OSError` (раньше повторялся и `ValueError`).
2. Отчёт `02-preprocess.json`, стабильная сортировка.
3. Run на BTS: success, retry, quality-fail.

## Инженерное решение

Детерминированная ошибка не повторяется: retry её не исправит.

## Риск или ошибка

Бессмысленные повторы; `test_deterministic_preprocess_error_is_not_retried` падает без условия.

## Воспроизведение

`python -m mlops_flight_delay.orchestration --data data/bts/atl_2026.csv --contract data/contract_bts.json --run-dir reports/prefect/x --model models/x.joblib --simulate-transient-failure`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
