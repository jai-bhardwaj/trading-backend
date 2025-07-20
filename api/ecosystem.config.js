module.exports = {
  apps: [
    {
      name: 'fastapi-backend',
      script: 'uvicorn',
      args: 'api.main:app --host 0.0.0.0 --port 8000 --reload',
      interpreter: '/root/trading-backend/venv/bin/python',
      cwd: '../',
      watch: false,
      env: {
        "PYTHONPATH": "."
      }
    },
    {
      name: 'trading-engine',
      script: 'main.py',
      interpreter: '/root/trading-backend/venv/bin/python',
      cwd: '../',
      watch: false,
      env: {
        "PYTHONPATH": ".",
        "LOG_LEVEL": "INFO"
      }
    }
  ]
}; 