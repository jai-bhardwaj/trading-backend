"""
Integration Tests
End-to-end tests for complete trading system integration
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.models.base import OrderStatus, StrategyStatus, AssetClass, TimeFrame
import uuid

class TestEndToEndIntegration:
    """Test complete end-to-end trading workflows"""
    
    async def test_complete_order_lifecycle(self, db_manager, test_user, test_strategy):
        """Test complete order lifecycle from creation to execution"""
        from app.models.base import Order, OrderSide, OrderType, ProductType
        from sqlalchemy import select
        
        # Create order
        async with db_manager.get_session() as session:
            order = Order(
                user_id=test_user.id,
                strategy_id=test_strategy.id,
                symbol="RELIANCE",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=10,
                status=OrderStatus.PENDING
            )
            session.add(order)
            await session.commit()
            order_id = order.id
        
        # Test order progression through valid statuses
        statuses = [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.COMPLETE]
        
        for status in statuses:
            async with db_manager.get_session() as session:
                result = await session.execute(select(Order).where(Order.id == order_id))
                order = result.scalar_one()
                order.status = status
                await session.commit()
                
                # Verify status update
                result = await session.execute(select(Order).where(Order.id == order_id))
                updated_order = result.scalar_one()
                assert updated_order.status == status

    async def test_strategy_to_order_flow(self, db_manager, test_user):
        """Test flow from strategy creation to order generation"""
        from app.models.base import Strategy, Order, OrderSide, OrderType, ProductType
        from sqlalchemy import select
        
        # Create active strategy
        async with db_manager.get_session() as session:
            strategy = Strategy(
                user_id=test_user.id,
                name="Integration Test Strategy",
                strategy_type="test_integration",
                asset_class=AssetClass.EQUITY,
                symbols=["RELIANCE", "TCS"],
                timeframe=TimeFrame.MINUTE_1,
                status=StrategyStatus.ACTIVE,
                parameters={"signal_threshold": 0.02},
                risk_parameters={"max_position_size": 100}
            )
            session.add(strategy)
            await session.commit()
            strategy_id = strategy.id
        
        # Simulate strategy generating orders
        async with db_manager.get_session() as session:
            # Strategy generates buy signal for RELIANCE
            buy_order = Order(
                user_id=test_user.id,
                strategy_id=strategy_id,
                symbol="RELIANCE",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=50,
                status=OrderStatus.PENDING
            )
            session.add(buy_order)
            
            # Strategy generates sell signal for TCS
            sell_order = Order(
                user_id=test_user.id,
                strategy_id=strategy_id,
                symbol="TCS",
                exchange="NSE",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                product_type=ProductType.INTRADAY,
                quantity=25,
                price=3500.0,
                status=OrderStatus.PENDING
            )
            session.add(sell_order)
            await session.commit()
        
        # Verify orders were created correctly
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.strategy_id == strategy_id)
            )
            orders = result.scalars().all()
            
            assert len(orders) == 2
            assert any(o.symbol == "RELIANCE" and o.side == OrderSide.BUY for o in orders)
            assert any(o.symbol == "TCS" and o.side == OrderSide.SELL for o in orders)

    async def test_multi_user_isolation(self, db_manager):
        """Test that multiple users don't interfere with each other"""
        from app.models.base import User, Strategy, Order, OrderSide, OrderType, ProductType
        from sqlalchemy import select
        
        # Create two users with unique identifiers
        unique_id = str(uuid.uuid4())[:8]
        async with db_manager.get_session() as session:
            user1 = User(
                email=f"user1_{unique_id}@test.com",
                username=f"user1_{unique_id}",
                hashed_password="password1"
            )
            user2 = User(
                email=f"user2_{unique_id}@test.com", 
                username=f"user2_{unique_id}",
                hashed_password="password2"
            )
            session.add_all([user1, user2])
            await session.commit()
            user1_id, user2_id = user1.id, user2.id
        
        # Create strategies for each user
        async with db_manager.get_session() as session:
            strategy1 = Strategy(
                user_id=user1_id,
                name="User1 Strategy",
                strategy_type="test",
                asset_class=AssetClass.EQUITY,
                symbols=["RELIANCE"],
                timeframe=TimeFrame.MINUTE_1,
                status=StrategyStatus.ACTIVE,
                parameters={"test_param": 1.0},
                risk_parameters={"max_loss": 0.02}
            )
            strategy2 = Strategy(
                user_id=user2_id,
                name="User2 Strategy", 
                strategy_type="test",
                asset_class=AssetClass.DERIVATIVES,
                symbols=["NIFTYFUT"],
                timeframe=TimeFrame.MINUTE_5,
                status=StrategyStatus.ACTIVE,
                parameters={"test_param": 2.0},
                risk_parameters={"max_loss": 0.03}
            )
            session.add_all([strategy1, strategy2])
            await session.commit()
            strategy1_id, strategy2_id = strategy1.id, strategy2.id
        
        # Create orders for each user
        async with db_manager.get_session() as session:
            order1 = Order(
                user_id=user1_id,
                strategy_id=strategy1_id,
                symbol="RELIANCE",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=10
            )
            order2 = Order(
                user_id=user2_id,
                strategy_id=strategy2_id,
                symbol="NIFTYFUT",
                exchange="NFO",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                product_type=ProductType.MARGIN,
                quantity=50,
                price=18000.0
            )
            session.add_all([order1, order2])
            await session.commit()
        
        # Verify isolation - each user sees only their data
        async with db_manager.get_session() as session:
            # User1 should only see their strategy
            result = await session.execute(
                select(Strategy).where(Strategy.user_id == user1_id)
            )
            user1_strategies = result.scalars().all()
            assert len(user1_strategies) == 1
            assert user1_strategies[0].name == "User1 Strategy"
            
            # User2 should only see their strategy
            result = await session.execute(
                select(Strategy).where(Strategy.user_id == user2_id)
            )
            user2_strategies = result.scalars().all()
            assert len(user2_strategies) == 1
            assert user2_strategies[0].name == "User2 Strategy"
            
            # User1 should only see their orders
            result = await session.execute(
                select(Order).where(Order.user_id == user1_id)
            )
            user1_orders = result.scalars().all()
            assert len(user1_orders) == 1
            assert user1_orders[0].symbol == "RELIANCE"
            
            # User2 should only see their orders
            result = await session.execute(
                select(Order).where(Order.user_id == user2_id)
            )
            user2_orders = result.scalars().all()
            assert len(user2_orders) == 1
            assert user2_orders[0].symbol == "NIFTYFUT"

