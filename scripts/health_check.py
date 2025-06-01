#!/usr/bin/env python3
"""
PM2 Health Check for Trading Engine
Simple health monitoring for PM2 integration
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import redis
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

class HealthChecker:
    """Simple health checker for PM2"""
    
    def __init__(self):
        load_dotenv()
        self.checks = {}
    
    async def check_database(self):
        """Check PostgreSQL connection"""
        try:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                return False
            
            parsed = urlparse(db_url.replace('+asyncpg', ''))
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:] if parsed.path else 'postgres',
                connect_timeout=5
            )
            conn.close()
            return True
        except:
            return False
    
    async def check_redis(self):
        """Check Redis connection"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url, socket_timeout=5)
            r.ping()
            return True
        except:
            return False
    
    async def check_environment(self):
        """Check essential environment variables"""
        required = ['DATABASE_URL', 'REDIS_URL', 'SECRET_KEY']
        return all(os.getenv(var) for var in required)
    
    async def run_checks(self):
        """Run all health checks"""
        self.checks['database'] = await self.check_database()
        self.checks['redis'] = await self.check_redis()
        self.checks['environment'] = await self.check_environment()
        
        # Calculate health score
        total = len(self.checks)
        passed = sum(self.checks.values())
        health_score = (passed / total) * 100
        
        return {
            'healthy': health_score >= 80,
            'score': health_score,
            'checks': self.checks
        }

async def main():
    """Main health check entry point"""
    checker = HealthChecker()
    result = await checker.run_checks()
    
    # Output for PM2 monitoring
    print(json.dumps(result))
    
    # Exit code for PM2
    sys.exit(0 if result['healthy'] else 1)

if __name__ == "__main__":
    asyncio.run(main()) 