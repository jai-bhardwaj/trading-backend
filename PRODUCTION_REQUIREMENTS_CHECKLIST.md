# 📋 Production Requirements Checklist

## ✅ Things YOU Need to Provide/Configure

### 🔧 1. Server & Infrastructure Setup

**DigitalOcean Droplet (or similar VPS):**
- [ ] Create Ubuntu 22.04 LTS droplet (minimum 4GB RAM, 2 vCPU)
- [ ] Configure SSH access with your SSH key
- [ ] Note down your server IP address
- [ ] (Optional) Set up a domain name pointing to your server IP

**Example DigitalOcean Setup:**
```bash
# After creating droplet, SSH into it:
ssh root@your-server-ip

# Then run the deployment scripts
```

### 🗃️ 2. Database Configuration

**You need to provide your actual database credentials in `.env.production`:**

```bash
# Replace these with your REAL database details:
DATABASE_URL=postgresql+asyncpg://your_username:your_password@your_db_host:5432/your_db_name

# If using DigitalOcean Managed Database:
DATABASE_URL=postgresql+asyncpg://doadmin:your_password@your-cluster-do-user-123456-0.b.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

**Required Database Info:**
- [ ] Database username
- [ ] Database password  
- [ ] Database host/URL
- [ ] Database name
- [ ] SSL settings (usually `sslmode=require` for managed databases)

### 🔑 3. Angel One Broker Credentials

**You MUST provide your actual Angel One credentials:**

```bash
# Replace with your REAL Angel One account details:
ANGEL_ONE_API_KEY=your_actual_api_key
ANGEL_ONE_CLIENT_ID=your_actual_client_id
ANGEL_ONE_PASSWORD=your_actual_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret  # If using TOTP
```

**Where to get these:**
- [ ] Log into Angel One developer portal
- [ ] Create API app and get API key
- [ ] Note your client ID
- [ ] Your trading password
- [ ] (Optional) TOTP secret for two-factor auth

### 🔒 4. Security Configuration

**Generate secure secrets:**

```bash
# Generate strong secrets (you can use online generators):
SECRET_KEY=your-super-long-random-secret-key-minimum-32-characters
JWT_SECRET_KEY=another-long-random-jwt-secret-key-for-tokens
MASTER_ENCRYPTION_KEY=base64-encoded-32-byte-key-for-credential-encryption
```

**How to generate them:**
```bash
# On your local machine or server:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # For SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # For JWT_SECRET_KEY
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"  # For MASTER_ENCRYPTION_KEY
```

### 🌐 5. Domain & SSL Configuration (Optional but Recommended)

**If you want a domain name:**
- [ ] Purchase a domain (e.g., mytrading.com)
- [ ] Point domain to your server IP in DNS settings
- [ ] Update Nginx configuration with your domain

**Update in `/etc/nginx/sites-available/trading-backend`:**
```bash
# Replace this line:
server_name your-domain.com;

# With your actual domain:
server_name mytrading.com;
```

### 📧 6. Notification Configuration (Optional)

**For email alerts and notifications:**
```bash
# Email settings (optional):
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=alerts@yourdomain.com
```

### 📱 7. PM2 Plus Setup (Optional but Recommended)

**For advanced monitoring with mobile app:**
- [ ] Sign up at https://app.pm2.io
- [ ] Create a server bucket
- [ ] Get your secret and public keys
- [ ] Run: `pm2 link <secret_key> <public_key>`

### 🔥 8. Firewall Configuration

**Open required ports on your server:**
```bash
# Essential ports:
sudo ufw allow 22        # SSH
sudo ufw allow 80        # HTTP
sudo ufw allow 443       # HTTPS (SSL)

# Monitoring ports (optional, for external access):
sudo ufw allow 3000      # Grafana
sudo ufw allow 9000      # Portainer
sudo ufw allow 19999     # Netdata

sudo ufw enable
```

### 📊 9. Monitoring Database Credentials

**Update monitoring configuration with your database details:**

**In `/opt/monitoring/docker-compose.yml`:**
```yaml
# Replace this line in postgres-exporter:
environment:
  - DATA_SOURCE_NAME=postgresql://your_username:your_password@your_host:5432/your_db_name?sslmode=require
