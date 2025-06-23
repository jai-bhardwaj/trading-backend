#!/bin/bash

# Simple Trading Backend Deployment
set -e

echo "🚀 SIMPLE TRADING BACKEND DEPLOYMENT"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please create your .env file with configuration"
    exit 1
fi

echo "✅ Environment configuration found"

# Check Docker
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Load environment variables
source .env

# Validate critical variables
required_vars=("DATABASE_URL" "REDIS_URL" "JWT_SECRET" "ENCRYPTION_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf "   - %s\n" "${missing_vars[@]}"
    echo ""
    echo "Please add these to your .env file"
    exit 1
fi

echo "✅ All required environment variables present"
echo ""

# Stop existing deployment
echo "🛑 Stopping existing deployment..."
docker-compose down 2>/dev/null || true

# Deploy system
echo "🚀 Deploying trading backend..."
docker-compose up -d --build

echo "⏳ Waiting for services to start..."
sleep 20

# Health checks
echo "🏥 Checking service health..."
echo ""

# Check trading backend
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Trading Backend: HEALTHY"
    echo "   📍 API: http://localhost:8000"
    echo "   📖 Docs: http://localhost:8000/docs"
else
    echo "❌ Trading Backend: UNHEALTHY"
    echo "   Checking logs..."
    docker-compose logs trading-backend | tail -10
fi

# Check Redis
if docker exec trading-redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis: HEALTHY"
else
    echo "❌ Redis: UNHEALTHY"
fi

echo ""
echo "🎯 DEPLOYMENT COMPLETE"
echo "====================="
echo ""
echo "📊 Service URLs:"
echo "   • Trading API: http://localhost:8000"
echo "   • Health Check: http://localhost:8000/health"
echo "   • API Documentation: http://localhost:8000/docs"
echo ""
echo "📝 Management Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop system: docker-compose down"
echo "   • Restart: ./deploy.sh"
echo ""
echo "🎉 Trading backend is ready!" 