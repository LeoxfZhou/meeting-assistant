FROM ghcr.io/astral-sh/uv:0.10.12 AS uv
FROM python:3.13-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
RUN useradd --create-home --uid 10001 appuser
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY data/company_docs ./data/company_docs
COPY scripts ./scripts
COPY evaluation ./evaluation
RUN mkdir -p models outputs && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log"]
