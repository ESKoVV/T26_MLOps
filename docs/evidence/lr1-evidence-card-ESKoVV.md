# Evidence card ЛР1 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР1: Release lead, repository administrator
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/1
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/2
- Контрольная версия: tag `lr1-v1` (ставится после review и merge)

## Личный вклад

1. Импорт стартового проекта в корень fork-а, ветки `student-02…05`, CODEOWNERS, ADR 0001, `docs/team-roles.md`, CONTRIBUTING.
2. Исправлены дефекты, из-за которых CI стартового проекта не проходил: нет fixture `contract_path`, `ruff format` на 16 файлах, gate Prefect на 5 строках test, skops в MLflow 3.17, полный pytest внутри Docker build.
3. `requirements.lock`: без него uv выбрал несовместимые prefect 3.8.8 и fastapi 0.162.

## Инженерное решение

Lock-файл вместо только диапазонов в pyproject: резолвер на чистой машине выбрал несовместимую пару, что видно по падению flow на старте.

## Риск или ошибка

Незакреплённые зависимости дают разный результат у участников; обнаруживается CI на Python 3.12 и установкой по README в чистом каталоге.

## Воспроизведение

`uv venv -p 3.12 .venv && uv pip install -e ".[dev,tracking,orchestration]" && ruff check . && pytest -q`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
