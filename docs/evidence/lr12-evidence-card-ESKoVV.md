# Evidence card ЛР12 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР12: Monitoring (в ЛР10 — registry)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/19
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/20
- Контрольная версия: tag `lr12-v1` (ставится после review и merge)

## Личный вклад

1. Сборщик журналов мониторинга из BTS и champion.
2. Политика под реальную модель.
3. Отчёты baseline / weekend-shift / late-labels.

## Инженерное решение

Drift без падения качества — расследование, а не переобучение.

## Риск или ошибка

Метрика по неполным меткам; при coverage 0.80 решение `hold`.

## Воспроизведение

`python scripts/build_monitoring_window.py data/bts/atl_2026.csv models/lr10-a.joblib data/monitoring/bts/baseline --reference-end 2026-02-05 --current-start 2026-02-17 --current-end 2026-02-28`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
