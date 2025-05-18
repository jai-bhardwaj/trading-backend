#!/bin/bash

# Exit on error
set -e

# Check if required environment variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Error: Required environment variables are not set"
    echo "Please set the following environment variables:"
    echo "DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
    exit 1
fi

# Default SSL mode if not set
SSL_MODE=${SSL_MODE:-"require"}

# Instructions for database reset option
echo "=== Trading Backend Deployment Script ==="
echo "Note: By default, this script performs a safe migration that preserves your data."
echo "To reset the database (DELETE ALL DATA), run with: RESET_DB=true ./deploy-backend.sh"
echo "================================================================="

# Update system
echo "Updating system..."
sudo apt update
sudo apt upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt install -y python3-pip python3-venv nginx redis-server

# Start and enable Redis
echo "Starting Redis..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# No need to create application directory - using existing /root/trading-backend
echo "Using existing application directory: /root/trading-backend"

# No need to copy files - already in the correct directory
echo "Skipping file copy - using files in current directory"

# Create and activate virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv /root/trading-backend/venv
source /root/trading-backend/venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "Creating environment file..."
cat > /root/trading-backend/.env << EOF
PROJECT_NAME="Trading Backend"
API_V1_STR="/api/v1"
ENV="production"
DEBUG="False"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?sslmode=${SSL_MODE}"
REDIS_URL="redis://localhost:6379/0"
SECRET_KEY="$(openssl rand -hex 32)"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="1440"
EOF

# Setup Nginx
echo "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/trading-backend << EOF
server {
    listen 80;
    server_name _;

    # Backend API
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/trading-backend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Setup systemd service
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/trading-backend.service << EOF
[Unit]
Description=Trading Backend Service
After=network.target redis-server.service

[Service]
User=root
WorkingDirectory=/root/trading-backend
Environment="PATH=/root/trading-backend/venv/bin"
EnvironmentFile=/root/trading-backend/.env
ExecStart=/root/trading-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level debug
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Run database migrations
echo "Running database migrations..."
# Already in /root/trading-backend, no need to cd

# Optional database reset - only if explicitly requested
if [ "${RESET_DB}" == "true" ]; then
    echo "WARNING: You've enabled database reset. This will DELETE ALL DATA."
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        echo "Dropping existing database objects..."
        
        # Drop existing ENUM types if they exist
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TYPE IF EXISTS ordertype CASCADE;"
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TYPE IF EXISTS orderstatus CASCADE;"
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TYPE IF EXISTS strategystatus CASCADE;"

        # Drop existing tables if they exist
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TABLE IF EXISTS orders CASCADE;"
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TABLE IF EXISTS strategies CASCADE;"
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TABLE IF EXISTS users CASCADE;"
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP TABLE IF EXISTS alembic_version CASCADE;"
        
        echo "Database reset completed. Creating new migration..."
        
        # Clean up migrations directory
        rm -rf migrations_new/versions/*
        rm -rf migrations_new/versions/__pycache__ 2>/dev/null || true
        
        # Create migrations directory if it doesn't exist
        mkdir -p migrations_new/versions
        
        # Create new migration
        alembic revision --autogenerate -m "initial migration"
    else
        echo "Database reset cancelled."
        exit 1
    fi
else
    echo "Performing safe database migration (preserving existing data)..."
    
    # Check if migrations directory exists, create if needed
    if [ ! -d "migrations_new/versions" ]; then
        echo "Creating migrations directory..."
        mkdir -p migrations_new/versions
        
        # Create initial migration if no previous migrations exist
        if [ ! "$(ls -A migrations_new/versions 2>/dev/null)" ]; then
            echo "Creating initial migration..."
            alembic revision --autogenerate -m "initial migration"
        fi
    fi
fi

# Apply migration (this will safely update the schema without dropping tables)
echo "Applying migrations to database..."
alembic upgrade head

# Start the service
echo "Starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable trading-backend
sudo systemctl restart trading-backend

# Show status
echo "Checking service status..."
sudo systemctl status trading-backend

echo "Deployment completed! Your application should be running at http://localhost:8000"
echo "To check the logs, run: sudo journalctl -u trading-backend -f" 