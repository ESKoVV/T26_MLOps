# Feast demo for ЛР13

Этот каталог является необязательной демонстрацией. Обязательная сдача выполняется модулем
`mlops_flight_delay.features` и не требует локальной установки Feast.

После установки extra `feature_store` преобразуйте `data/features/history.csv` в Parquet,
запустите `feast apply`, затем вызовите `get_historical_features` с entity dataframe,
содержащим `airport_id` и `event_time`. Сравните результат с `point-in-time.csv`.

Feature service `flight_delay_v1` связывает набор признаков с версией модели. Не используйте
online retrieval для построения исторической обучающей выборки: он возвращает актуальное, а не
исторически корректное значение.
