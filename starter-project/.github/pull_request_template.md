## Связанная задача

Closes #[номер issue]

## Что изменено

- [кратко перечислите изменения]

## Как проверить

```bash
python -m ruff check .
python -m ruff format --check .
python -m mlops_flight_delay.validate_data --data data/flights_sample.csv --contract data/contract.json --report reports/validation/local.json
python -m pytest -q --junitxml=reports/tests/local.xml
python scripts/export_openapi.py --output reports/openapi/local-openapi.json
docker build --tag mlops-flight-delay:local .
```

## Запуски CI

- успешный run после исправления: [ссылка и run ID]
- намеренно неуспешный run: [ссылка и run ID]
- ожидаемо упавший step и корневая причина: [описание]
- исправление: [commit]

## Контроль автора

- [ ] Изменение относится только к указанной issue.
- [ ] Секреты, персональные данные, `.env`, модели и локальное окружение не добавлены.
- [ ] README или другая документация обновлены при изменении способа запуска.
- [ ] Я указал риск или ограничение изменения.
- [ ] Проверки `quality` и `container` завершились успешно; обход или повтор без причины не использовался.
- [ ] История контролируемого отказа сохранена и связана с моей evidence card.

## Evidence

[ссылки на Actions run, загруженный artifact, отчёт и индивидуальную evidence card]
