#!/usr/bin/env python3
"""
Trading Engine Management Script
Simplified PM2 process management for the trading engine
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        return None

def check_pm2_status():
    """Check if PM2 is installed and working"""
    if not run_command("which pm2", check=False):
        print("❌ PM2 not found. Install with: npm install -g pm2")
        return False
    return True

def check_process_status():
    """Check if trading-engine is running"""
    try:
        output = run_command("pm2 jlist", check=False)
        if output:
            processes = json.loads(output)
            for proc in processes:
                if proc.get('name') == 'trading-engine':
                    return proc.get('pm2_env', {}).get('status', 'unknown')
    except:
        pass
    return 'stopped'

def start_engine():
    """Start the trading engine"""
    print("🚀 Starting trading engine...")
    
    # Check prerequisites
    if not os.path.exists('main.py'):
        print("❌ main.py not found. Run from the correct directory.")
        return False
    
    if not os.path.exists('venv'):
        print("❌ Virtual environment not found. Create it first:")
        print("   python3 -m venv venv")
        print("   source venv/bin/activate") 
        print("   pip install -r requirements.txt")
        return False
    
    if not os.path.exists('.env'):
        print("⚠️  .env file not found. Please create one with your configuration.")
        return False
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Start with PM2
    result = run_command("pm2 start ecosystem.config.js --env production")
    if result is not None:
        print("✅ Trading engine started successfully!")
        run_command("pm2 save")
        return True
    return False

def stop_engine():
    """Stop the trading engine"""
    print("🛑 Stopping trading engine...")
    run_command("pm2 stop trading-engine", check=False)
    print("✅ Trading engine stopped")

def restart_engine():
    """Restart the trading engine"""
    print("🔄 Restarting trading engine...")
    result = run_command("pm2 restart trading-engine", check=False)
    if result is not None:
        print("✅ Trading engine restarted")
        return True
    else:
        print("⚠️  Process not running, starting fresh...")
        return start_engine()

def reload_engine():
    """Reload the trading engine (zero-downtime)"""
    print("♻️  Reloading trading engine...")
    result = run_command("pm2 reload trading-engine", check=False)
    if result is not None:
        print("✅ Trading engine reloaded")
        return True
    return False

def delete_engine():
    """Delete the trading engine process"""
    print("🗑️  Deleting trading engine process...")
    run_command("pm2 delete trading-engine", check=False)
    print("✅ Trading engine process deleted")

def show_status():
    """Show PM2 status"""
    print("📊 PM2 Status:")
    run_command("pm2 status")

def show_logs():
    """Show recent logs"""
    print("📜 Recent logs:")
    run_command("pm2 logs trading-engine --lines 50")

def monitor():
    """Open PM2 monitor"""
    print("📈 Opening PM2 monitor...")
    os.system("pm2 monit")

def main():
    """Main function"""
    if not check_pm2_status():
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("""
🔧 Trading Engine Manager

Usage: python manage.py <command>

Commands:
  start      Start the trading engine
  stop       Stop the trading engine  
  restart    Restart the trading engine
  reload     Reload the trading engine (zero-downtime)
  delete     Delete the process from PM2
  status     Show PM2 status
  logs       Show recent logs
  monitor    Open PM2 monitor
  
Current status: {}
        """.format(check_process_status()))
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        start_engine()
    elif command == 'stop':
        stop_engine()
    elif command == 'restart':
        restart_engine()
    elif command == 'reload':
        reload_engine()
    elif command == 'delete':
        delete_engine()
    elif command == 'status':
        show_status()
    elif command == 'logs':
        show_logs()
    elif command == 'monitor':
        monitor()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main() 