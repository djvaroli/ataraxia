FROM ghcr.io/astral-sh/uv:0.11.16 AS uv

# The Claude Code CLI, pinned by version and SHA-256 (from the release's manifest.json).
# Only the worker images copy it; the API image never contains it.
FROM python:3.12.15-slim-bookworm AS claude-cli
ARG TARGETARCH
ARG CLAUDE_CODE_VERSION=2.1.332
ARG CLAUDE_CODE_SHA256_AMD64=a2df1f41bb00250992926420d0063f89b127cb81abdd284dbefb80c50ff1d026
ARG CLAUDE_CODE_SHA256_ARM64=50c305fcb8912851ce774429131d94ed6f84edbe3d8d0ed7a59dade5d893acc0
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) platform=linux-x64; sum="$CLAUDE_CODE_SHA256_AMD64" ;; \
      arm64) platform=linux-arm64; sum="$CLAUDE_CODE_SHA256_ARM64" ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], '/claude')" \
      "https://downloads.claude.ai/claude-code-releases/$CLAUDE_CODE_VERSION/$platform/claude"; \
    echo "$sum  /claude" | sha256sum -c -; \
    chmod 0755 /claude

FROM python:3.12.15-slim-bookworm AS base
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
# Both build targets own /data (and the worker's Claude login directory) as the same
# unprivileged user, so the volumes work whichever mode created them.
RUN useradd --uid 10001 --create-home app \
    && mkdir /data /home/app/.claude && chown app:app /data /home/app/.claude
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src

# Checks run as root in this stage; compose.dev.yaml runs the services as `app`.
FROM base AS development
RUN uv sync --locked
COPY tests ./tests
ENV PATH="/app/.venv/bin:$PATH"
# No access log: query strings carry search terms. nginx logs paths without them.
CMD ["uvicorn", "ataraxia.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--no-access-log"]

FROM base AS runtime
RUN uv sync --locked --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH"
USER app
CMD ["uvicorn", "ataraxia.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

# The worker: runtime plus the CLI. The login lives on a volume at CLAUDE_CONFIG_DIR.
FROM runtime AS worker
COPY --from=claude-cli /claude /usr/local/bin/claude
ENV CLAUDE_CONFIG_DIR=/home/app/.claude DISABLE_UPDATES=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
CMD ["python", "-m", "ataraxia.worker"]

FROM development AS worker-development
COPY --from=claude-cli /claude /usr/local/bin/claude
ENV CLAUDE_CONFIG_DIR=/home/app/.claude DISABLE_UPDATES=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
CMD ["python", "-m", "ataraxia.worker"]
