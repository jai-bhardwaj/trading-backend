"""
Trading Engine Tests
Tests for core trading engine functionality
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.base import OrderStatus, OrderSide, OrderType, ProductType

class TestTradingEngine:
    """Test core trading engine functionality"""
    
    async def test_engine_initialization(self, trading_engine):
        """Test trading engine initializes correctly"""
        assert trading_engine is not None
        assert trading_engine.worker_config.worker_count == 2
        assert trading_engine.queue_config.max_queue_size == 100
        assert trading_engine.queue_manager is not None

    async def test_engine_start_stop(self, trading_engine):
        """Test engine start and stop functionality"""
        # Test starting
        result = await trading_engine.start()
        assert result is True
        assert trading_engine.is_running is True
        
        # Test stopping
        await trading_engine.stop()
        assert trading_engine.is_running is False

    async def test_order_submission(self, trading_engine, test_order):
        """Test order submission to queue"""
        # Start the engine first
        await trading_engine.start()
        
        # Test submitting an order
        result = await trading_engine.submit_order(test_order.id)
        
        # Should succeed (mocked)
        assert result is not None

class TestOrderProcessing:
    """Test order processing functionality"""
    
    async def test_order_status_progression(self, db_manager, test_order):
        """Test order status progression"""
        async with db_manager.get_session() as session:
            from sqlalchemy import select
            from app.models.base import Order
            
            # Initial status should be PENDING
            result = await session.execute(select(Order).where(Order.id == test_order.id))
            order = result.scalar_one()
            assert order.status == OrderStatus.PENDING
            
            # Update to QUEUED
            order.status = OrderStatus.QUEUED
            await session.commit()
            
            # Verify update
            result = await session.execute(select(Order).where(Order.id == test_order.id))
            updated_order = result.scalar_one()
            assert updated_order.status == OrderStatus.QUEUED

class TestEngineComponents:
    """Test engine component integration"""
    
    async def test_queue_manager_integration(self, trading_engine):
        """Test queue manager integration"""
        assert trading_engine.queue_manager is not None
        assert hasattr(trading_engine.queue_manager, 'start')
        assert hasattr(trading_engine.queue_manager, 'stop')

    async def test_database_integration(self, trading_engine, db_manager):
        """Test database integration"""
        assert trading_engine.db_manager is not None
        # Test database connectivity through engine
        async with trading_engine.db_manager.get_session() as session:
            assert session is not None

class TestErrorHandling:
    """Test error handling scenarios"""
    
    async def test_invalid_order_submission(self, trading_engine):
        """Test handling of invalid order submission"""
        # Start engine
        await trading_engine.start()
        
        # Try to submit non-existent order
        result = await trading_engine.submit_order("non-existent-order-id")
        assert result is False

    async def test_engine_stop_when_not_running(self, trading_engine):
        """Test stopping engine when not running"""
        # Engine should not be running initially
        assert trading_engine.is_running is False
        
        # Should handle stop gracefully
        await trading_engine.stop()
        assert trading_engine.is_running is False

class TestPerformanceMetrics:
    """Test performance tracking"""
    
    async def test_engine_stats(self, trading_engine):
        """Test engine statistics tracking"""
        stats = trading_engine.get_engine_stats()
        
        assert isinstance(stats, dict)
        assert "orders_processed" in stats
        assert "orders_failed" in stats
        assert "strategies_executed" in stats
        assert "is_running" in stats

    async def test_metrics_initialization(self, trading_engine):
        """Test metrics are properly initialized"""
        assert trading_engine.orders_processed == 0
        assert trading_engine.orders_failed == 0
        assert trading_engine.strategies_executed == 0 