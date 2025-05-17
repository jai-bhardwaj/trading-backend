#!/bin/sh

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready!"

# Create test database
echo "Creating test database..."
PGPASSWORD=postgres psql -h db -U postgres -c 'CREATE DATABASE trading_test;'

# Set environment variables
export PYTHONPATH=/app
export ENVIRONMENT=test
export DATABASE_URL=postgresql://postgres:postgres@db:5432/trading_test
export REDIS_URL=redis://redis:6379/0

# Update alembic.ini with test database URL
echo "Updating alembic.ini with test database URL..."
sed -i "s|sqlalchemy.url = postgresql://postgres:postgres@db:5432/trading_db|sqlalchemy.url = postgresql://postgres:postgres@db:5432/trading_test|" /app/alembic.ini

# Run migrations
echo "Running migrations..."
cd /app
alembic -c alembic.ini upgrade head

# Run tests
echo "Running tests..."
pytest app/tests/ 