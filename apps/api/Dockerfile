# Cloudflare Containers pulls a linux/amd64 image. Build for that explicitly
# if you are on an Apple Silicon machine.
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /srv

# Dependency layer first, so app edits do not reinstall the world.
COPY pyproject.toml ./
RUN uv pip compile pyproject.toml -o /tmp/requirements.txt \
 && uv pip install --system --no-cache -r /tmp/requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY app ./app

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000

# Single worker. The Container instance is the unit of scale here, not the
# process pool, and Cloudflare bills active CPU.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--no-access-log", "--proxy-headers"]