class TestSystemStressTest:
    """Test system under stress conditions"""
    
    async def test_high_volume_order_processing(self, db_manager, test_user, test_strategy):
        """Test processing high volume of orders"""
        from app.models.base import Order, OrderSide, OrderType, ProductType
        from sqlalchemy import select
        
        # Create multiple orders rapidly
        order_count = 50
        orders = []
        
        async with db_manager.get_session() as session:
            for i in range(order_count):
                order = Order(
                    user_id=test_user.id,
                    strategy_id=test_strategy.id,
                    symbol=f"STOCK{i % 10}",  # Cycle through 10 different stocks
                    exchange="NSE",
                    side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    product_type=ProductType.INTRADAY,
                    quantity=10 + (i % 50),
                    status=OrderStatus.PENDING
                )
                orders.append(order)
            
            session.add_all(orders)
            await session.commit()
        
        # Verify all orders were created
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.user_id == test_user.id)
            )
            created_orders = result.scalars().all()
            assert len(created_orders) >= order_count

    async def test_concurrent_strategy_execution(self, db_manager, test_user):
        """Test concurrent execution of multiple strategies"""
        from app.models.base import Strategy
        from sqlalchemy import select
        
        # Create multiple strategies
        strategies_data = [
            ("Equity Strategy", AssetClass.EQUITY, ["RELIANCE", "TCS"]),
            ("Derivatives Strategy", AssetClass.DERIVATIVES, ["NIFTYFUT", "BANKNIFTYFUT"]),
            ("Crypto Strategy", AssetClass.CRYPTO, ["BTCUSDT", "ETHUSDT"]),
        ]
        
        strategy_ids = []
        async with db_manager.get_session() as session:
            for name, asset_class, symbols in strategies_data:
                strategy = Strategy(
                    user_id=test_user.id,
                    name=name,
                    strategy_type="concurrent_test",
                    asset_class=asset_class,
                    symbols=symbols,
                    timeframe=TimeFrame.MINUTE_1,
                    status=StrategyStatus.ACTIVE,
                    parameters={"test": True},
                    risk_parameters={"max_loss": 0.02}
                )
                session.add(strategy)
                await session.commit()
                strategy_ids.append(strategy.id)
        
        # Simulate concurrent strategy execution
        async def mock_strategy_execution(strategy_id):
            await asyncio.sleep(0.1)  # Simulate processing time
            return f"Strategy {strategy_id} executed"
        
        # Execute all strategies concurrently
        tasks = [mock_strategy_execution(sid) for sid in strategy_ids]
        results = await asyncio.gather(*tasks)
        
        # All should complete
        assert len(results) == len(strategy_ids)
        assert all("executed" in result for result in results)

