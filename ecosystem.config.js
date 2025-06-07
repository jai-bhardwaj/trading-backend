module.exports = {
  apps: [
    {
      name: 'trading-engine',
      script: 'main.py',
      interpreter: 'python3',
      cwd: '/root/trading-backend',
      env: {
        PYTHONPATH: '/root/trading-backend',
        PATH: '/root/trading-backend/venv/bin:' + process.env.PATH
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: './logs/trading-engine-error.log',
      out_file: './logs/trading-engine-out.log',
      log_file: './logs/trading-engine-combined.log',
      time: true
    },
    {
      name: 'trading-api',
      script: '/root/trading-backend/venv/bin/uvicorn',
      args: 'app.api.main:app --host 0.0.0.0 --port 8000 --workers 2',
      cwd: '/root/trading-backend',
      env: {
        PYTHONPATH: '/root/trading-backend',
        PATH: '/root/trading-backend/venv/bin:' + process.env.PATH
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      error_file: './logs/trading-api-error.log',
      out_file: './logs/trading-api-out.log',
      log_file: './logs/trading-api-combined.log',
      time: true
    },
    {
      name: 'strategy-monitor',
      script: 'app/monitoring/strategy_monitor.py',
      interpreter: 'python3',
      cwd: '/root/trading-backend',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        ENVIRONMENT: 'production',
        PYTHONPATH: '/root/trading-backend',
        PYTHONUNBUFFERED: '1'
      },
      log_file: '/root/trading-backend/logs/strategy-monitor.log',
      out_file: '/root/trading-backend/logs/strategy-monitor-out.log',
      error_file: '/root/trading-backend/logs/strategy-monitor-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      time: true,
      autorestart: true,
      restart_delay: 10000,
      max_restarts: 5,
      min_uptime: '30s'
    }
  ],

  deploy: {
    production: {
      user: 'root',
      host: ['your-production-server.com'],
      ref: 'origin/main',
      repo: 'git@github.com:yourusername/trading-backend.git',
      path: '/root/trading-backend',
      'pre-deploy-local': '',
      'post-deploy': 'pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': '',
      'ssh_options': 'StrictHostKeyChecking=no'
    }
  }
};
