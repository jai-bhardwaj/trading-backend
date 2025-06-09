import asyncio
import uuid
import time
from app.database import get_database_manager, initialize_database
from app.models.base import Order
from app.queue.redis_client import get_redis_connection
from app.services.order_db_sync_worker import db_sync_worker

async def main():
    print("🧪 Testing complete DB sync system...")
    
    # Ensure DB is initialized
    await initialize_database()
    db_manager = get_database_manager()
    redis_client = get_redis_connection()

    # Start the DB sync worker
    print("🔄 Starting DB sync worker...")
    sync_task = asyncio.create_task(db_sync_worker())
    
    # Give it a moment to start
    await asyncio.sleep(1)

    # First, create a test user in the database (to satisfy foreign key constraint)
    from app.models.base import User
    test_user_id = "test_user_123"
    async with db_manager.get_async_session() as session:
        existing_user = await session.get(User, test_user_id)
        if not existing_user:
            test_user = User(
                id=test_user_id,
                email="test@example.com",
                username="testuser123",
                hashed_password="dummy_hash",
                first_name="Test",
                last_name="User"
            )
            session.add(test_user)
            await session.commit()
            print(f"✅ Created test user {test_user_id}")

    # Create a test order
    order_id = str(uuid.uuid4())
    order_key = f"order:{order_id}"
    order_data = {
        "id": order_id,
        "user_id": "test_user_123",
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "side": "BUY",
        "order_type": "MARKET",
        "product_type": "INTRADAY",
        "quantity": "100",
        "price": "2500.0",
        "status": "PENDING",
        "created_at": time.strftime('%Y-%m-%dT%H:%M:%S'),
        "worker_id": "test_worker"
    }
    
    # Add to Redis and mark for sync
    redis_client.hset(order_key, mapping=order_data)
    redis_client.sadd("orders:pending_sync", order_id)
    print(f"✅ Test order {order_id} added to Redis and marked for sync.")

    # Wait for the sync worker to process it
    print("⏳ Waiting 5 seconds for DB sync worker to process...")
    await asyncio.sleep(5)

    # Check if the order is in the database
    async with db_manager.get_async_session() as session:
        db_order = await session.get(Order, order_id)
        if db_order:
            print(f"🎉 SUCCESS! Order {order_id} was synced to the database!")
            print(f"📊 Order details: symbol={db_order.symbol}, quantity={db_order.quantity}, price={db_order.price}, status={db_order.status}")
            print(f"📊 User ID: {db_order.user_id}, Exchange: {db_order.exchange}")
        else:
            print(f"❌ FAILED! Order {order_id} was NOT found in the database.")
    
    # Check if it was removed from pending sync set
    pending_count = redis_client.scard("orders:pending_sync")
    print(f"📈 Pending sync orders remaining: {pending_count}")
    
    # Stop the sync worker
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        print("🛑 DB sync worker stopped.")
    
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 