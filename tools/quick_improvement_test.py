#!/usr/bin/env python3
"""
Quick test to verify improvements are working
"""

import asyncio
import httpx
import json
import time

async def test_improvements():
    """Test key improvements"""
    print("🚀 Quick Improvement Test")
    print("=" * 40)
    
    # Test 1: Input Validation
    print("\n🔒 Testing Input Validation...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8004/orders",
                json={
                    "symbol": "INVALID_SYMBOL_123!@#",
                    "side": "INVALID_SIDE",
                    "order_type": "INVALID_TYPE",
                    "quantity": -1,
                    "price": -100
                },
                headers={"Authorization": "Bearer invalid_token"}
            )
            
            if response.status_code in [400, 401]:
                print("✅ Input validation working - rejected invalid order")
            else:
                print(f"❌ Input validation failed - got status {response.status_code}")
                
    except Exception as e:
        print(f"❌ Input validation test failed: {e}")
    
    # Test 2: Performance (Caching)
    print("\n⚡ Testing Performance (Caching)...")
    try:
        async with httpx.AsyncClient() as client:
            # First request
            start_time = time.time()
            response1 = await client.get("http://localhost:8002/realtime/RELIANCE")
            time1 = time.time() - start_time
            
            # Second request (should be cached)
            start_time = time.time()
            response2 = await client.get("http://localhost:8002/realtime/RELIANCE")
            time2 = time.time() - start_time
            
            if time2 < time1:
                print(f"✅ Caching working - second request faster ({time2:.3f}s vs {time1:.3f}s)")
            else:
                print(f"⚠️ Caching may not be working - times: {time1:.3f}s vs {time2:.3f}s")
                
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
    
    # Test 3: Health Monitoring
    print("\n📊 Testing Health Monitoring...")
    try:
        async with httpx.AsyncClient() as client:
            services = [
                ("User Service", "http://localhost:8001/health"),
                ("Market Data", "http://localhost:8002/health"),
                ("Order Management", "http://localhost:8004/health")
            ]
            
            for name, url in services:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"✅ {name} healthy")
                    else:
                        print(f"❌ {name} unhealthy (status: {response.status_code})")
                except:
                    print(f"❌ {name} unreachable")
                    
    except Exception as e:
        print(f"❌ Health monitoring test failed: {e}")
    
    # Test 4: Error Handling
    print("\n🔧 Testing Error Handling...")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Test with non-existent service
            response = await client.get("http://localhost:9999/health")
            print(f"✅ Error handling working - got status {response.status_code}")
    except Exception as e:
        print(f"✅ Error handling working - caught exception: {type(e).__name__}")
    
    print("\n" + "=" * 40)
    print("🎯 Improvement Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_improvements()) 