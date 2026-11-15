# API + dashboard image (no training stack). The serving bundle is mounted at runtime, never baked in.
FROM python:3.12-slim

# LightGBM is not needed for serving; curl is used by the health checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home app \
    && mkdir /app && chown app /app

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Build as the unprivileged user so no slow recursive chown is needed afterwards.
USER app
WORKDIR /app
COPY --chown=app pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra dashboard --no-install-project
COPY --chown=app src ./src
COPY --chown=app app ./app
RUN uv sync --frozen --no-dev --extra dashboard

ENV PATH="/app/.venv/bin:$PATH" \
    SERVING_DIR=/app/reports/serving \
    BACKTEST_DIR=/app/reports/backtest \
    PYTHONUNBUFFERED=1

EXPOSE 8000 8501
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["uvicorn", "m5forecast.serve.api:app", "--host", "0.0.0.0", "--port", "8000"]
