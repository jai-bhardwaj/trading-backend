module.exports = {
  apps: [
    {
      name: 'trading-engine',
      script: 'main.py',
      interpreter: './venv/bin/python',
      interpreter_args: '',
      cwd: process.cwd(),
      
      // Environment
      env: {
        NODE_ENV: 'production',
        ENV: 'production',
        PYTHONPATH: process.cwd(),
        PATH: process.cwd() + '/venv/bin:' + process.env.PATH
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
      
      // Advanced PM2 features
      pmx: false,  // Disable pmx to avoid issues
      automation: false,
      
      // Health monitoring
      kill_timeout: 5000,
      
      // Environment specific config
      env_production: {
        NODE_ENV: 'production',
        ENV: 'production',
        LOG_LEVEL: 'INFO',
        DEBUG: 'False',
        PYTHONPATH: process.cwd(),
        PATH: process.cwd() + '/venv/bin:' + process.env.PATH
      },
      
      env_development: {
        NODE_ENV: 'development',
        ENV: 'development',
        LOG_LEVEL: 'DEBUG',
        DEBUG: 'True',
        watch: false,  // Disable watch to prevent issues
        PYTHONPATH: process.cwd(),
        PATH: process.cwd() + '/venv/bin:' + process.env.PATH
      }
    }
  ],

  deploy : {
    production : {
      user : 'SSH_USERNAME',
      host : 'SSH_HOSTMACHINE',
      ref  : 'origin/master',
      repo : 'GIT_REPOSITORY',
      path : 'DESTINATION_PATH',
      'pre-deploy-local': '',
      'post-deploy' : 'npm install && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};
