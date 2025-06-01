"""
Database Tests
Tests for database connectivity, models, and data operations
"""

import pytest
import uuid
from sqlalchemy import select
from app.models.base import User, Strategy, Order, StrategyStatus, OrderStatus, AssetClass, TimeFrame

class TestDatabase:
    """Test database connectivity and basic operations"""
    
    async def test_database_connection(self, db_manager):
        """Test database connectivity"""
        assert db_manager is not None
        
        # Test basic query
        async with db_manager.get_session() as session:
            result = await session.execute(select(1))
            assert result.scalar() == 1

    async def test_user_model_crud(self, db_manager):
        """Test User model CRUD operations"""
        unique_id = str(uuid.uuid4())
        async with db_manager.get_session() as session:
            # Create
            user = User(
                email=f"crud_test_{unique_id}@example.com",
                username=f"crud_test_user_{unique_id[:8]}",
                hashed_password="test_password",
                first_name="CRUD",
                last_name="Test"
            )
            session.add(user)
            await session.commit()
            
            # Read
            result = await session.execute(
                select(User).where(User.email == f"crud_test_{unique_id}@example.com")
            )
            found_user = result.scalar_one()
            assert found_user.username == f"crud_test_user_{unique_id[:8]}"
            assert found_user.first_name == "CRUD"
            
            # Update
            found_user.first_name = "Updated"
            await session.commit()
            
            # Verify update
            result = await session.execute(
                select(User).where(User.id == found_user.id)
            )
            updated_user = result.scalar_one()
            assert updated_user.first_name == "Updated"
            
            # Delete
            await session.delete(updated_user)
            await session.commit()
            
            # Verify deletion
            result = await session.execute(
                select(User).where(User.id == found_user.id)
            )
            assert result.scalar_one_or_none() is None

    async def test_strategy_model_relationships(self, db_manager, test_user):
        """Test Strategy model and relationships"""
        async with db_manager.get_session() as session:
            # Create strategy
            strategy = Strategy(
                user_id=test_user.id,
                name="Relationship Test Strategy",
                strategy_type="test",
                asset_class=AssetClass.EQUITY,
                symbols=["TEST1", "TEST2"],
                timeframe=TimeFrame.MINUTE_5,
                status=StrategyStatus.DRAFT,
                parameters={"test": True},
                risk_parameters={"max_risk": 0.05}
            )
            session.add(strategy)
            await session.commit()
            
            # Test relationship
            result = await session.execute(
                select(Strategy).where(Strategy.user_id == test_user.id)
            )
            strategies = result.scalars().all()
            assert len(strategies) >= 1
            
            found_strategy = next(s for s in strategies if s.name == "Relationship Test Strategy")
            assert found_strategy.asset_class == AssetClass.EQUITY
            assert "TEST1" in found_strategy.symbols
            assert found_strategy.parameters["test"] is True

    async def test_order_model_with_strategy(self, db_manager, test_user, test_strategy):
        """Test Order model with strategy relationship"""
        async with db_manager.get_session() as session:
            from app.models.base import OrderSide, OrderType, ProductType
            
            order = Order(
                user_id=test_user.id,
                strategy_id=test_strategy.id,
                symbol="TESTSTOCK",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=50,
                status=OrderStatus.PENDING
            )
            session.add(order)
            await session.commit()
            
            # Test relationships
            result = await session.execute(
                select(Order).where(Order.strategy_id == test_strategy.id)
            )
            orders = result.scalars().all()
            assert len(orders) >= 1
            
            found_order = next(o for o in orders if o.symbol == "TESTSTOCK")
            assert found_order.user_id == test_user.id
            assert found_order.quantity == 50
            assert found_order.status == OrderStatus.PENDING

class TestDataIntegrity:
    """Test data integrity and constraints"""
    
    async def test_unique_constraints(self, db_manager):
        """Test unique constraints work properly"""
        unique_id = str(uuid.uuid4())
        async with db_manager.get_session() as session:
            # Create first user
            user1 = User(
                email=f"unique_{unique_id}@example.com",
                username=f"unique_user_{unique_id[:8]}",
                hashed_password="password1"
            )
            session.add(user1)
            await session.commit()
            
            # Try to create duplicate email - should raise exception
            user2 = User(
                email=f"unique_{unique_id}@example.com",  # Same email
                username=f"different_user_{unique_id[:8]}",
                hashed_password="password2"
            )
            session.add(user2)
            
            # This should raise an integrity error
            with pytest.raises(Exception):  # Should raise integrity error
                await session.commit()

    async def test_foreign_key_constraints(self, db_manager, test_user):
        """Test foreign key constraints"""
        async with db_manager.get_session() as session:
            from app.models.base import OrderSide, OrderType, ProductType
            
            # Try to create order with non-existent strategy - should raise exception
            order = Order(
                user_id=test_user.id,
                strategy_id="non-existent-strategy-id",
                symbol="TEST",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=10,
                status=OrderStatus.PENDING
            )
            session.add(order)
            
            # This should raise a foreign key constraint error
            with pytest.raises(Exception):  # Should raise foreign key error
                await session.commit()

    async def test_enum_constraints(self, db_manager, test_user):
        """Test enum field constraints"""
        unique_id = str(uuid.uuid4())
        async with db_manager.get_session() as session:
            strategy = Strategy(
                user_id=test_user.id,
                name=f"Enum Test Strategy {unique_id[:8]}",
                strategy_type="test",
                asset_class=AssetClass.DERIVATIVES,  # Test enum value
                symbols=["FUTURE1"],
                timeframe=TimeFrame.HOUR_1,  # Test enum value
                status=StrategyStatus.ACTIVE,  # Test enum value
                parameters={},
                risk_parameters={}
            )
            session.add(strategy)
            await session.commit()
            
            # Verify enum values are stored correctly
            result = await session.execute(
                select(Strategy).where(Strategy.name == f"Enum Test Strategy {unique_id[:8]}")
            )
            found_strategy = result.scalar_one()
            assert found_strategy.asset_class == AssetClass.DERIVATIVES
            assert found_strategy.timeframe == TimeFrame.HOUR_1
            assert found_strategy.status == StrategyStatus.ACTIVE 