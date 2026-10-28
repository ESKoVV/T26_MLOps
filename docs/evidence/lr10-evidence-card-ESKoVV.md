# Evidence card ЛР10 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР10: Registry / release (в ЛР9 — orchestration)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/17
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/18
- Контрольная версия: tag `lr10-v1` (ставится после review и merge)

## Личный вклад

1. Pyfunc отдавал метки вместо вероятностей → `pyfunc_predict_fn=predict_proba`.
2. `promote` отклоняет одобрение автором кандидата.
3. Две версии, champion, отказы gate, rollback v2 → v1.

## Инженерное решение

Aliases и exact versions вместо deprecated stages.

## Риск или ошибка

Самоодобрение выпуска; ловит `test_self_or_blank_approval_is_rejected`. Promotion выполнены как drill — нужен reviewer.

## Воспроизведение

`bash scripts/lr10_registry_drill.sh`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
