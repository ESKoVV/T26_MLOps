# ЛР8 — review CI quality gates и failure evidence

**Issue:** [#37](https://github.com/ESKoVV/T26_MLOps/issues/37)  
**Роль:** Documentation and risk reviewer  
**Reviewed base:** `ESKoVV/T26_MLOps:student-04`  
**Base commit:** `c0341095f8df196dad6e693eed6e029d97bd4648`  
**Review type:** статический анализ GitHub workflow и документации; без изменения CI и без запуска контролируемого отказа.

## Итог

Workflow задаёт понятную последовательность `quality -> container`, а evidence card и PR template требуют связать контролируемый отказ с исправлением и успешным запуском. При этом обнаружены существенные риски воспроизводимости и сохранности evidence. Наиболее конкретный блокирующий риск — JUnit XML направляется в `reports/tests/`, но в проверенном snapshot каталог не присутствует и перед запуском pytest явно не создаётся.

## Findings

### R1 — High: JUnit XML output directory is not provisioned

**Observation.** В `.github/workflows/ci.yml` шаг Run tests запускает `pytest -q --junitxml=reports/tests/ci.xml`. В `README.md` приведена аналогичная команда с `reports/tests/lr5-pass.xml`. В проверенном Git snapshot `student-04` каталог `reports/tests/` отсутствует; перед pytest нет шага `mkdir -p reports/tests`. В PR template также предлагается писать JUnit XML в этот каталог.

**Risk.** Если родительский каталог отсутствует на чистом checkout, pytest не сможет открыть целевой XML-файл. Это может завершить quality job ошибкой до получения полноценного тестового результата и заблокировать downstream job `container`.

**Recommendation.** Создавать `reports/tests/` перед pytest в CI и добавить тот же шаг в локальную инструкцию. Либо направлять XML в уже гарантированно существующий каталог. После исправления подтвердить поведение отдельным CI run; в рамках этого review ошибка не воспроизводилась.

### R2 — Medium: push trigger не покрывает интеграционную ветку student-04

**Observation.** Workflow запускается на `push` только для `main`, на `pull_request` без фильтра по целевым веткам и через `workflow_dispatch`. Командный процесс использует промежуточную интеграционную ветку `student-04`.

**Risk.** PR в `student-04` должен запускать workflow через событие `pull_request`, но обычный push непосредственно в `student-04` не запускает CI по push trigger. Если команда ожидает проверки после каждого обновления интеграционной ветки, конфигурация этого не обеспечивает.

**Recommendation.** Явно согласовать модель: либо добавить `student-04` в push branches, либо документировать, что проверки интеграционной ветки выполняются только в PR context. Отдельно проверить фактическую настройку required status checks для целевой ветки.

### R3 — Medium: concurrency cancellation может прервать evidence run

**Observation.** Группа concurrency задаётся как `${{ github.workflow }}-${{ github.ref }}`, а `cancel-in-progress: true` отменяет предыдущий запуск в той же группе при появлении нового.

**Risk.** Повторный push или запуск на том же ref может отменить предыдущий run. Для обычной CI-экономии это ожидаемое поведение, но для контролируемого отказа может усложнить получение завершённого диагностического лога и полного artifact. `if: always()` помогает выполнить upload step после обычной ошибки, но не гарантирует наличие полного отчёта при отмене job/runner.

**Recommendation.** В инструкции ЛР8 требовать фиксировать run ID и статус, отличать `failure` от `cancelled`, а для персонального failure-evidence использовать отдельную ветку/ref или отдельный workflow/concurrency group, не запускающийся повторно на том же ref до сохранения доказательств.

### R4 — Medium: artifact retention ограничен 14 днями и покрывает только reports/

**Observation.** Шаг Upload quality evidence выполняется с `if: always()`, загружает `reports/`, задаёт `if-no-files-found: warn` и `retention-days: 14`. Логи шагов Actions в этот artifact явно не включены.

**Risk.** После истечения retention artifact перестаёт быть доступным через Actions. Кроме того, если нужный отчёт не был создан или каталог пуст, upload завершится предупреждением, а не гарантированным наличием диагностического файла. Сам artifact не заменяет ссылку на run и step logs.

**Recommendation.** В evidence card и инструкции явно разделить: ссылка/run ID, job/step logs и скачанный artifact. Участнику следует сохранять необходимые файлы в долговременном учебном хранилище в соответствии с правилами команды и не включать секреты. Рассмотреть срок хранения, соответствующий длительности курса, если это допускают настройки репозитория.

### R5 — Medium: evidence card не фиксирует все атрибуты воспроизводимости запуска

**Observation.** Карточка требует ссылку и run ID неуспешного запуска, ожидаемый step и exit code/diagnostic, root cause, fixing commit, успешный run и artifact. Однако в явном виде не требует event type, branch/ref, tested commit SHA, workflow run attempt и идентификацию сохранённых файлов/их checksum.

**Risk.** Run ID полезен для поиска, но без ref и SHA сложнее доказать, какой именно код проверялся, особенно при повторных попытках или нескольких запусках на одной ветке. Одного общего artifact name недостаточно, если нужно показать конкретный диагностический файл.

**Recommendation.** Дополнить карточку полями event, branch/ref, tested commit SHA, run attempt, failed job/step, artifact download date и перечнем проверенных файлов. Для пары отказ/исправление явно связать failing SHA с fixing commit и успешным run.

### R6 — Low: правила защиты ветки описаны, но фактическое enforcement не подтверждено review snapshot

**Observation.** `CONTRIBUTING.md` называет правила `main` рекомендуемыми и требует PR, независимое approval, resolved discussions и checks `quality`/`container`. Документ также допускает, что тариф GitHub может не позволять применить часть настроек технически. Статический просмотр workflow и документации не показывает фактическую конфигурацию ruleset/branch protection.

**Risk.** Документированное требование не доказывает, что GitHub действительно блокирует merge при красном check, отсутствии approval или unresolved discussion.

**Recommendation.** Приложить безопасное доказательство фактических branch protection/ruleset settings либо зафиксировать в evidence, какие ограничения реализованы технически, а какие обеспечиваются только командным процессом. Не обходить защиту для демонстрации.

## Положительные практики

- `container` зависит от `quality` через `needs: quality`, поэтому контейнерная проверка не стартует после неуспешного quality job.
- В quality job явно заданы timeout и последовательные quality/smoke steps.
- `Upload quality evidence` использует `if: always()`, что позволяет попытаться загрузить уже сформированные отчёты после обычного падения предыдущего шага.
- Checkout использует `persist-credentials: false`, а workflow ограничивает token permission до `contents: read`.
- Evidence card требует индивидуальный контролируемый отказ и успешное исправление; README запрещает переносить намеренный дефект в принимаемую версию.
- PR template просит связать два CI run, ожидаемо упавший step и fixing commit.

## Evidence gaps и ограничения проверки

- Ветка `student-04` проверена на commit `c0341095f8df196dad6e693eed6e029d97bd4648`; review не утверждает, что более поздние изменения отсутствуют.
- Получить список PR-triggered workflow runs для этого commit через доступный интерфейс не удалось: результат пустой. Это не доказывает, что в репозитории нет других Actions runs.
- Фактические branch protection/ruleset settings и список required checks не подтверждены статическим просмотром файлов.
- Не запускались pytest, Ruff, Docker, workflow_dispatch или контролируемый отказ.
- Не скачивались artifacts и не проверялись логи реальных run.
- Не проверялись доступность GitHub-hosted runners, внешних actions/images и поведение workflow на текущем runner image.
- Не изменялись workflow, исходный код, чужие ветки или существующие CI evidence.

## Checklist для автора ЛР8

- [ ] Создать и сохранить собственный намеренно неуспешный CI run; указать URL, run ID, ref и commit SHA.
- [ ] Показать ожидаемо упавший step, exit code/diagnostic и объяснить root cause.
- [ ] Сохранить ссылку на artifact и скачать нужные файлы до истечения срока хранения.
- [ ] Выполнить исправление отдельным commit и связать его с failing run.
- [ ] Показать успешный run после исправления и успешные обязательные checks.
- [ ] Подтвердить, что PR не может быть принят при красном required check и что approval выполнен другим участником.
- [ ] Не удалять ветку и не переписывать историю намеренно неуспешного запуска до защиты.

---

**Вывод:** базовая архитектура gates и направление evidence workflow понятны, но прежде всего необходимо устранить/проверить создание каталога JUnit XML и сделать доказательства отказа устойчивыми к отмене run и истечению срока хранения artifact. Все выводы ограничены статическим snapshot; фактические CI результаты и enforcement правил ветки не подтверждались.
