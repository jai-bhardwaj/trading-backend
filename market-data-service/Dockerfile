# Market Data Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY market-data-service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service-specific files
COPY market-data-service/ /app/market-data-service/

# Create non-root user first
RUN useradd --create-home --shell /bin/bash marketdata

# Create necessary directories and set ownership
RUN mkdir -p /app/data /app/market-data-service/logs && \
    chown -R marketdata:marketdata /app && \
    chmod -R 755 /app/market-data-service/logs

# Switch to non-root user
USER marketdata

# Set working directory to market-data-service
WORKDIR /app/market-data-service

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["python", "/app/market-data-service/main.py"]
