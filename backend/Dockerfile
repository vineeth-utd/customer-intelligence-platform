# syntax=docker/dockerfile:1

FROM python:3.14-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies reproducibly from lockfile into the project virtual environment
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# Copy application source
COPY app/ ./app/

# Copy Alembic migration tooling
COPY alembic.ini ./alembic.ini
COPY migrations/ ./migrations/

EXPOSE 8000

# Run via uv so the project virtual environment is used
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

