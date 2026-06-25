FROM python:3.12-slim AS base
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools>=68 && pip install --no-cache-dir -e ".[test]"
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY tests/ tests/

FROM base AS api
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS consumer
CMD ["python", "-m", "app.consumer"]
