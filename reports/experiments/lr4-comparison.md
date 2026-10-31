# ЛР4 Сравнение двух MLflow run

- Experiment: `mlops-tmo41-team-3-flight-delay` (локальный Tracking Server, SQLite `mlflow.db`, артефакты `mlartifacts/`).
- Данные: BTS ATL v2 (`data/bts/atl_2026.csv`), DVC md5 `bb0fdbb60462dd3c4f22aea8b0aa901f`,
  SHA-256 `78721daf85b396674e95464ca6aae151dedc7db86c480d5aef881ab4187fcace`, контракт `flight-delay-bts-atl` 1.0.0.
- Git commit обоих run: `4069260be6d107fb5fd3b3fd01658692a19c3cb2`, `git.dirty=false`.
- Разбиение `chronological-60-20-20-by-date`: train 27 436 (до 2026-02-05), validation 8 867
  (02-06 — 02-16), test 9 651 (02-17 — 02-28). Test в ЛР4 не использовался.
- Меняется один параметр — `max_depth` (3 и 8); `n_estimators=120`, `random_state=42`.

| Run ID | Конфигурация | Версия данных | Validation ROC AUC | Precision | Recall | F1 | Решение |
|---|---|---|---:|---:|---:|---:|---|
| `c366ae6c809e4b6eb921b918a755787f` | RF depth 3, n 120 | v2 `bb0fdbb6` | 0.5744 | 0.000 | 0.000 | 0.000 | rejected |
| `c4027b6d09b347408e806ea00965f201` | RF depth 8, n 120 | v2 `bb0fdbb6` | 0.5761 | 0.000 | 0.000 | 0.000 | candidate |

Доля задержек в validation — 0.149, средняя предсказанная вероятность — 0.216 / 0.216.

## Гипотеза

Более глубокие деревья лучше различат сочетания часа отправления и выходного дня. Ожидали рост
validation ROC AUC не больше чем на 0.02: признаков всего два, и `DepHour` имеет 24 значения.

## Наблюдение

ROC AUC вырос на 0.0017 — в пределах шума: на 8 867 строках стандартная ошибка AUC около 0.008.
Precision, recall и F1 равны нулю у обоих run: порог 0.5 при доле положительного класса около 0.15
не срабатывает ни разу, модель всегда отвечает «без задержки». Это свойство порога, а не обучения.

## Решение

- Candidate — depth 8: ROC AUC не хуже, а при равенстве метрик берём модель, которая не упирается в
  предел глубины. Разницу нельзя считать доказанным улучшением.
- Порог 0.5 не годится для этой задачи. Выбор порога по validation (например, по F1 или по доле
  рейсов, которые диспетчер готов проверять) отложен до ЛР5/ЛР10 — test для этого не открывается.
- Реальный предел — признаки: для заметного роста нужны перевозчик, маршрут, погода и
  накопленная задержка борта, доступные к моменту прогноза.

## Отклонённые запуски

Run `60c9008b…` и `3021ed81…` (тот же код до исправления) записаны с `data.dvc_hash=unknown`: парсер
не понимал формат `.dvc` DVC 3. Они помечены `validation.status=invalid` с причиной и в сравнении
не участвуют. Метрики у них такие же — данные и параметры совпадали.

## Воспроизведение

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
python -m mlops_flight_delay.train_mlflow --data data/bts/atl_2026.csv --contract data/contract_bts.json \
  --experiment mlops-tmo41-team-3-flight-delay --n-estimators 120 --max-depth 8
python -c "import mlflow, joblib, pandas as pd; p = mlflow.artifacts.download_artifacts(run_id='c4027b6d09b347408e806ea00965f201', artifact_path='model/model.joblib'); b = joblib.load(p); print(b['model'].predict_proba(pd.DataFrame([{'DepHour': 17, 'IsWeekend': 0}]))[:, 1])"
```

Smoke-предсказание загруженной модели depth 8 для `DepHour=17, IsWeekend=0`: 0.189
(depth 3: 0.202), форма ответа `(1,)`, значение в `[0, 1]`.
