# Enterprise-Grade Base Image for Pinnacle Trading Platform
# Built with Google/Meta production standards
FROM python:3.11-slim as base

# Metadata for enterprise tracking
LABEL maintainer="Pinnacle Trading Team"
LABEL version="1.0.0"
LABEL description="High-Performance Trading Platform"
LABEL org.opencontainers.image.source="https://github.com/pinnacle-trading"

# Enterprise security hardening
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    netcat-traditional \
    redis-tools \
    postgresql-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r trading && useradd --no-log-init -r -g trading trading

# Production-grade Python optimizations
ENV PYTHONOPTIMIZE=2
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# High-performance runtime settings
ENV MALLOC_ARENA_MAX=2
ENV PYTHONMALLOC=malloc

# Enterprise-grade performance configuration
ENV HTTP_POOL_SIZE=2000
ENV HTTP_POOL_PER_HOST=500
ENV MAX_CONCURRENT_REQUESTS=5000
ENV WORKER_THREADS=64
ENV DB_POOL_MIN_SIZE=20
ENV DB_POOL_MAX_SIZE=100
ENV REDIS_POOL_SIZE=50
ENV REDIS_MAX_MEMORY=1024mb
ENV ENABLE_COMPRESSION=true
ENV GRPC_MAX_WORKERS=100

# Security configurations
ENV SECURE_SSL_REDIRECT=true
ENV SESSION_COOKIE_SECURE=true
ENV CSRF_COOKIE_SECURE=true

WORKDIR /app

# Copy requirements with layer caching
COPY requirements.txt .

# Enterprise-grade dependency installation
RUN pip install --no-cache-dir --upgrade pip==24.0 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        prometheus-client==0.20.0 \
        opentelemetry-api==1.24.0 \
        opentelemetry-sdk==1.24.0 \
        structlog==24.1.0

# Create required directories
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R trading:trading /app

# Switch to non-root user
USER trading

# Health check configuration
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command can be overridden
CMD ["python", "-c", "print('Enterprise base image ready')"] 