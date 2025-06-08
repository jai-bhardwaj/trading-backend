#!/usr/bin/env python3
"""
Setup Angel One Broker Configuration

This script helps setup Angel One broker credentials in the database
for live trading with the engine.
"""

import asyncio
import logging
import os
from passlib.context import CryptContext
from app.database import get_database_manager
from app.models.base import BrokerConfig, BrokerName, User
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def check_broker_config():
    """Check if Angel One broker configuration exists"""
    db = get_database_manager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        # Check for existing Angel One config
        result = await session.execute(
            select(BrokerConfig).where(BrokerConfig.broker_name == BrokerName.ANGEL_ONE)
        )
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            logger.info("✅ Angel One broker configuration found:")
            logger.info(f"   Client ID: {existing_config.client_id}")
            logger.info(f"   API Key: {existing_config.api_key[:10]}..." if existing_config.api_key else "   API Key: Not set")
            logger.info(f"   TOTP Secret: {'Set' if existing_config.totp_secret else 'Not set'}")
            logger.info(f"   Is Active: {existing_config.is_active}")
            return existing_config
        else:
            logger.warning("❌ No Angel One broker configuration found")
            return None

async def create_broker_config():
    """Create Angel One broker configuration"""
    logger.info("🔧 Setting up Angel One broker configuration...")
    
    # Get credentials from environment or user input
    api_key = os.getenv('ANGEL_ONE_API_KEY') or input("Enter Angel One API Key: ").strip()
    client_id = os.getenv('ANGEL_ONE_CLIENT_ID') or input("Enter Angel One Client ID: ").strip()
    password = os.getenv('ANGEL_ONE_PASSWORD') or input("Enter Angel One Password: ").strip()
    totp_secret = os.getenv('ANGEL_ONE_TOTP_SECRET') or input("Enter Angel One TOTP Secret: ").strip()
    
    if not all([api_key, client_id, password, totp_secret]):
        logger.error("❌ All credentials are required!")
        return None
    
    db = get_database_manager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        # Get first user or create default user
        user_result = await session.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.info("📝 Creating default user...")
            # Generate a secure random password for default user
            import secrets
            import string
            default_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            
            user = User(
                username="default",
                email="default@tradingengine.com",
                hashed_password=pwd_context.hash(default_password),  # Proper password hashing
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"✅ Created default user with ID: {user.id}")
            logger.warning(f"🔐 Default user password: {default_password} (Please save this securely!)")
        
        # Create broker configuration
        broker_config = BrokerConfig(
            user_id=user.id,
            broker_name=BrokerName.ANGEL_ONE,
            api_key=api_key,
            client_id=client_id,
            password=password,  # TODO: Encrypt this before storing
            totp_secret=totp_secret,  # TODO: Encrypt this before storing
            is_active=True
        )
        
        session.add(broker_config)
        await session.commit()
        await session.refresh(broker_config)
        
        logger.info("✅ Angel One broker configuration created successfully!")
        logger.info(f"   Config ID: {broker_config.id}")
        logger.info(f"   Client ID: {broker_config.client_id}")
        logger.warning("⚠️  Broker credentials stored in plain text - implement encryption for production!")
        
        return broker_config

async def test_broker_auth():
    """Test broker authentication with saved config"""
    logger.info("🔍 Testing Angel One broker authentication...")
    
    config = await check_broker_config()
    if not config:
        logger.error("❌ No broker configuration found. Please create one first.")
        return False
    
    try:
        from app.brokers.base import BrokerRegistry
        broker = BrokerRegistry.get_broker(config)
        
        # Test authentication
        auth_success = await broker.authenticate()
        
        if auth_success:
            logger.info("✅ Angel One authentication successful!")
            
            # Test getting profile
            profile = await broker.get_profile()
            logger.info(f"   Client Code: {profile.get('clientcode', 'N/A')}")
            logger.info(f"   Name: {profile.get('name', 'N/A')}")
            
            return True
        else:
            logger.error("❌ Angel One authentication failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing authentication: {e}")
        return False

async def main():
    """Main setup function"""
    logger.info("🚀 Angel One Broker Configuration Setup")
    logger.info("=" * 50)
    
    # Check existing configuration
    existing_config = await check_broker_config()
    
    if existing_config:
        choice = input("\nBroker config exists. Test authentication? (y/N): ").lower().strip()
        if choice == 'y':
            await test_broker_auth()
    else:
        choice = input("\nNo broker config found. Create new configuration? (y/N): ").lower().strip()
        if choice == 'y':
            config = await create_broker_config()
            if config:
                # Test the new configuration
                test_choice = input("\nTest the new configuration? (y/N): ").lower().strip()
                if test_choice == 'y':
                    await test_broker_auth()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Setup interrupted by user")
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}") 