#!/usr/bin/env python3
"""
Setup environment variables for the trading system
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
def setup_environment():
    """Setup environment variables"""
    
    print("🔧 Setting up environment variables...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️ .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Setup cancelled")
            return False
    
    # Get database URL
    print("\n📊 Database Configuration:")
    print("Enter your PostgreSQL database URL:")
    print("Format: postgresql+psycopg2://username:password@host:port/database?sslmode=require")
    
    db_url = input("DATABASE_URL: ").strip()
    if not db_url:
        print("❌ DATABASE_URL is required")
        return False
    
    # Get Angel One credentials
    print("\n🔐 Angel One API Credentials:")
    api_key = input("ANGEL_ONE_API_KEY: ").strip()
    client_id = input("ANGEL_ONE_CLIENT_ID: ").strip()
    password = input("ANGEL_ONE_PASSWORD: ").strip()
    totp_secret = input("ANGEL_ONE_TOTP_SECRET: ").strip()
    
    if not all([api_key, client_id, password, totp_secret]):
        print("❌ All Angel One credentials are required")
        return False
    
    # Get Redis URL
    print("\n🔴 Redis Configuration:")
    redis_url = input("REDIS_URL (default: redis://localhost:6379/0): ").strip()
    if not redis_url:
        redis_url = "redis://localhost:6379/0"
    
    # Get trading configuration
    print("\n📈 Trading Configuration:")
    paper_trading = input("PAPER_TRADING (true/false, default: false): ").strip().lower()
    if not paper_trading:
        paper_trading = "false"
    
    execution_interval = input("EXECUTION_INTERVAL in seconds (default: 1): ").strip()
    if not execution_interval:
        execution_interval = "1"
    
    # Get logging configuration
    print("\n📝 Logging Configuration:")
    log_level = input("LOG_LEVEL (default: INFO): ").strip()
    if not log_level:
        log_level = "INFO"
    
    # Create .env file
    env_content = f"""# Trading Backend Environment Variables

# Angel One API Credentials
ANGEL_ONE_API_KEY={api_key}
ANGEL_ONE_CLIENT_ID={client_id}
ANGEL_ONE_PASSWORD={password}
ANGEL_ONE_TOTP_SECRET={totp_secret}

# Database Configuration
DATABASE_URL={db_url}

# Redis Configuration
REDIS_URL={redis_url}

# Trading Configuration
PAPER_TRADING={paper_trading}
EXECUTION_INTERVAL={execution_interval}

# Logging Configuration
LOG_LEVEL={log_level}
"""
    
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("\n✅ Environment variables saved to .env file")
        print("🔒 Make sure to keep your .env file secure and never commit it to version control")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def test_environment():
    """Test the environment setup"""
    print("\n🧪 Testing environment setup...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required variables
    required_vars = [
        "DATABASE_URL",
        "ANGEL_ONE_API_KEY", 
        "ANGEL_ONE_CLIENT_ID",
        "ANGEL_ONE_PASSWORD",
        "ANGEL_ONE_TOTP_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables are set")
    
    # Test database connection
    try:
        from shared.database import test_db_connection
        if test_db_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    print("✅ Environment setup is complete and working!")
    return True

if __name__ == "__main__":
    print("🚀 Trading System Environment Setup")
    print("=" * 50)
    
    if setup_environment():
        test_environment()
    else:
        print("❌ Environment setup failed")
        sys.exit(1) 