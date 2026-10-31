# Evidence card ЛР13 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР13: Features (в ЛР12 — monitoring)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/21
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/22
- Контрольная версия: tag `lr13-v1` (ставится после review и merge)

## Личный вклад

1. Аудит проверяет `maximum_missing_rate` и завершается ненулевым кодом при `fail`.
2. История признаков перевозчика с available time D+1 06:00.
3. Оценка утечки: point-in-time 0.581, same-day 0.683, naive 0.517.

## Инженерное решение

Признак доступен только после ночного batch; прогноз в 04:00 берёт позавчерашний день.

## Риск или ошибка

Same-day join завышает AUC на 0.10; ловит `point_in_time_leakage_rows`.

## Воспроизведение

`python -m mlops_flight_delay.features --entities data/features/bts/entities.csv --history data/features/bts/history.csv --contract features/feature_contract_bts.json --output-dir reports/features/lr13-bts`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
