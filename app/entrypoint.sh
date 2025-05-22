#!/bin/bash
set -e # Ensure script exits on error

echo "--- Entrypoint: Starting (RUN MODE V2) ---"

echo "--- Entrypoint: Waiting for database to be ready... ---"
python /app/wait_for_db.py
echo "--- Entrypoint: Database is ready. ---"

# Stamping is removed. We will rely on a clean versions directory with one initial migration.
# echo "--- Entrypoint: Stamping database with Alembic head... ---"
# /app/.venv/bin/alembic stamp head

# Autogenerate is removed. Migrations should be pre-generated and included in the image.
# echo "--- Entrypoint: Attempting to generate initial Alembic revision... ---"
# /app/.venv/bin/alembic revision -m "create_initial_tables" --autogenerate

echo "--- Entrypoint: Running Alembic migrations... ---"
# Assumes all necessary migration files (ideally one initial) are present in alembic/versions/
/app/.venv/bin/alembic upgrade head

echo "--- Entrypoint: Starting Uvicorn server... ---"
exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

echo "--- Entrypoint: Should not reach here if Uvicorn starts successfully ---" 