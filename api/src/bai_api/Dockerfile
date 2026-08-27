FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
COPY packages/platform-py /app/packages/platform-py
COPY apps/api /app/apps/api
RUN uv sync --frozen --no-dev --package bai-api

# Never run as root.
RUN useradd --create-home --uid 10001 bai
USER bai

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uv","run","uvicorn","bai_api.main:app","--host","0.0.0.0","--port","8000"]
