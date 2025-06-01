#!/bin/bash

# Trading Engine PM2 Deployment Script
set -e

echo "🚀 Trading Engine PM2 Deployment"
echo "================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run from the trading-backend directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found. Please create it first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Creating from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "📝 Please edit .env with your actual configuration"
    else
        echo "❌ Error: No .env.example found. Please create .env manually."
        exit 1
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "❌ Error: PM2 is not installed. Install it with:"
    echo "   npm install -g pm2"
    exit 1
fi

echo "✅ Pre-flight checks passed"

# Stop existing process if running
echo "🛑 Stopping existing process..."
pm2 stop trading-engine 2>/dev/null || echo "No existing process found"
pm2 delete trading-engine 2>/dev/null || echo "No existing process to delete"

# Start the application
echo "🚀 Starting trading engine..."
pm2 start ecosystem.config.js --env production

# Save PM2 configuration
echo "💾 Saving PM2 configuration..."
pm2 save

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Monitor the application:"
echo "   pm2 status"
echo "   pm2 logs trading-engine"
echo "   pm2 monit"
echo ""
echo "🛑 Stop the application:"
echo "   pm2 stop trading-engine" 