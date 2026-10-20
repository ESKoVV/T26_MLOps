# SLI/SLO Flight Delay API

Версия: шаблон ЛР11. Замените учебные значения обоснованными значениями команды.

## Availability

- Population: валидные запросы `POST /predict` за 15 минут.
- Good event: HTTP status не относится к 5xx.
- SLI: доля good events в population.
- SLO: не менее 99% при минимум 50 запросах.
- PromQL: зафиксируйте запрос с явным окном.
- Ограничение: отсутствие трафика не доказывает доступность.

## Latency

- Population: валидные запросы `POST /predict` за 15 минут.
- Good event: duration не более 0.5 секунды.
- SLI: доля good events; дополнительный диагностический показатель — p95.
- SLO: не менее 95% good events при минимум 50 запросах.
- PromQL: зафиксируйте запрос к histogram buckets.
- Ограничение: `histogram_quantile` оценивает quantile внутри выбранных buckets.

## Владелец и реакция

- Владелец:
- Связанные alerts:
- Runbook: `docs/runbooks/flight-delay-api.md`.
- Release manifest:
- Условие завершения инцидента:
