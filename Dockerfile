# syntax=docker/dockerfile:1
FROM python:3.12-slim AS quality

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY data ./data

# The image gate runs the tests of components that ship in the runtime image. The full suite
# (registry, orchestration, governance, release ...) needs extras and repo files outside this
# context and runs in the CI quality job, which the container job depends on.
RUN python -m pip install --no-cache-dir ".[dev]" \
    && python -m ruff check src tests \
    && python -m pytest -q tests/test_api.py tests/test_data_contract.py tests/test_evaluate.py \
        tests/test_observability.py tests/test_pipeline.py tests/test_train.py \
    && python -m mlops_flight_delay.validate_data \
        --data data/flights_sample.csv \
        --contract data/contract.json \
        --report /tmp/validation.json \
    && python -m mlops_flight_delay.train \
        --data data/flights_sample.csv \
        --model /artifacts/model.joblib \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/app/models/model.joblib \
    PATH=/opt/venv/bin:$PATH

RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app --home /nonexistent --no-create-home app \
    && python -m venv /opt/venv
WORKDIR /app

COPY --from=quality /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels mlops-flight-delay-starter \
    && rm -rf /wheels

COPY --from=quality --chown=10001:10001 /artifacts/model.joblib /app/models/model.joblib
USER 10001:10001

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=2)"]
CMD ["uvicorn", "mlops_flight_delay.api:app", "--host", "0.0.0.0", "--port", "8080"]

