# Evidence card ЛР4 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР4: Experiment tracking (в ЛР3 — data versioning)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/7
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/8
- Контрольная версия: tag `lr4-v1` (ставится после review и merge)

## Личный вклад

1. Tag `team.code`, артефакты `run_summary.md` и `environment/requirements.lock`.
2. Исправлен `data.dvc_hash=unknown` (парсер не понимал формат DVC 3).
3. Два run: `c366ae6c` (depth 3) и `c4027b6d` (depth 8), отчёт `reports/experiments/lr4-comparison.md`.

## Инженерное решение

Меняется один параметр (`max_depth`), выбор по validation; test не открывался.

## Риск или ошибка

Run не связан с версией данных — ловит `test_dvc_hash_is_read_from_dvc3_pointer` и tags run.

## Воспроизведение

`python -m mlops_flight_delay.train_mlflow --data data/bts/atl_2026.csv --contract data/contract_bts.json --experiment mlops-tmo41-team-3-flight-delay --n-estimators 120 --max-depth 8`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
