# ЛР8 Непрерывная интеграция и quality gates

Workflow `.github/workflows/ci.yml`: события `pull_request`, push в `main`, `workflow_dispatch`; `permissions: contents: read`;
concurrency `${{ github.workflow }}-${{ github.ref }}` с `cancel-in-progress`; job `quality` → job `container` (`needs: quality`),
образ `mlops-flight-delay:${{ github.sha }}` без `latest`; artifact `quality-evidence-<run_id>` (каталог `reports/`, 14 дней).

## Controlled failure и исправление (ветка `lr8/issue-13-ci`, PR #14)

| Run | Commit | Итог | Упавший step | Корневая причина |
|---|---|---|---|---|
| [40690440467](https://github.com/ESKoVV/T26_MLOps/actions/runs/40690440467) | `2d94822a0456d36c0daacb99fde42f0b7d71a0e0` | failure | `quality / Lint` (step 5); дальнейшие steps и job `container` skipped | намеренно добавлен `import os` без использования — ruff `F401` в `src/mlops_flight_delay/evaluate.py:3` |
| [40690653599](https://github.com/ESKoVV/T26_MLOps/actions/runs/40690653599) | `2c2d6cb3c610195f735e6843648129ed5f8dbef6` | success | — | исправлено commit `654ef3b` (удалён import), затем `2c2d6cb` — actions по SHA |

Ожидаемый step был назван заранее в сообщении commit (`Expected failing step: quality / Lint`). Фрагмент лога красного run:

```text
F401 [*] `os` imported but unused
 --> src/mlops_flight_delay/evaluate.py:3:8
Found 1 error.
##[error]Process completed with exit code 1.
```

Повторный запуск без изменения кода исправлением не считается; история ветки не переписывалась.

Artifact зелёного run `quality-evidence-40690653599` скачан и проверен: 28 файлов, в том числе
`validation/ci.json` (`passed: true`), `tests/ci.xml` (103 теста), `openapi/ci-openapi.json`.

## Дефекты CI, найденные до ЛР8 (PR #2)

Исходный workflow стартового проекта не проходил ни одного run: `ruff format --check` (16 файлов), отсутствующий
fixture, gate Prefect на 5 строках test, skops в MLflow 3.17, полный pytest внутри Docker build. Первые красные
run: 40686180990 (`main`), 40686793735 и 40687466651 (ЛР1).

## Закрепление actions

| Action | Major | Commit SHA |
|---|---|---|
| `actions/checkout` | v7 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | v7 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` |
| `actions/upload-artifact` | v4 | `ea165f8d65b6e75b540449e92b4886f43607fa02` |

Major tag владелец action может перенести на другой commit, поэтому один и тот же `@v7` в разные дни может
означать разный код. Полный SHA неизменяем. Тест `test_ci_actions_are_pinned_to_full_commit_sha` не даёт вернуть
ссылку по tag. Цена: обновления не приходят сами, SHA нужно обновлять осознанно (Dependabot понимает комментарий `# v7`).

## Защита веток

Настроено через API 2026-10-28 для `main` и `student-01…05`: merge только через PR; 1 approval не от автора,
устаревшие approval сбрасываются, последний push должен одобрить другой участник; required checks `quality` и
`container` (strict — ветка должна быть актуальной); обязательное разрешение обсуждений; force push и удаление запрещены.

Ограничение: `enforce_admins=false` — владелец fork-а технически может обойти правила. Процесс команды
(CONTRIBUTING) это запрещает; соблюдение видно по истории PR.
