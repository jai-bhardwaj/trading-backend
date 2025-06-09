# 🚀 Production Trading Engine Dockerfile
FROM python:3.12-slim-bullseye

LABEL maintainer="Trading Engine Team"
LABEL version="2.0.0"
LABEL description="High-Performance Trading Engine with Optimizations"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create non-root user for security
RUN groupadd -r trading && useradd -r -g trading trading

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY main.py .
COPY manage.py .
COPY create_tables.py .
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Copy configuration
COPY .env.example .env

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R trading:trading /app

# Switch to non-root user
USER trading

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import redis; r = redis.Redis(host='redis', port=6379); r.ping()" || exit 1

# Expose port (if needed for API)
EXPOSE 8000

# Default command
CMD ["python", "main.py"] 