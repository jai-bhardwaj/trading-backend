#!/usr/bin/env python3
"""
Script to schedule instrument fetcher to run daily in the morning
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def setup_cron_job():
    """Setup cron job to run instrument fetcher daily at 6:30 AM IST"""
    
    # Get the current directory
    current_dir = Path(__file__).parent.parent.absolute()
    
    # Path to the instrument fetcher script
    fetcher_script = current_dir / "instruments" / "fetcher.py"
    
    # Path to the Python executable in virtual environment
    python_path = current_dir / "venv" / "bin" / "python"
    
    # Create the cron command
    cron_command = f"30 6 * * * cd {current_dir} && {python_path} {fetcher_script}"
    
    # Create a temporary cron file
    temp_cron_file = "/tmp/trading_cron"
    
    try:
        # Get existing cron jobs
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing_crons = result.stdout if result.returncode == 0 else ""
        
        # Check if our cron job already exists
        if "fetcher.py" not in existing_crons:
            # Add our cron job
            new_crons = existing_crons + f"\n# Trading Backend - Instrument Fetcher\n{cron_command}\n"
            
            # Write to temporary file
            with open(temp_cron_file, "w") as f:
                f.write(new_crons)
            
            # Install the new cron job
            subprocess.run(["crontab", temp_cron_file], check=True)
            
            print("✅ Cron job installed successfully!")
            print(f"📅 Instrument fetcher will run daily at 6:30 AM IST")
            print(f"🔧 Cron command: {cron_command}")
            
        else:
            print("ℹ️ Cron job already exists for instrument fetcher")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up cron job: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Clean up temporary file
        if os.path.exists(temp_cron_file):
            os.remove(temp_cron_file)
    
    return True

def remove_cron_job():
    """Remove the instrument fetcher cron job"""
    try:
        # Get existing cron jobs
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            existing_crons = result.stdout
            
            # Remove lines containing fetcher.py
            new_crons = "\n".join([line for line in existing_crons.split("\n") 
                                  if "fetcher.py" not in line and line.strip()])
            
            # Write back to crontab
            temp_cron_file = "/tmp/trading_cron_remove"
            with open(temp_cron_file, "w") as f:
                f.write(new_crons)
            
            subprocess.run(["crontab", temp_cron_file], check=True)
            os.remove(temp_cron_file)
            
            print("✅ Cron job removed successfully!")
            
        else:
            print("ℹ️ No existing cron jobs found")
            
    except Exception as e:
        print(f"❌ Error removing cron job: {e}")

def list_cron_jobs():
    """List current cron jobs"""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            print("📋 Current cron jobs:")
            print(result.stdout)
        else:
            print("ℹ️ No cron jobs found")
    except Exception as e:
        print(f"❌ Error listing cron jobs: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "install":
            setup_cron_job()
        elif command == "remove":
            remove_cron_job()
        elif command == "list":
            list_cron_jobs()
        else:
            print("Usage: python schedule_instrument_fetch.py [install|remove|list]")
    else:
        print("Trading Backend - Instrument Fetcher Scheduler")
        print("Usage: python schedule_instrument_fetch.py [install|remove|list]")
        print("\nCommands:")
        print("  install - Install cron job to run daily at 6:30 AM IST")
        print("  remove  - Remove the cron job")
        print("  list    - List current cron jobs") 