#!/bin/sh
# Entrypoint for the fiadobot container image: applies pending Alembic
# migrations and then starts the FastAPI application. Migrations run
# automatically on every container start because this project is deployed
# as a single instance, so there is no risk of concurrent migration races.
set -e

echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head

PORT="${PORT:-8000}"
echo "Starting fiadobot on port ${PORT}..."
exec uvicorn fiadobot.main:app --host 0.0.0.0 --port "${PORT}"
