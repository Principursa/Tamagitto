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

# Create tables directly using SQLAlchemy (skip Alembic for now)
echo "Creating database tables..."
uv run -- python -c "
from database import Base, engine
from models.user import User
from models.repository import Repository
from models.entity import Entity
from models.commit_analysis import CommitAnalysis
from models.health_history import HealthHistory
from models.user_session import UserSession

print('Creating all tables...')
Base.metadata.create_all(bind=engine)
print('Tables created successfully!')

# Verify tables exist
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT tablename FROM pg_tables WHERE schemaname = \'public\''))
    tables = [row[0] for row in result]
    print('Tables in database:', sorted(tables))
"

# Start the application
echo "Starting FastAPI application..."
exec uv run -- uvicorn main:app --host 0.0.0.0 --port 8000 --reload