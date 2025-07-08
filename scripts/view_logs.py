#!/usr/bin/env python3
"""
View trading backend logs from different sources
"""

import os
import sys
import subprocess
from datetime import datetime
import argparse

def view_systemd_logs(lines=50, follow=False):
    """View systemd service logs"""
    print("📋 Systemd Service Logs:")
    print("=" * 50)
    
    cmd = ["journalctl", "-u", "trading-backend.service", "--no-pager"]
    if follow:
        cmd.append("-f")
    else:
        cmd.extend(["-n", str(lines)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"❌ Error viewing systemd logs: {e}")

def view_file_logs(log_file, lines=50):
    """View log files"""
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return
    
    print(f"📋 File Logs ({log_file}):")
    print("=" * 50)
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            if lines > 0:
                all_lines = all_lines[-lines:]
            print(''.join(all_lines))
    except Exception as e:
        print(f"❌ Error reading log file: {e}")

def view_service_status():
    """View service status"""
    print("📋 Service Status:")
    print("=" * 50)
    
    try:
        result = subprocess.run(["systemctl", "status", "trading-backend.service"], 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"❌ Error checking service status: {e}")

def find_log_files():
    """Find all log files"""
    print("📋 Available Log Files:")
    print("=" * 50)
    
    try:
        result = subprocess.run(["find", ".", "-name", "*.log", "-type", "f"], 
                              capture_output=True, text=True)
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"  - {line}")
        else:
            print("No log files found")
    except Exception as e:
        print(f"❌ Error finding log files: {e}")

def main():
    parser = argparse.ArgumentParser(description="View trading backend logs")
    parser.add_argument("--systemd", action="store_true", help="View systemd logs")
    parser.add_argument("--file", type=str, help="View specific log file")
    parser.add_argument("--status", action="store_true", help="View service status")
    parser.add_argument("--find", action="store_true", help="Find all log files")
    parser.add_argument("--follow", action="store_true", help="Follow logs in real-time")
    parser.add_argument("--lines", type=int, default=50, help="Number of lines to show")
    
    args = parser.parse_args()
    
    if args.systemd:
        view_systemd_logs(args.lines, args.follow)
    elif args.file:
        view_file_logs(args.file, args.lines)
    elif args.status:
        view_service_status()
    elif args.find:
        find_log_files()
    else:
        # Default: show all
        print("🔍 Trading Backend Logs")
        print("=" * 60)
        
        view_service_status()
        print()
        view_systemd_logs(args.lines)
        print()
        find_log_files()
        print()
        
        # Show current log file if it exists
        current_log = f"logs/{datetime.now().strftime('%Y-%m-%d')}/app.log"
        if os.path.exists(current_log):
            view_file_logs(current_log, args.lines)

if __name__ == "__main__":
    main() 