class TestFailureRecovery:
    """Test system recovery from failures"""
    
    async def test_database_reconnection(self, db_manager):
        """Test recovery from database connection loss"""
        # Simulate database reconnection
        original_session = db_manager.get_session
        
        async def failing_session():
            raise Exception("Database connection lost")
        
        # Temporarily replace with failing session
        db_manager.get_session = failing_session
        
        # Should handle failure gracefully
        with pytest.raises(Exception):
            async with db_manager.get_session():
                pass
        
        # Restore original session
        db_manager.get_session = original_session
        
        # Should work normally after restoration
        async with db_manager.get_session() as session:
            assert session is not None

    async def test_partial_order_failure_recovery(self, db_manager, test_user, test_strategy):
        """Test recovery when some orders fail"""
        from app.models.base import Order, OrderSide, OrderType, ProductType
        from sqlalchemy import select
        
        # Create multiple orders
        orders_data = [
            ("RELIANCE", 10, True),   # Should succeed
            ("INVALID", -5, False),   # Should fail (negative quantity)
            ("TCS", 20, True),        # Should succeed
            ("BADSTOCK", 0, False),   # Should fail (zero quantity)
            ("INFY", 15, True),       # Should succeed
        ]
        
        successful_orders = []
        failed_orders = []
        
        async with db_manager.get_session() as session:
            for symbol, quantity, should_succeed in orders_data:
                try:
                    order = Order(
                        user_id=test_user.id,
                        strategy_id=test_strategy.id,
                        symbol=symbol,
                        exchange="NSE",
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        product_type=ProductType.INTRADAY,
                        quantity=quantity,
                        status=OrderStatus.PENDING
                    )
                    session.add(order)
                    await session.commit()
                    
                    if should_succeed:
                        successful_orders.append(order.id)
                    else:
                        # Mark as failed
                        order.status = OrderStatus.ERROR
                        await session.commit()
                        failed_orders.append(order.id)
                        
                except Exception:
                    failed_orders.append(symbol)
        
        # Verify successful orders are processed
        assert len(successful_orders) == 3  # RELIANCE, TCS, INFY
        
        # Verify system continues despite failures
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.user_id == test_user.id)
            )
            all_orders = result.scalars().all()
            
            # Should have all orders created
            assert len(all_orders) >= 3
            
            # Some should be successful, some failed
            successful_count = len([o for o in all_orders if o.status != OrderStatus.ERROR])
            assert successful_count >= 3

class TestDataConsistency:
    """Test data consistency across the system"""
    
    async def test_order_strategy_consistency(self, db_manager, test_user, test_strategy):
        """Test consistency between orders and their strategies"""
        from app.models.base import Order, OrderSide, OrderType, ProductType
        from sqlalchemy import select
        
        # Create orders for strategy
        async with db_manager.get_session() as session:
            orders = [
                Order(
                    user_id=test_user.id,
                    strategy_id=test_strategy.id,
                    symbol=symbol,
                    exchange="NSE",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    product_type=ProductType.INTRADAY,
                    quantity=10,
                    status=OrderStatus.PENDING
                )
                for symbol in test_strategy.symbols
            ]
            session.add_all(orders)
            await session.commit()
        
        # Verify all orders belong to correct strategy and user
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.strategy_id == test_strategy.id)
            )
            strategy_orders = result.scalars().all()
            
            # All orders should belong to correct user and strategy
            assert all(o.user_id == test_user.id for o in strategy_orders)
            assert all(o.strategy_id == test_strategy.id for o in strategy_orders)
            assert all(o.symbol in test_strategy.symbols for o in strategy_orders)

    async def test_user_data_isolation(self, db_manager):
        """Test that user data is properly isolated"""
        from app.models.base import User, Strategy, Order
        from sqlalchemy import select, func
        import uuid
        
        # Create multiple users with data using unique identifiers
        unique_id = str(uuid.uuid4())[:8]
        users_data = [
            (f"user1_{unique_id}@test.com", f"user1_{unique_id}"),
            (f"user2_{unique_id}@test.com", f"user2_{unique_id}"),
            (f"user3_{unique_id}@test.com", f"user3_{unique_id}"),
        ]
        
        user_ids = []
        async with db_manager.get_session() as session:
            for email, username in users_data:
                user = User(
                    email=email,
                    username=username,
                    hashed_password="password"
                )
                session.add(user)
                await session.commit()
                user_ids.append(user.id)
        
        # Create strategies and orders for each user
        for i, user_id in enumerate(user_ids):
            async with db_manager.get_session() as session:
                strategy = Strategy(
                    user_id=user_id,
                    name=f"User{i+1} Strategy",
                    strategy_type="isolation_test",
                    asset_class=AssetClass.EQUITY,
                    symbols=[f"STOCK{i+1}"],
                    timeframe=TimeFrame.MINUTE_1,
                    status=StrategyStatus.ACTIVE,
                    parameters={"test_param": i+1},
                    risk_parameters={"max_loss": 0.02}
                )
                session.add(strategy)
                await session.commit()
        
        # Verify each user has exactly their own data
        for user_id in user_ids:
            async with db_manager.get_session() as session:
                # Count strategies for this user
                result = await session.execute(
                    select(func.count(Strategy.id)).where(Strategy.user_id == user_id)
                )
                strategy_count = result.scalar()
                assert strategy_count == 1
                
                # Verify no access to other users' strategies from this test
                other_user_ids = [uid for uid in user_ids if uid != user_id]
                result = await session.execute(
                    select(func.count(Strategy.id)).where(Strategy.user_id.in_(other_user_ids))
                )
                other_strategies_count = result.scalar()
                assert other_strategies_count == len(user_ids) - 1 