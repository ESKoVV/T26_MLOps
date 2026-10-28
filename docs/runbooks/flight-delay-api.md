# Runbook: Flight Delay API

## Область

Alerts `FlightDelayServiceDown`, `FlightDelayHigh5xxRatio` и `FlightDelayHighP95Latency`.

## Первые проверки

1. Зафиксировать время, alert name, labels и текущий release manifest.
2. Проверить `docker compose ps`, `/healthz`, `/readyz` и Prometheus target status.
3. Найти JSON-логи по `request_id`, `model_name` и `model_version`.
4. Сопоставить изменение метрик с последним promotion или конфигурационным изменением.

## Диагностика

- `Down`: проверить процесс, healthcheck, сеть Compose и наличие модели.
- `High5xxRatio`: определить route/status, найти первую ошибку и связанный request ID.
- `HighP95Latency`: сравнить routes, нагрузку и время до/после выпуска.

## Безопасные действия

- остановить генератор нагрузки;
- вернуть последнюю проверенную конфигурацию;
- при связи с выпуском выполнить документированный rollback alias `champion`;
- не удалять логи, manifests и не перезапускать сервис циклически без гипотезы.

## Завершение

Убедиться, что условие alert отсутствует, `/readyz` успешен, p95 и 5xx ratio вернулись к норме.
Создать краткий incident note: причина, evidence, действие, проверка восстановления и профилактика.