```

### 🚀 10. Git Repository (For Auto-Deployment)

**If you want automated deployments:**
- [ ] Push your code to a Git repository (GitHub, GitLab, etc.)
- [ ] Update `ecosystem.config.js` deployment section:

```javascript
deploy: {
  production: {
    user: 'root',
    host: ['your-actual-server-ip'],
    ref: 'origin/main',
    repo: 'https://github.com/yourusername/your-repo.git',  // Your actual repo
    path: '/root/trading-backend',
    'post-deploy': 'pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production'
  }
}
```

## 📝 Complete Configuration Template

**Here's your complete `.env.production` template to fill out:**

```bash
# =============================================================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database - REPLACE WITH YOUR ACTUAL DATABASE CREDENTIALS
DATABASE_URL=postgresql+asyncpg://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:5432/YOUR_DB_NAME?sslmode=require

# Redis - REPLACE WITH YOUR ACTUAL REDIS URL  
REDIS_URL=redis://localhost:6379

# Security - GENERATE YOUR OWN SECURE SECRETS
SECRET_KEY=YOUR_32_CHAR_SECRET_KEY_HERE
JWT_SECRET_KEY=YOUR_32_CHAR_JWT_SECRET_HERE
MASTER_ENCRYPTION_KEY=YOUR_BASE64_ENCRYPTION_KEY_HERE

# Angel One - REPLACE WITH YOUR ACTUAL BROKER CREDENTIALS
ANGEL_ONE_API_KEY=YOUR_ACTUAL_ANGEL_ONE_API_KEY
ANGEL_ONE_CLIENT_ID=YOUR_ACTUAL_CLIENT_ID
ANGEL_ONE_PASSWORD=YOUR_ACTUAL_TRADING_PASSWORD
ANGEL_ONE_TOTP_SECRET=YOUR_TOTP_SECRET_IF_USING

# Trading Engine Performance
TRADING_ENGINE_WORKERS=4
TRADING_ENGINE_MAX_QUEUE_SIZE=10000

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Email Notifications (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=alerts@yourdomain.com

# Security Headers
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,your-server-ip
```

## 🎯 Quick Action Steps

**1. Server Setup:**
```bash
# Create DigitalOcean droplet and SSH in
ssh root@your-server-ip
```

**2. Clone your repository:**
```bash
git clone https://github.com/yourusername/trading-backend.git /root/trading-backend
cd /root/trading-backend
```

**3. Configure environment:**
```bash
# Copy and edit the production environment file
cp .env.example .env.production
nano .env.production  # Fill in all YOUR actual values
```

**4. Run deployment:**
```bash
sudo ./deploy_production.sh
```

**5. Setup monitoring:**
```bash
sudo ./monitoring_setup.sh
```

**6. Test everything:**
```bash
pm2 status
pm2 logs
```

## ⚠️ Important Notes

- **Never commit real credentials to Git** - use environment variables
- **Test with paper trading first** before going live
- **Backup your database** regularly
- **Monitor your system** especially during market hours
- **Keep your Angel One credentials secure**
- **Use strong passwords** for all services

## ✅ Final Checklist

Before going live, ensure you have:
- [ ] Real database credentials configured
- [ ] Angel One broker credentials working
- [ ] Generated secure secret keys
- [ ] Firewall properly configured
- [ ] Domain/SSL setup (if using)
- [ ] PM2 Plus monitoring linked (recommended)
- [ ] Backup strategy in place
- [ ] Tested with paper trading

## 🆘 If You Need Help

**Common issues and solutions:**
1. **Database connection fails**: Check your DATABASE_URL format and credentials
2. **Angel One auth fails**: Verify your API key, client ID, and password
3. **PM2 won't start**: Check logs with `pm2 logs` for specific errors
4. **Monitoring not working**: Ensure Docker is running and ports are open
5. **SSL issues**: Check domain DNS settings and certificate installation

You're all set! The scripts handle everything else automatically. 🚀 