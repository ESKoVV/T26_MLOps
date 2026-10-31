# Evidence card ЛР2 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР2: Quality engineer, leakage reviewer
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/3
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/4
- Контрольная версия: tag `lr2-v1` (ставится после review и merge)

## Личный вклад

1. Блок `split` в отчёте валидатора и проверка `split.chronological_boundaries`.
2. `split.py`: разбиение 60/20/20 по календарным дням — на реальных данных row-разрез резал день пополам.
3. Контракт `contract_bts.json`, сборщик фрагмента BTS, параметризованные негативные тесты.

## Инженерное решение

Граница сдвигается к началу дня, а не на строку: рейсы одного дня иначе попадают в train и validation одновременно.

## Риск или ошибка

Утечка через общий день; ловит `test_split_never_cuts_inside_one_day` и проверка порядка периодов.

## Воспроизведение

`python -m mlops_flight_delay.validate_data --data data/flights_sample.csv --contract data/contract.json`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
