"""
Priority Order Queue System

Provides advanced priority-based order queuing with smart routing and load balancing.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .redis_client import get_redis_connection
from .order_queue import QueuedOrder, QueuePriority

logger = logging.getLogger(__name__)

class OrderUrgency(Enum):
    """Order urgency levels for smart routing"""
    MARKET_CLOSE = "MARKET_CLOSE"      # Orders before market close
    STOP_LOSS = "STOP_LOSS"            # Stop loss orders
    ARBITRAGE = "ARBITRAGE"            # Arbitrage opportunities
    LIQUIDATION = "LIQUIDATION"        # Position liquidation
    NORMAL = "NORMAL"                  # Regular orders

@dataclass
class PriorityOrderMetadata:
    """Extended metadata for priority orders"""
    urgency: str = OrderUrgency.NORMAL.value
    deadline: Optional[str] = None
    strategy_id: Optional[str] = None
    risk_level: str = "LOW"
    estimated_profit: Optional[float] = None
    market_impact: str = "LOW"

class PriorityOrderQueue:
    """Advanced priority queue with smart routing and load balancing"""
    
    def __init__(self, queue_name: str = "priority_orders"):
        self.queue_name = queue_name
        
        # Priority-based queues
        self.critical_queue = f"{queue_name}:critical"
        self.urgent_queue = f"{queue_name}:urgent"
        self.high_queue = f"{queue_name}:high"
        self.normal_queue = f"{queue_name}:normal"
        self.low_queue = f"{queue_name}:low"
        
        # Specialized queues
        self.market_close_queue = f"{queue_name}:market_close"
        self.stop_loss_queue = f"{queue_name}:stop_loss"
        self.arbitrage_queue = f"{queue_name}:arbitrage"
        self.liquidation_queue = f"{queue_name}:liquidation"
        
        # Processing tracking
        self.processing_queue = f"{queue_name}:processing"
        self.worker_assignment = f"{queue_name}:workers"
        
        # Statistics
        self.stats_key = f"{queue_name}:priority_stats"
        
    def enqueue_priority_order(self, order: QueuedOrder, metadata: PriorityOrderMetadata) -> bool:
        """Add order to appropriate priority queue"""
        try:
            redis_client = get_redis_connection()
            
            # Enhance order with priority metadata
            order.metadata.update({
                'urgency': metadata.urgency,
                'deadline': metadata.deadline,
                'strategy_id': metadata.strategy_id,
                'risk_level': metadata.risk_level,
                'estimated_profit': metadata.estimated_profit,
                'market_impact': metadata.market_impact,
                'priority_score': self._calculate_priority_score(order, metadata)
            })
            
            # Determine target queue
            target_queue = self._select_target_queue(order, metadata)
            
            # Serialize order data
            order_data = json.dumps({
                'order': order.__dict__,
                'metadata': metadata.__dict__,
                'enqueued_at': datetime.utcnow().isoformat(),
                'priority_score': order.metadata['priority_score']
            })
            
            # Add to queue with score for sorting
            if target_queue in [self.arbitrage_queue, self.liquidation_queue]:
                # Use sorted sets for time-sensitive orders
                redis_client.zadd(target_queue, {order_data: order.metadata['priority_score']})
            else:
                # Use lists for regular priority orders
                redis_client.lpush(target_queue, order_data)
            
            # Update statistics
            self._update_priority_stats(target_queue, "enqueued")
            
            logger.info(f"📈 Priority order {order.order_id} added to {target_queue} (score: {order.metadata['priority_score']})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue priority order {order.order_id}: {e}")
            return False
    
    def dequeue_priority_order(self, worker_id: str, timeout: int = 5) -> Optional[QueuedOrder]:
        """Get next highest priority order"""
        try:
            redis_client = get_redis_connection()
            
            # Define queue priority order (highest to lowest)
            queue_priority = [
                self.liquidation_queue,     # Immediate liquidation
                self.market_close_queue,    # Market close urgency
                self.arbitrage_queue,       # Time-sensitive arbitrage
                self.stop_loss_queue,       # Risk management
                self.critical_queue,        # Critical priority
                self.urgent_queue,          # Urgent priority
                self.high_queue,            # High priority
                self.normal_queue,          # Normal priority
                self.low_queue              # Low priority
            ]
            
            # Try each queue in priority order
            for queue in queue_priority:
                order_data = None
                
                if queue in [self.arbitrage_queue, self.liquidation_queue]:
                    # Get highest score from sorted set
                    items = redis_client.zrevrange(queue, 0, 0, withscores=True)
                    if items:
                        order_data, score = items[0]
                        redis_client.zrem(queue, order_data)
                else:
                    # Get from list
                    order_data = redis_client.rpop(queue)
                
                if order_data:
                    # Parse order data
                    if isinstance(order_data, bytes):
                        order_data = order_data.decode('utf-8')
                    
                    data = json.loads(order_data)
                    order = QueuedOrder(**data['order'])
                    
                    # Assign to worker
                    self._assign_to_worker(order.order_id, worker_id)
                    
                    # Update statistics
                    self._update_priority_stats(queue, "dequeued")
                    
                    logger.info(f"🔄 Worker {worker_id} dequeued priority order {order.order_id} from {queue}")
                    return order
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue priority order: {e}")
            return None
    
    def _calculate_priority_score(self, order: QueuedOrder, metadata: PriorityOrderMetadata) -> float:
        """Calculate dynamic priority score for order"""
        base_score = order.priority * 100
        
        # Urgency multiplier
        urgency_multipliers = {
            OrderUrgency.LIQUIDATION.value: 5.0,
            OrderUrgency.MARKET_CLOSE.value: 4.0,
            OrderUrgency.ARBITRAGE.value: 3.5,
            OrderUrgency.STOP_LOSS.value: 3.0,
            OrderUrgency.NORMAL.value: 1.0
        }
        
        urgency_score = urgency_multipliers.get(metadata.urgency, 1.0)
        
        # Time-based urgency
        time_score = 1.0
        if metadata.deadline:
            try:
                deadline = datetime.fromisoformat(metadata.deadline)
                time_to_deadline = (deadline - datetime.utcnow()).total_seconds()
                if time_to_deadline > 0:
                    # Higher score for closer deadlines
                    time_score = max(1.0, 3600 / max(60, time_to_deadline))
            except:
                pass
        
        # Profit potential
        profit_score = 1.0
        if metadata.estimated_profit:
            profit_score = min(2.0, 1.0 + (metadata.estimated_profit / 10000))  # Cap at 2x
        
        # Risk adjustment
        risk_multipliers = {
            "LOW": 1.0,
            "MEDIUM": 1.2,
            "HIGH": 1.5
        }
        risk_score = risk_multipliers.get(metadata.risk_level, 1.0)
        
        # Market impact penalty
        impact_penalties = {
            "LOW": 1.0,
            "MEDIUM": 0.9,
            "HIGH": 0.8
        }
        impact_score = impact_penalties.get(metadata.market_impact, 1.0)
        
        # Calculate final score
        final_score = (base_score * urgency_score * time_score * profit_score * risk_score * impact_score)
        
        return round(final_score, 2)
    
    def _select_target_queue(self, order: QueuedOrder, metadata: PriorityOrderMetadata) -> str:
        """Select appropriate queue based on order characteristics"""
        
        # Special urgency routing
        if metadata.urgency == OrderUrgency.LIQUIDATION.value:
            return self.liquidation_queue
        elif metadata.urgency == OrderUrgency.MARKET_CLOSE.value:
            return self.market_close_queue
        elif metadata.urgency == OrderUrgency.ARBITRAGE.value:
            return self.arbitrage_queue
        elif metadata.urgency == OrderUrgency.STOP_LOSS.value:
            return self.stop_loss_queue
        
        # Priority-based routing
        if order.priority >= QueuePriority.CRITICAL.value:
            return self.critical_queue
        elif order.priority >= QueuePriority.URGENT.value:
            return self.urgent_queue
        elif order.priority >= QueuePriority.HIGH.value:
            return self.high_queue
        elif order.priority >= QueuePriority.NORMAL.value:
            return self.normal_queue
        else:
            return self.low_queue
    
    def _assign_to_worker(self, order_id: str, worker_id: str):
        """Assign order to specific worker"""
        try:
            redis_client = get_redis_connection()
            
            assignment_data = {
                'worker_id': worker_id,
                'assigned_at': datetime.utcnow().isoformat(),
                'status': 'processing'
            }
            
            redis_client.hset(
                self.worker_assignment,
                order_id,
                json.dumps(assignment_data)
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to assign order {order_id} to worker {worker_id}: {e}")
    
    def _update_priority_stats(self, queue_name: str, action: str):
        """Update priority queue statistics"""
        try:
            redis_client = get_redis_connection()
            
            # Extract queue type from name
            queue_type = queue_name.split(':')[-1]
            
            # Update counters
            redis_client.hincrby(self.stats_key, f"{queue_type}_{action}", 1)
            redis_client.hincrby(self.stats_key, f"total_{action}", 1)
            redis_client.hset(self.stats_key, "last_updated", datetime.utcnow().isoformat())
            
        except Exception as e:
            logger.error(f"❌ Failed to update priority stats: {e}")
    
    def get_priority_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive priority queue statistics"""
        try:
            redis_client = get_redis_connection()
            
            # Get queue lengths
            queue_lengths = {}
            for queue_name, queue_key in [
                ("critical", self.critical_queue),
                ("urgent", self.urgent_queue),
                ("high", self.high_queue),
                ("normal", self.normal_queue),
                ("low", self.low_queue),
                ("market_close", self.market_close_queue),
                ("stop_loss", self.stop_loss_queue),
                ("arbitrage", self.arbitrage_queue),
                ("liquidation", self.liquidation_queue)
            ]:
                if queue_key in [self.arbitrage_queue, self.liquidation_queue]:
                    queue_lengths[queue_name] = redis_client.zcard(queue_key)
                else:
                    queue_lengths[queue_name] = redis_client.llen(queue_key)
            
            # Get processing count
            processing_count = redis_client.hlen(self.worker_assignment)
            
            # Get statistics
            stats = redis_client.hgetall(self.stats_key)
            stats = {k.decode('utf-8'): v.decode('utf-8') for k, v in stats.items()}
            
            # Calculate totals
            total_pending = sum(queue_lengths.values())
            total_urgent = (queue_lengths.get('critical', 0) + 
                          queue_lengths.get('urgent', 0) + 
                          queue_lengths.get('liquidation', 0) + 
                          queue_lengths.get('market_close', 0))
            
            return {
                'queue_lengths': queue_lengths,
                'processing_count': processing_count,
                'statistics': stats,
                'summary': {
                    'total_pending': total_pending,
                    'total_urgent': total_urgent,
                    'total_processing': processing_count,
                    'urgency_ratio': total_urgent / max(1, total_pending)
                },
                'health': {
                    'status': 'critical' if total_urgent > 100 else 'healthy',
                    'urgent_backlog': total_urgent > 50,
                    'processing_capacity': processing_count < 1000
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get priority queue stats: {e}")
            return {'error': str(e)}
    
    def rebalance_queues(self) -> Dict[str, int]:
        """Rebalance queues based on current load and priorities"""
        try:
            redis_client = get_redis_connection()
            rebalanced = {}
            
            # Get current queue states
            stats = self.get_priority_queue_stats()
            queue_lengths = stats.get('queue_lengths', {})
            
            # Check for overloaded normal/low priority queues
            normal_count = queue_lengths.get('normal', 0)
            low_count = queue_lengths.get('low', 0)
            
            # Promote some normal orders to high if normal queue is overloaded
            if normal_count > 1000:
                promoted = min(100, normal_count // 10)  # Promote 10%
                
                for _ in range(promoted):
                    order_data = redis_client.rpop(self.normal_queue)
                    if order_data:
                        redis_client.lpush(self.high_queue, order_data)
                        rebalanced['normal_to_high'] = rebalanced.get('normal_to_high', 0) + 1
            
            # Promote some low orders to normal if low queue is overloaded
            if low_count > 2000:
                promoted = min(200, low_count // 10)  # Promote 10%
                
                for _ in range(promoted):
                    order_data = redis_client.rpop(self.low_queue)
                    if order_data:
                        redis_client.lpush(self.normal_queue, order_data)
                        rebalanced['low_to_normal'] = rebalanced.get('low_to_normal', 0) + 1
            
            if rebalanced:
                logger.info(f"🔄 Queue rebalancing completed: {rebalanced}")
            
            return rebalanced
            
        except Exception as e:
            logger.error(f"❌ Failed to rebalance queues: {e}")
            return {}
    
    def cleanup_expired_assignments(self, max_age_minutes: int = 30) -> int:
        """Clean up expired worker assignments"""
        try:
            redis_client = get_redis_connection()
            cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
            
            # Get all assignments
            assignments = redis_client.hgetall(self.worker_assignment)
            cleaned_count = 0
            
            for order_id, assignment_data in assignments.items():
                try:
                    assignment = json.loads(assignment_data.decode('utf-8'))
                    assigned_at = datetime.fromisoformat(assignment['assigned_at'])
                    
                    if assigned_at < cutoff_time:
                        redis_client.hdel(self.worker_assignment, order_id)
                        cleaned_count += 1
                        logger.warning(f"🧹 Cleaned expired assignment for order {order_id.decode('utf-8')}")
                
                except Exception as e:
                    # Remove corrupted assignment
                    redis_client.hdel(self.worker_assignment, order_id)
                    cleaned_count += 1
                    logger.error(f"🧹 Removed corrupted assignment: {e}")
            
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned {cleaned_count} expired worker assignments")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired assignments: {e}")
            return 0 