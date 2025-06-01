module.exports = {
  apps: [
    {
      name: 'trading-engine',
      script: 'main.py',
      interpreter: './venv/bin/python',
      cwd: '/root/trading-backend',
      
      // Environment
      env: {
        NODE_ENV: 'production',
        ENV: 'production'
      },
      
      // Process Management
      instances: 1,
      exec_mode: 'fork',
      
      // Restart Policy
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',
      
      // Logging
      log_file: './logs/trading-engine-combined.log',
      out_file: './logs/trading-engine-out.log',
      error_file: './logs/trading-engine-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      log_type: 'json',
      
      // Advanced PM2 features
      pmx: true,
      automation: false,
      
      // Health monitoring
      health_check_grace_period: 30000,
      kill_timeout: 5000,
      
      // Environment specific config
      env_production: {
        NODE_ENV: 'production',
        ENV: 'production',
        LOG_LEVEL: 'INFO',
        DEBUG: 'False'
      },
      
      env_development: {
        NODE_ENV: 'development',
        ENV: 'development',
        LOG_LEVEL: 'DEBUG',
        DEBUG: 'True',
        watch: true
      }
    }
  ],
  
  // PM2 Deploy configuration (optional)
  deploy: {
    production: {
      user: 'root',
      host: 'localhost',
      ref: 'origin/main',
      repo: 'git@github.com:your-repo/trading-backend.git',
      path: '/root/trading-backend',
      'pre-deploy-local': '',
      'post-deploy': 'source venv/bin/activate && pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
}; 