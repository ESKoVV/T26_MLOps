# Чек-лист итогового учебного выпуска

- [ ] Release tag и source commit неизменяемы и совпадают с manifest.
- [ ] Data/feature contracts, dataset identity и point-in-time audit указаны.
- [ ] MLflow run, exact model version, alias `champion` и resolved URI согласованы.
- [ ] Image использует digest или commit-SHA tag; `latest` отсутствует.
- [ ] OpenAPI version и результат contract tests зафиксированы.
- [ ] CI run успешен; автор и release reviewer различаются.
- [ ] Drift/quality decision, governance и capacity evidence имеют SHA-256.
- [ ] Исключение имеет причину, владельца и срок пересмотра.
- [ ] Security, licenses, model/data cards и ограничения актуальны.
- [ ] Rollback указывает точные предыдущие model/image identities.
- [ ] Демонстрация и индивидуальные evidence cards воспроизводимы.
- [ ] После rollback выполнены smoke/readiness checks и записано решение.

GitHub artifact attestation является дополнительным доказательством происхождения build, но не
доказывает безопасность или качество артефакта. Если команда её использует, сохраняются команда и
результат `gh attestation verify`.
