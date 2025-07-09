#!/bin/bash

# Setup systemd service for trading backend
echo "Setting up systemd service for trading backend..."

# Copy service file to systemd directory
cp trading-backend.service /etc/systemd/system/

# Reload systemd daemon
systemctl daemon-reload

# Enable the service
systemctl enable trading-backend

echo "Systemd service setup complete!"
echo "To start the service: sudo systemctl start trading-backend"
echo "To check status: sudo systemctl status trading-backend"
echo "To view logs: sudo journalctl -u trading-backend -f" 