# Evidence card ЛР5 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР5: Quality engineer (в ЛР4 — tracking)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/9
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/10
- Контрольная версия: tag `lr5-v1` (ставится после review и merge)

## Личный вклад

1. Fixtures `valid_frame`, `csv_factory`; `delay_target()` как единое определение цели.
2. Тесты bundle, интеграции validate → train → load → predict, повреждённого файла модели.
3. Defect injection: 5 дефектов; `DepHour` max 24 изначально не ловился — добавлен граничный case.

## Инженерное решение

Повреждённый файл модели останавливает старт сервиса (контракт ЛР7), отсутствующий — 503.

## Риск или ошибка

Тест, который не ловит дефект; проверено внесением дефектов (`docs/testing/lr5.md`).

## Воспроизведение

`pytest -q "tests/test_data_contract.py::test_invalid_sample_values_are_rejected[hour-24-boundary]"`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
