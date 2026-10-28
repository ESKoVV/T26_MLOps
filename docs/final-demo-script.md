# Сценарий итоговой демонстрации

1. Показать release tag, commit и `reports/releases/lr16-manifest.json`.
2. Воспроизвести окружение и выполнить data/feature validation.
3. Показать MLflow exact version и разрешение alias `champion`.
4. Запустить контейнер по immutable image ref; проверить `/healthz`, `/readyz`, `/metrics`.
5. Выполнить валидный и невалидный API-запрос, показать request ID и безопасный лог.
6. Показать monitoring/governance/capacity решения и известное ограничение.
7. Выполнить контролируемый rollback на точную предыдущую model/image identity.
8. Подтвердить smoke/readiness после rollback и вернуть согласованное состояние.

Командная демонстрация рассчитана на 10–12 минут. Затем каждый участник за 3–4 минуты показывает
личный артефакт и выполняет диагностическую операцию преподавателя.
