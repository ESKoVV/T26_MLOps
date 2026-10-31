# Evidence card ЛР16 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР16: Release lead
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/27
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/28
- Контрольная версия: tag `lr16-v1` (ставится после review и merge)

## Личный вклад

1. Build сверяет заявленный статус gate с evidence.
2. Одобрение без учёта регистра логина.
3. `release/release_spec.json`, manifest и сценарий демонстрации.

## Инженерное решение

Manifest честно остаётся draft, пока нет независимого одобрения.

## Риск или ошибка

Ложный `pass` в spec; ловит `test_gate_cannot_claim_pass_over_failing_evidence`.

## Воспроизведение

`python -m mlops_flight_delay.release verify --manifest reports/releases/lr16-manifest.json --policy release/release_policy.json`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
