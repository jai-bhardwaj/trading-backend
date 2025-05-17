# Use a Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Add the app directory to PYTHONPATH
ENV PYTHONPATH=/app

# Create a non-root user and set permissions
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Create a script to handle database setup and test execution
RUN echo '#!/bin/sh\n\
    echo "Waiting for database..."\n\
    while ! nc -z db 5432; do\n\
    sleep 1\ndone\n\
    echo "Creating test database..."\n\
    PGPASSWORD=postgres psql -h db -U postgres -c "CREATE DATABASE trading_test;"\n\
    echo "Running migrations..."\n\
    alembic upgrade head\n\
    echo "Running tests..."\n\
    python -m pytest app/tests/test_order_flow.py -vv --tb=long\n\
    ' > /app/run-tests.sh && \
    chmod +x /app/run-tests.sh

USER appuser

EXPOSE 8000

# The command will be specified in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]