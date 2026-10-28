# Протокол воспроизводимости ЛР3

Набор: `data/bts/atl_2026.csv` (фрагмент BTS, вылеты из ATL), контракт `data/contract_bts.json` 1.0.0.
Remote: `course-local` → `../dvc-storage` относительно корня репозитория (каталог вне рабочего дерева).
DVC 3.67.1, Python 3.12.16.

| Версия | Git commit | DVC md5 | SHA-256 CSV | Период | Строк | Контракт | Результат |
|---|---|---|---|---|---:|---|---|
| v1 | `656236c358f4dcbf47542296058eb5df858a408b` | `89511bf17a122596d2b7a21f6a2925ac` | `0f73c37dae1a684f703d24d84b850dfd1486aef72b0ca43fe8cd7088877af1c1` | 2026-01-01 — 2026-01-31 | 23 321 | 1.0.0 | passed |
| v2 | `4e0d208dd1e65a2d0b669ea12b9a1dd98d82fa9f` | `bb0fdbb60462dd3c4f22aea8b0aa901f` | `78721daf85b396674e95464ca6aae151dedc7db86c480d5aef881ab4187fcace` | 2026-01-01 — 2026-02-28 | 45 954 | 1.0.0 | passed |

Отчёты валидации: `docs/reproducibility/lr3-v1-validation.json`, `lr3-v2-validation.json`.
Три идентификатора не заменяют друг друга: Git commit фиксирует проект, DVC md5 — объект в cache и
remote, SHA-256 из отчёта связывает конкретные байты с результатом проверки.

## Влияние v2 на разбиение

| Часть | v1 | v2 |
|---|---|---|
| train | 13 797, 01-01 — 01-18 | 27 436, 01-01 — 02-05 |
| validation | 4 774, 01-19 — 01-24 | 8 867, 02-06 — 02-16 |
| test | 4 750, 01-25 — 01-31 | 9 651, 02-17 — 02-28 |

Строки января в v2 не изменены (v1 — префикс v2). Test v1 входит в train v2: метрики разных версий
сравнивать напрямую нельзя.

## Восстановление (проверено 2026-10-28 в чистом клоне рядом с `dvc-storage`)

```bash
git clone https://github.com/ESKoVV/T26_MLOps.git && cd T26_MLOps
git switch --detach 656236c358f4dcbf47542296058eb5df858a408b   # или v2
dvc pull
sha256sum data/bts/atl_2026.csv
python -m mlops_flight_delay.validate_data --data data/bts/atl_2026.csv \
  --contract data/contract_bts.json --dvc-file data/bts/atl_2026.csv.dvc
git switch -   # вернуться в рабочую ветку
```

Результат: v1 — SHA-256 совпал, 23 321 строка, код 0; v2 — совпал, 45 954 строки, код 0.

Remote локальный: у участника без доступа к этому диску `dvc pull` не найдёт объект. Тогда файл
собирается из первоисточника и сверяется по SHA-256 из таблицы:

```bash
curl -LO https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_1.zip
python scripts/build_bts_fragment.py data/bts/atl_2026.csv On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_1.zip
```

## Отказные сценарии

1. CSV изменён вручную без `dvc add` (дописана строка). `dvc status` показывает
   `changed outs: modified: data/bts/atl_2026.csv`; валидатор с `--dvc-file` падает на `dvc.md5_matches`
   (тест `test_dvc_pointer_mismatch_is_detected`). Восстановление: `dvc checkout --force data/bts/atl_2026.csv`.
2. Восстановленная копия с нарушенным порядком дат (первая и последняя строки переставлены):
   валидатор завершается с кодом 1, падает `FlightDate.chronological_order`.
