#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
until uv run -- python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database is ready!')
except psycopg2.OperationalError:
    sys.exit(1)
"; do
  sleep 1
done

# Check if this is the first time (no migrations directory or empty)
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
    echo "Generating initial migration..."
    uv run -- alembic revision --autogenerate -m "Initial migration with all models"
fi

# Run migrations
echo "Running database migrations..."
uv run -- alembic upgrade head

# Start the application
echo "Starting FastAPI application..."
exec uv run -- uvicorn main:app --host 0.0.0.0 --port 8000 --reload