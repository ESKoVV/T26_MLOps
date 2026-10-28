# Evidence card ЛР8 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР8: CI / platform (в ЛР7 — API)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/13
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/14
- Контрольная версия: tag `lr8-v1` (ставится после review и merge)

## Личный вклад

1. Controlled failure: run 40690440467 упал на Lint (F401), исправление — зелёный run 40690653599.
2. Actions закреплены полным SHA, тест на закрепление.
3. Защита `main` и `student-*`: PR, 1 approval, required checks `quality` и `container`.

## Инженерное решение

SHA вместо major tag: tag владелец action может перенести на другой commit.

## Риск или ошибка

Подмена action; ловит `test_ci_actions_are_pinned_to_full_commit_sha`.

## Воспроизведение

Открыть run 40690440467 → step Lint → `F401 os imported but unused`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
