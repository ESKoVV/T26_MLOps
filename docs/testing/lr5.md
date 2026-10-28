# ЛР5 Тестирование данных, модели и pipeline

Положительный отчёт: `reports/tests/lr5-pass.xml` — 88 тестов, 0 failures, 0 errors (commit ветки lr5, Python 3.12.16).

```bash
python -m pytest -q --junitxml=reports/tests/lr5-pass.xml
python -m pytest -q tests/test_model_bundle.py::test_delay_of_exactly_15_minutes_is_positive
```

## Слои тестов

| Слой | Файлы |
|---|---|
| Unit | `test_evaluate.py`, `test_model_bundle.py::test_delay_of_exactly_15_minutes_is_positive`, `test_data_contract.py::test_split_*` |
| Contract | `test_data_contract.py`, `test_api.py`, `test_ci_contract.py`, `test_container_contract.py` |
| Model | `test_train.py`, `test_model_bundle.py` (bundle, версия, повреждённый файл) |
| Integration | `test_model_bundle.py::test_validate_train_load_predict`, `test_pipeline.py`, `test_orchestration.py`, `test_train_mlflow.py` (SQLite во временном каталоге, без сервера) |

Общие fixtures в `tests/conftest.py`: `valid_frame` (новая копия образца на каждый тест), `csv_factory`
(пишет DataFrame в `tmp_path`), `sample_data_path`, `contract_path`, `model_path`. Эталонный CSV тесты не меняют.

## Риск — тест — ожидаемый сигнал

| Риск | Тест | Ожидаемый сигнал |
|---|---|---|
| строка из будущего попала в train | `test_data_contract.py::test_split_never_cuts_inside_one_day`, `test_report_contains_chronological_split` | assertion о границе дня / `split.ordered` |
| один день разрезан между частями | `test_split_with_single_day_has_empty_parts` | `split.chronological_boundaries` = false |
| validation содержит один класс | `test_evaluate.py` (case «обоих классов») | `ValueError` |
| неверный порог цели (`> 15`) | `test_delay_of_exactly_15_minutes_is_positive` | `[0, 0, 0, 1, 1] != [0, 0, 1, 1, 1]` |
| перепутан порядок признаков | `test_bundle_predicts_one_row_with_two_class_probabilities` | assertion на `features` |
| контракт пропускает `DepHour=24` | `test_invalid_sample_values_are_rejected[hour-24-boundary]` | `passed` = true вместо false |
| схема API и bundle расходятся | `test_api_reports_the_bundle_version` | неверная версия или 503 |
| модельный файл повреждён | `test_damaged_model_file_stops_startup[garbage-bytes,empty-file]` | `RuntimeError` на старте и событие `model_load_failed` |
| CSV разошёлся с DVC-версией | `test_dvc_pointer_mismatch_is_detected` | `dvc.md5_matches` = false |
| run без обязательных tags | `test_train_mlflow.py::test_run_has_course_tags_and_artifacts` | assertion на набор tags |

## Defect injection (2026-10-28)

Каждый дефект вносился в рабочую копию, тест запускался по node ID, затем файл восстанавливался
`git checkout -- <file>`. В принимаемую версию дефекты не входят.

```text
### target >= 15 -> > 15
$ python -m pytest tests/test_model_bundle.py::test_delay_of_exactly_15_minutes_is_positive -q
E       assert [0, 0, 0, 1, 1] == [0, 0, 1, 1, 1]
E         
E         At index 2 diff: 0 != 1
E         Use -v to get more diff
### FEATURES order swapped
$ python -m pytest tests/test_model_bundle.py::test_bundle_predicts_one_row_with_two_class_probabilities -q
E       AssertionError: assert ['IsWeekend', 'DepHour'] == ['DepHour', 'IsWeekend']
E         
E         At index 0 diff: 'IsWeekend' != 'DepHour'
E         Use -v to get more diff
### one-class check removed
$ python -m pytest tests/test_evaluate.py -q
E       Failed: DID NOT RAISE <class 'ValueError'>
1 failed, 5 passed, 1 warning in 0.61s
### bundle version field removed
$ python -m pytest tests/test_model_bundle.py::test_api_reports_the_bundle_version -q
E       KeyError: 'model_version'
ERROR    mlops_flight_delay.observability:api.py:136 {"event": "model_load_failed", "error": "ValueError"}
1 failed, 1 warning in 0.96s
### DepHour=24 allowed (до исправления теста: test_course_sample_matches_contract — 1 passed, дефект не пойман)
$ python -m pytest "tests/test_data_contract.py::test_invalid_sample_values_are_rejected[hour-24-boundary]" -q
>       assert result["passed"] is False
E       assert True is False
1 failed in 0.05s
```

Находка: дефект «контракт допускает `DepHour=24`» исходно не ловился — проверялось только 25.
Добавлен граничный case `hour-24-boundary` (отдельный commit).

До ЛР5 повреждённый `model.joblib` ронял старт сырым исключением joblib/pickle. Теперь старт
останавливается контролируемым `RuntimeError` с именем файла, а в лог пишется событие `model_load_failed`
(контракт ЛР7: сервис не принимает запросы с частично инициализированным состоянием). Отсутствующий
файл — другой случай: процесс жив, `/readyz` и `/predict` отвечают 503.
