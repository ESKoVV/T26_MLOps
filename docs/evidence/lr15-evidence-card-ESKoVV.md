# Evidence card ЛР15 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР15: Capacity (в ЛР14 — governance)
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/25
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/26
- Контрольная версия: tag `lr15-v1` (ставится после review и merge)

## Личный вклад

1. Три профиля steady/burst, recovery 1.74 с.
2. Эксперименты по одному фактору: 2 worker, меньшая модель.
3. Review `k8s/`: digest вместо tag, `/tmp` для read-only FS, CPU request.

## Инженерное решение

2 replicas по одному worker: узкое место — CPU одного процесса (GIL).

## Риск или ошибка

Масштабирование без подтверждённого bottleneck; решение основано на экспериментах.

## Воспроизведение

`bash scripts/lr15_capacity_experiments.sh`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
