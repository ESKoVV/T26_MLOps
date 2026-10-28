# Обзорная карточка LLMOps evaluation

LLMOps переносит знакомые инварианты курса на генеративное приложение: версионируются prompt,
system instructions, model/provider, параметры, tools, retrieval source и eval dataset. Проверяются
не только средний score, но и отдельные критические кейсы, latency, token usage и стоимость.

`llmops/eval_cases.json` — статический безопасный пример. Он не вызывает внешний API и не требует
ключа. Перед реальным запуском команда определяет scorer, порог, обработку judge disagreement,
маскирование входов/выходов и запрет отправки закрытых данных внешнему провайдеру.

MLflow GenAI Tracing может фиксировать шаги, latency и token usage, а `mlflow.genai.evaluate()` —
оценивать traces или predict function. Этот API не следует смешивать с `mlflow.models.evaluate()`
для классических ML-моделей. В ЛР15 реализация LLM-приложения не является условием допуска.
