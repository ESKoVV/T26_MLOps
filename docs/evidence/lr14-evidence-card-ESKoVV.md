# Evidence card ЛР14 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР14: Governance (в ЛР13 — features)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/23
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/24
- Контрольная версия: tag `lr14-v1` (ставится после review и merge)

## Личный вклад

1. Model card 2.0.0 по реальной модели (в 1.0.0 была «логистическая регрессия»).
2. Порог 0.19 выбран на validation; групповой аудит IsWeekend.
3. Threat model, поиск секретов, лицензии.

## Инженерное решение

F1 gap 0.256 — `accepted_with_investigation` с владельцем и сроком, а не подгонка порогов по группам на test.

## Риск или ошибка

Разрыв качества по сегментам; отчёт `lr14-bts.json` даёт `review`.

## Воспроизведение

`python -m mlops_flight_delay.governance --evaluation data/governance/bts_evaluation.csv --policy governance/responsible_ai_policy_bts.json --model-card docs/model-card.md --output reports/governance/lr14-bts.json`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
