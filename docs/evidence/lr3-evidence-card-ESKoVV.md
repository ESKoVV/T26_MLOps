# Evidence card ЛР3 — Еськов Владимир

- Студент: Еськов Владимир Сергеевич, группа Т.МО41, команда team-3, GitHub @ESKoVV
- Роль в ЛР3: Data versioning
- Issue: https://github.com/ESKoVV/T26_MLOps/issues/5
- Pull request: https://github.com/ESKoVV/T26_MLOps/pull/6
- Контрольная версия: tag `lr3-v1` (ставится после review и merge)

## Личный вклад

1. DVC, remote `../dvc-storage`, версии v1 `656236c` и v2 `4e0d208` фрагмента BTS.
2. Проверка `--dvc-file`: CSV сверяется с md5 из `.dvc`.
3. Протокол `docs/reproducibility/lr3.md`, восстановление обеих версий в чистом клоне.

## Инженерное решение

Реальный фрагмент BTS (public domain) вместо 24-строчного образца, который оставлен для CI.

## Риск или ошибка

Ручная правка CSV без `dvc add`: `dvc status` и `dvc.md5_matches`.

## Воспроизведение

`git switch --detach 656236c && dvc pull && sha256sum data/bts/atl_2026.csv`

## Review

Нужно review участника, который не является автором (@Babidjon1337, @HollowInsideBro или @KavaleristovaSofia).

## Использование ИИ

Claude Code (Anthropic) по поручению студента: код, тесты, запуски и документы этой ЛР. Проверено запуском: `ruff check .`, `pytest -q`, CI run по ссылке, команды воспроизведения ниже; числа в карточке взяты из сохранённых отчётов, а не написаны вручную. Перед защитой студент сам повторяет команды воспроизведения и разбирает diff.
