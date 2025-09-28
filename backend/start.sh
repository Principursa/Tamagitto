#!/bin/bash

# Add debugging
echo "🚀 START SCRIPT RUNNING - $(date)"
echo "DATABASE_URL: $DATABASE_URL"
echo "Working directory: $(pwd)"
echo "Files in current dir: $(ls -la)"

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

# Check if this is the first time (no migrations directory or no .py files)
if [ ! -d "alembic/versions" ] || [ -z "$(ls alembic/versions/*.py 2>/dev/null)" ]; then
    echo "Generating initial migration..."
    echo "Directory contents: $(ls -la alembic/versions/)"
    echo "Running: uv run -- alembic revision --autogenerate -m 'Initial migration with all models'"
    uv run -- alembic revision --autogenerate -m "Initial migration with all models" 2>&1 | tee migration_output.log
    RESULT=$?
    echo "Migration generation result: $RESULT"
    if [ $RESULT -ne 0 ]; then
        echo "Migration generation failed! Output:"
        cat migration_output.log
    fi
    echo "Directory contents after: $(ls -la alembic/versions/)"
else
    echo "Migration files already exist: $(ls -la alembic/versions/)"
fi

# Run migrations
echo "Running database migrations..."
echo "Current migration files: $(ls -la alembic/versions/)"
uv run -- alembic upgrade head
echo "Migration upgrade result: $?"
echo "Checking database tables:"
uv run -- python -c "
from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT tablename FROM pg_tables WHERE schemaname = \'public\''))
    tables = [row[0] for row in result]
    print('Tables:', tables)
"

# Start the application
echo "Starting FastAPI application..."
exec uv run -- uvicorn main:app --host 0.0.0.0 --port 8000 --reload