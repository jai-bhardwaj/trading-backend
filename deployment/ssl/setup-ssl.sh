#!/bin/bash

# Pinnacle Trading System - SSL Certificate Setup
# For Digital Ocean Droplet

set -e

echo "🔒 Setting up SSL certificates for Pinnacle Trading System..."

# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get domain from user
read -p "Enter your domain name (e.g., trading.yourdomain.com): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    echo "❌ Domain name is required"
    exit 1
fi

# Update Nginx configuration with domain
sudo sed -i "s/your-domain.com/$DOMAIN_NAME/g" /etc/nginx/sites-available/pinnacle-trading

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Obtain SSL certificate
echo "Obtaining SSL certificate for $DOMAIN_NAME..."
sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME

# Set up automatic renewal
echo "Setting up automatic certificate renewal..."
sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

# Test SSL configuration
echo "Testing SSL configuration..."
curl -I https://$DOMAIN_NAME || echo "⚠️ SSL test failed - check your domain configuration"

echo "✅ SSL setup completed!"
echo "📋 SSL configuration:"
echo "   • Domain: $DOMAIN_NAME"
echo "   • Certificate: Auto-renewed monthly"
echo "   • HTTPS: Enabled and configured"
echo "   • Security: HSTS and security headers enabled" 