FROM ghcr.io/astral-sh/uv:0.11.16 AS uv
FROM python:3.12.15-slim-bookworm AS base
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
# Both build targets own /data as the same unprivileged user, so the database volume
# works whichever mode created it.
RUN useradd --uid 10001 --create-home app && mkdir /data && chown app:app /data
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src

# Checks run as root in this stage; compose.dev.yaml runs the services as `app`.
FROM base AS development
RUN uv sync --locked
COPY tests ./tests
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "ataraxia.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS runtime
RUN uv sync --locked --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH"
USER app
CMD ["uvicorn", "ataraxia.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
