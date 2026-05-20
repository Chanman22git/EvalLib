FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .[dev]

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY tests ./tests

EXPOSE 8001

# Tables are created on startup (see src/main.py). Alembic is available for
# explicit migrations: `docker compose run --rm governance-api alembic upgrade head`.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
