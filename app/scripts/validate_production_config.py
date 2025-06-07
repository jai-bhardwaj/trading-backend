#!/usr/bin/env python3
"""
Production Environment Configuration Validator

This script validates that all required environment variables and configurations
are properly set for production deployment of the trading engine.
"""

import os
import sys
import logging
import asyncio
from typing import Dict, List, Tuple, Any
from pathlib import Path
import redis
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionValidator:
    """Validates production environment configuration."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed_checks: List[str] = []
        
    def add_error(self, message: str):
        """Add a critical error."""
        self.errors.append(message)
        logger.error(f"❌ {message}")
    
    def add_warning(self, message: str):
        """Add a warning."""
        self.warnings.append(message)
        logger.warning(f"⚠️  {message}")
    
    def add_success(self, message: str):
        """Add a successful check."""
        self.passed_checks.append(message)
        logger.info(f"✅ {message}")
    
    def validate_required_env_vars(self) -> bool:
        """Validate all required environment variables."""
        logger.info("🔍 Validating required environment variables...")
        
        required_vars = {
            # Database
            'DATABASE_URL': 'PostgreSQL database connection string',
            'REDIS_URL': 'Redis connection string',
            
            # Security
            'SECRET_KEY': 'Application secret key for JWT tokens',
            'ENCRYPTION_KEY': 'Master encryption key for sensitive data',
            
            # Environment
            'ENVIRONMENT': 'Application environment (production)',
            
            # Optional but recommended
            'SENTRY_DSN': 'Error tracking with Sentry (optional)',
            'LOG_LEVEL': 'Application log level (optional)',
        }
        
        all_present = True
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                if var in ['SENTRY_DSN', 'LOG_LEVEL']:
                    self.add_warning(f"Optional environment variable {var} not set: {description}")
                else:
                    self.add_error(f"Required environment variable {var} not set: {description}")
                    all_present = False
            else:
                self.add_success(f"Environment variable {var} is set")
                
                # Validate specific values
                if var == 'ENVIRONMENT' and value.lower() != 'production':
                    self.add_warning(f"ENVIRONMENT is set to '{value}', expected 'production'")
                elif var == 'SECRET_KEY' and len(value) < 32:
                    self.add_error(f"SECRET_KEY is too short ({len(value)} chars), minimum 32 characters required")
                elif var == 'ENCRYPTION_KEY' and len(value) < 32:
                    self.add_error(f"ENCRYPTION_KEY is too short ({len(value)} chars), minimum 32 characters required")
        
        return all_present
    
    def validate_broker_config(self) -> bool:
        """Validate broker configuration."""
        logger.info("🔍 Validating broker configuration...")
        
        # Angel One broker config
        angel_vars = [
            'ANGEL_ONE_API_KEY',
            'ANGEL_ONE_CLIENT_ID', 
            'ANGEL_ONE_PASSWORD',
            'ANGEL_ONE_TOTP_SECRET'
        ]
        
        angel_configured = all(os.getenv(var) for var in angel_vars)
        
        if angel_configured:
            self.add_success("Angel One broker configuration is complete")
            
            # Validate TOTP secret format
            totp_secret = os.getenv('ANGEL_ONE_TOTP_SECRET')
            if totp_secret and len(totp_secret) < 16:
                self.add_warning("ANGEL_ONE_TOTP_SECRET seems too short for a valid TOTP secret")
                
        else:
            missing_vars = [var for var in angel_vars if not os.getenv(var)]
            self.add_warning(f"Angel One broker not fully configured. Missing: {', '.join(missing_vars)}")
        
        return True  # Broker config is optional
    
    def validate_notification_config(self) -> bool:
        """Validate notification service configuration."""
        logger.info("🔍 Validating notification configuration...")
        
        # Email configuration (SendGrid)
        sendgrid_vars = ['SENDGRID_API_KEY', 'SENDGRID_FROM_EMAIL']
        sendgrid_configured = all(os.getenv(var) for var in sendgrid_vars)
        
        if sendgrid_configured:
            self.add_success("SendGrid email configuration is complete")
        else:
            self.add_warning("SendGrid email not configured - email notifications will be disabled")
        
        # SMS configuration (Twilio)
        twilio_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']
        twilio_configured = all(os.getenv(var) for var in twilio_vars)
        
        if twilio_configured:
            self.add_success("Twilio SMS configuration is complete")
        else:
            self.add_warning("Twilio SMS not configured - SMS notifications will be disabled")
        
        return True  # Notification config is optional
    
    async def validate_database_connection(self) -> bool:
        """Validate database connectivity."""
        logger.info("🔍 Validating database connection...")
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            self.add_error("DATABASE_URL not set - cannot test database connection")
            return False
        
        try:
            # Test database connection
            engine = create_engine(database_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                if result.fetchone()[0] == 1:
                    self.add_success("Database connection successful")
                    
                    # Test if required tables exist
                    try:
                        conn.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
                        self.add_success("Database schema appears to be initialized")
                    except Exception:
                        self.add_warning("Database schema may not be initialized - run migrations")
                    
                    return True
                else:
                    self.add_error("Database connection test failed")
                    return False
                    
        except Exception as e:
            self.add_error(f"Database connection failed: {e}")
            return False
    
    async def validate_redis_connection(self) -> bool:
        """Validate Redis connectivity."""
        logger.info("🔍 Validating Redis connection...")
        
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            self.add_error("REDIS_URL not set - cannot test Redis connection")
            return False
        
        try:
            redis_client = redis.from_url(redis_url)
            pong = redis_client.ping()
            
            if pong:
                self.add_success("Redis connection successful")
                
                # Test Redis operations
                test_key = "production_validation_test"
                redis_client.set(test_key, "test_value", ex=10)
                retrieved = redis_client.get(test_key)
                
                if retrieved and retrieved.decode() == "test_value":
                    self.add_success("Redis read/write operations working")
                    redis_client.delete(test_key)
                    return True
                else:
                    self.add_error("Redis read/write test failed")
                    return False
            else:
                self.add_error("Redis ping failed")
                return False
                
        except Exception as e:
            self.add_error(f"Redis connection failed: {e}")
            return False
    
    def validate_security_config(self) -> bool:
        """Validate security configuration."""
        logger.info("🔍 Validating security configuration...")
        
        # Check if debug mode is disabled
        debug = os.getenv('DEBUG', 'false').lower()
        if debug in ['true', '1', 'yes']:
            self.add_error("DEBUG mode is enabled in production - this is a security risk")
        else:
            self.add_success("DEBUG mode is properly disabled")
        
        # Check secret key strength
        secret_key = os.getenv('SECRET_KEY')
        if secret_key:
            if len(secret_key) >= 64:
                self.add_success("SECRET_KEY has good length")
            elif len(secret_key) >= 32:
                self.add_warning("SECRET_KEY meets minimum length but could be longer")
            else:
                self.add_error("SECRET_KEY is too short for production use")
        
        # Check if HTTPS is enforced
        force_https = os.getenv('FORCE_HTTPS', 'false').lower()
        if force_https in ['true', '1', 'yes']:
            self.add_success("HTTPS enforcement is enabled")
        else:
            self.add_warning("HTTPS enforcement not explicitly enabled")
        
        return len(self.errors) == 0
    
    def validate_performance_config(self) -> bool:
        """Validate performance-related configuration."""
        logger.info("🔍 Validating performance configuration...")
        
        # Check worker configuration
        workers = os.getenv('WORKERS')
        if workers:
            try:
                worker_count = int(workers)
                if worker_count >= 2:
                    self.add_success(f"Worker count is set to {worker_count}")
                else:
                    self.add_warning(f"Worker count is low ({worker_count}) for production")
            except ValueError:
                self.add_warning(f"Invalid WORKERS value: {workers}")
        else:
            self.add_warning("WORKERS not set - will use default")
        
        # Check connection pool settings
        pool_size = os.getenv('DB_POOL_SIZE')
        if pool_size:
            try:
                pool_count = int(pool_size)
                if 5 <= pool_count <= 50:
                    self.add_success(f"Database pool size is reasonable: {pool_count}")
                else:
                    self.add_warning(f"Database pool size may need adjustment: {pool_count}")
            except ValueError:
                self.add_warning(f"Invalid DB_POOL_SIZE value: {pool_size}")
        
        return True
    
    def validate_file_permissions(self) -> bool:
        """Validate file and directory permissions."""
        logger.info("🔍 Validating file permissions...")
        
        # Check if .env file has restrictive permissions
        env_file = Path('.env')
        if env_file.exists():
            stat = env_file.stat()
            # Check if file is readable by others (octal 044)
            if stat.st_mode & 0o044:
                self.add_warning(".env file has overly permissive permissions")
            else:
                self.add_success(".env file has appropriate permissions")
        else:
            self.add_warning(".env file not found")
        
        # Check log directory permissions
        log_dir = Path('logs')
        if log_dir.exists():
            if log_dir.is_dir() and os.access(log_dir, os.W_OK):
                self.add_success("Log directory is writable")
            else:
                self.add_error("Log directory is not writable")
        else:
            self.add_warning("Log directory does not exist")
        
        return True
    
    async def run_all_validations(self) -> bool:
        """Run all validation checks."""
        logger.info("🚀 Starting production environment validation...")
        logger.info("=" * 60)
        
        # Load environment variables
        load_dotenv()
        
        # Run validation checks
        self.validate_required_env_vars()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("🏁 Validation Summary")
        logger.info("=" * 60)
        
        logger.info(f"✅ Passed checks: {len(self.passed_checks)}")
        logger.info(f"⚠️  Warnings: {len(self.warnings)}")
        logger.info(f"❌ Errors: {len(self.errors)}")
        
        if self.errors:
            logger.error("\n🚨 Critical Issues Found:")
            for error in self.errors:
                logger.error(f"   • {error}")
        
        if self.warnings:
            logger.warning("\n⚠️  Warnings:")
            for warning in self.warnings:
                logger.warning(f"   • {warning}")
        
        # Determine overall result
        is_production_ready = len(self.errors) == 0
        
        if is_production_ready:
            logger.info("\n🎉 Environment is PRODUCTION READY!")
        else:
            logger.error(f"\n🚫 Environment is NOT production ready. Please fix {len(self.errors)} critical issues.")
        
        return is_production_ready

async def main():
    """Main validation function."""
    validator = ProductionValidator()
    
    try:
        is_ready = await validator.run_all_validations()
        sys.exit(0 if is_ready else 1)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 