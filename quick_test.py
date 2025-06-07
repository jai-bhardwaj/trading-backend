#!/usr/bin/env python3
"""
Quick test to verify trading engine is working
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def main():
    """Quick test of core functionality"""
    print("🚀 Quick Trading Engine Test")
    print("=" * 40)
    
    try:
        # Test 1: Configuration
        print("1️⃣ Testing Configuration...")
        from app.core.config import get_settings
        settings = get_settings()
        print(f"   ✅ Environment: {settings.environment}")
        print(f"   ✅ Debug: {settings.debug}")
        
        # Test 2: Database initialization
        print("\n2️⃣ Testing Database Initialization...")
        from app.database import initialize_database
        db_manager = await initialize_database()
        print("   ✅ Database manager initialized")
        
        # Test 3: Health check
        print("\n3️⃣ Testing Health Check...")
        health = await db_manager.health_check()
        print(f"   Database: {'✅ OK' if health['database']['healthy'] else '❌ FAILED'}")
        print(f"   Redis: {'✅ OK' if health['redis']['healthy'] else '❌ FAILED'}")
        
        if not health['overall_healthy']:
            if not health['database']['healthy']:
                print(f"   Database Error: {health['database']['error']}")
            if not health['redis']['healthy']:
                print(f"   Redis Error: {health['redis']['error']}")
        
        # Test 4: Security (if encryption key is set)
        print("\n4️⃣ Testing Security...")
        try:
            from app.core.security import check_security_configuration, encrypt_credential, decrypt_credential
            if check_security_configuration():
                test_data = "test_credential"
                encrypted = encrypt_credential(test_data)
                decrypted = decrypt_credential(encrypted)
                if decrypted == test_data:
                    print("   ✅ Encryption working")
                else:
                    print("   ❌ Encryption failed")
            else:
                print("   ⚠️ Encryption key not configured")
        except Exception as e:
            print(f"   ❌ Security test failed: {e}")
        
        # Test 5: Broker initialization
        print("\n5️⃣ Testing Broker...")
        try:
            from app.brokers.angelone_new import AngelOneBroker
            broker = AngelOneBroker()
            print("   ✅ AngelOne broker can be initialized")
        except Exception as e:
            print(f"   ❌ Broker test failed: {e}")
        
        # Test 6: Strategy registry
        print("\n6️⃣ Testing Strategy Registry...")
        try:
            from app.strategies import get_strategy_registry
            registry = get_strategy_registry()
            strategies = registry.get_all_strategies()
            print(f"   ✅ {len(strategies)} strategies loaded")
            for category, strats in strategies.items():
                if strats:
                    print(f"      {category}: {len(strats)} strategies")
        except Exception as e:
            print(f"   ❌ Strategy registry test failed: {e}")
        
        # Cleanup
        await db_manager.close()
        
        print("\n" + "=" * 40)
        if health['overall_healthy']:
            print("🎉 Core systems are working!")
            print("\n📚 Ready to start trading engine:")
            print("   • Start with: python3 main.py")
            print("   • Or use PM2: python3 manage.py start")
            print("   • View logs: python3 manage.py logs")
            print("   • Check status: python3 manage.py status")
        else:
            print("⚠️ Some issues detected - check database/Redis connections")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 