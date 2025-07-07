#!/bin/bash

set -e

# Load environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
  echo "Starting Redis server..."
  redis-server --daemonize yes
else
  echo "Redis server already running."
fi

# Activate virtual environment if present
if [ -d "venv" ]; then
  echo "Activating virtual environment..."
  source venv/bin/activate
fi

# Install requirements if needed
if [ -f requirements.txt ]; then
  echo "Installing Python dependencies..."
  pip install -r requirements.txt
fi

# Run the main system
echo "Starting trading backend system..."
python main.py 