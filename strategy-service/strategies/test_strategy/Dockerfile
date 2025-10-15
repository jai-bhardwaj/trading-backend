# Test Strategy Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy base strategy framework
COPY strategy-service/base/ /app/strategy-service/base/
COPY strategy-service/shared/ /app/strategy-service/shared/

# Copy strategy-specific files
COPY strategy-service/strategies/test_strategy/ /app/strategy-service/strategies/test_strategy/

# Install Python dependencies
RUN pip install --no-cache-dir redis==6.4.0

# Create non-root user
RUN useradd --create-home --shell /bin/bash strategy && \
    chown -R strategy:strategy /app

# Switch to non-root user
USER strategy

# Set Python path
ENV PYTHONPATH=/app

# Default environment variables
ENV STRATEGY_ID=test_strategy
ENV SYMBOLS=RELIANCE,TCS,INFY
ENV TEST_MODE=true
ENV SIGNAL_INTERVAL=10
ENV CAPITAL=100000
ENV MAX_QUANTITY=1000
ENV MIN_QUANTITY=1
ENV REDIS_URL=redis://redis:6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import redis; r=redis.from_url('redis://redis:6379'); r.ping()" || exit 1

# Run the strategy
CMD ["python", "/app/strategy-service/strategies/test_strategy/strategy.py"]
