"""
Intelligent Memory Management for Trading Strategies
Prevents memory leaks and optimizes memory usage for price history
"""

import time
import psutil
import os
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_symbols: int
    active_symbols: int
    inactive_symbols: int
    memory_usage_mb: float
    price_points_stored: int
    last_cleanup: datetime
    cleanup_count: int

class SymbolMemoryTracker:
    """Track memory usage per symbol"""
    
    def __init__(self):
        self.symbol_access_times: Dict[str, float] = {}
        self.symbol_sizes: Dict[str, int] = {}
        self.total_memory_points = 0
        
    def record_access(self, symbol: str, data_points: int = 1):
        """Record that a symbol was accessed"""
        current_time = time.time()
        self.symbol_access_times[symbol] = current_time
        self.symbol_sizes[symbol] = self.symbol_sizes.get(symbol, 0) + data_points
        self.total_memory_points += data_points
    
    def get_inactive_symbols(self, inactive_threshold_minutes: int = 30) -> Set[str]:
        """Get symbols that haven't been accessed recently"""
        current_time = time.time()
        threshold = inactive_threshold_minutes * 60
        
        inactive = set()
        for symbol, last_access in self.symbol_access_times.items():
            if current_time - last_access > threshold:
                inactive.add(symbol)
        
        return inactive
    
    def remove_symbol(self, symbol: str) -> int:
        """Remove symbol from tracking and return freed points"""
        freed_points = self.symbol_sizes.pop(symbol, 0)
        self.symbol_access_times.pop(symbol, None)
        self.total_memory_points -= freed_points
        return freed_points

class SmartPriceHistory:
    """
    Smart price history with automatic memory management
    Features:
    - Automatic cleanup of unused symbols
    - Memory usage monitoring
    - Efficient data storage
    - Age-based cleanup
    """
    
    def __init__(self, 
                 max_history_per_symbol: int = 200,
                 max_total_symbols: int = 1000,
                 cleanup_interval_minutes: int = 15,
                 inactive_threshold_minutes: int = 30,
                 memory_limit_mb: int = 100):
        
        # Configuration
        self.max_history_per_symbol = max_history_per_symbol
        self.max_total_symbols = max_total_symbols
        self.cleanup_interval = cleanup_interval_minutes * 60
        self.inactive_threshold = inactive_threshold_minutes * 60
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # Storage - using deque for efficient operations
        self.price_data: Dict[str, deque] = {}
        self.strategy_symbols: Set[str] = set()  # Symbols actively used by strategies
        
        # Memory tracking
        self.memory_tracker = SymbolMemoryTracker()
        self.last_cleanup = time.time()
        self.cleanup_count = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        logger.info(f"🧠 Smart Price History initialized: "
                   f"max {max_history_per_symbol} points/symbol, "
                   f"max {max_total_symbols} symbols, "
                   f"cleanup every {cleanup_interval_minutes}min")
    
    def register_strategy_symbols(self, symbols: List[str]):
        """Register symbols that are actively used by strategies"""
        with self.lock:
            self.strategy_symbols.update(symbols)
            logger.debug(f"📋 Registered strategy symbols: {symbols}")
    
    def add_price_point(self, symbol: str, price: float, volume: int = 0, timestamp: datetime = None):
        """Add a price point with intelligent memory management"""
        if timestamp is None:
            timestamp = datetime.now()
        
        with self.lock:
            # Initialize if new symbol
            if symbol not in self.price_data:
                # Check if we're at symbol limit
                if len(self.price_data) >= self.max_total_symbols:
                    self._cleanup_inactive_symbols(force=True)
                
                self.price_data[symbol] = deque(maxlen=self.max_history_per_symbol)
            
            # Add price point (compact storage)
            price_point = {
                'p': float(price),      # price (shortened key)
                'v': int(volume),       # volume
                't': int(timestamp.timestamp())  # timestamp as int
            }
            
            self.price_data[symbol].append(price_point)
            
            # Track memory usage
            self.memory_tracker.record_access(symbol, 1)
            
            # Periodic cleanup check
            current_time = time.time()
            if current_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_inactive_symbols()
    
    def get_price_history(self, symbol: str, count: int = None) -> List[Dict[str, Any]]:
        """Get price history for symbol with access tracking"""
        with self.lock:
            if symbol not in self.price_data:
                return []
            
            # Record access
            self.memory_tracker.record_access(symbol, 0)  # Access but no new data
            
            # Get data
            data = list(self.price_data[symbol])
            if count:
                data = data[-count:]
            
            # Convert back to full format
            return [
                {
                    'price': point['p'],
                    'volume': point['v'],
                    'timestamp': datetime.fromtimestamp(point['t'])
                }
                for point in data
            ]
    
    def get_prices_only(self, symbol: str, count: int = None) -> List[float]:
        """Get only prices (optimized for calculations)"""
        with self.lock:
            if symbol not in self.price_data:
                return []
            
            self.memory_tracker.record_access(symbol, 0)
            
            data = list(self.price_data[symbol])
            if count:
                data = data[-count:]
            
            return [point['p'] for point in data]
    
    def _cleanup_inactive_symbols(self, force: bool = False):
        """Clean up inactive symbols to free memory"""
        try:
            current_time = time.time()
            
            # Get inactive symbols
            inactive_symbols = self.memory_tracker.get_inactive_symbols(
                self.inactive_threshold // 60
            )
            
            # Don't cleanup strategy symbols unless forced and memory critical
            if not force:
                inactive_symbols = inactive_symbols - self.strategy_symbols
            
            # Cleanup symbols
            cleaned_symbols = 0
            freed_points = 0
            
            for symbol in inactive_symbols:
                if symbol in self.price_data:
                    # Free memory
                    freed_points += self.memory_tracker.remove_symbol(symbol)
                    del self.price_data[symbol]
                    cleaned_symbols += 1
                    
                    # Don't cleanup too many at once unless forced
                    if not force and cleaned_symbols >= 10:
                        break
            
            self.last_cleanup = current_time
            self.cleanup_count += 1
            
            if cleaned_symbols > 0:
                logger.info(f"🧹 Memory cleanup: removed {cleaned_symbols} inactive symbols, "
                           f"freed {freed_points} data points")
            
            # Emergency cleanup if memory usage is high
            self._emergency_cleanup_if_needed()
            
        except Exception as e:
            logger.error(f"❌ Error during memory cleanup: {e}")
    
    def _emergency_cleanup_if_needed(self):
        """Emergency cleanup if memory usage is too high"""
        try:
            # Check memory usage
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss
            
            if memory_usage > self.memory_limit_bytes:
                logger.warning(f"⚠️ High memory usage: {memory_usage / 1024 / 1024:.1f}MB")
                
                # Aggressive cleanup - remove oldest non-strategy symbols
                all_symbols = list(self.price_data.keys())
                non_strategy_symbols = [s for s in all_symbols if s not in self.strategy_symbols]
                
                # Sort by last access time and remove oldest
                symbol_ages = [(s, self.memory_tracker.symbol_access_times.get(s, 0)) 
                              for s in non_strategy_symbols]
                symbol_ages.sort(key=lambda x: x[1])  # Oldest first
                
                cleaned = 0
                for symbol, _ in symbol_ages[:50]:  # Remove up to 50 oldest
                    if symbol in self.price_data:
                        self.memory_tracker.remove_symbol(symbol)
                        del self.price_data[symbol]
                        cleaned += 1
                
                if cleaned > 0:
                    logger.warning(f"🚨 Emergency cleanup: removed {cleaned} symbols")
                    
        except Exception as e:
            logger.error(f"❌ Error during emergency cleanup: {e}")
    
    def get_memory_stats(self) -> MemoryStats:
        """Get detailed memory usage statistics"""
        with self.lock:
            active_symbols = len(self.strategy_symbols & set(self.price_data.keys()))
            inactive_symbols = len(self.price_data) - active_symbols
            
            # Calculate memory usage
            try:
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
            except:
                memory_mb = 0
            
            return MemoryStats(
                total_symbols=len(self.price_data),
                active_symbols=active_symbols,
                inactive_symbols=inactive_symbols,
                memory_usage_mb=memory_mb,
                price_points_stored=self.memory_tracker.total_memory_points,
                last_cleanup=datetime.fromtimestamp(self.last_cleanup),
                cleanup_count=self.cleanup_count
            )
    
    def force_cleanup(self):
        """Force immediate cleanup of all inactive symbols"""
        with self.lock:
            logger.info("🧹 Forcing memory cleanup...")
            self._cleanup_inactive_symbols(force=True)
    
    def clear_symbol(self, symbol: str) -> bool:
        """Clear all data for a specific symbol"""
        with self.lock:
            if symbol in self.price_data:
                self.memory_tracker.remove_symbol(symbol)
                del self.price_data[symbol]
                logger.info(f"🗑️ Cleared price history for {symbol}")
                return True
            return False
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get detailed info about a symbol's memory usage"""
        with self.lock:
            if symbol not in self.price_data:
                return {"exists": False}
            
            data_points = len(self.price_data[symbol])
            last_access = self.memory_tracker.symbol_access_times.get(symbol, 0)
            is_strategy_symbol = symbol in self.strategy_symbols
            
            return {
                "exists": True,
                "data_points": data_points,
                "last_access": datetime.fromtimestamp(last_access) if last_access else None,
                "is_strategy_symbol": is_strategy_symbol,
                "memory_estimate_kb": data_points * 0.1  # Rough estimate
            }

# Global smart price history instance
_smart_price_history = None

def get_smart_price_history() -> SmartPriceHistory:
    """Get global smart price history instance"""
    global _smart_price_history
    if _smart_price_history is None:
        _smart_price_history = SmartPriceHistory()
    return _smart_price_history

def get_smart_memory_manager() -> SmartPriceHistory:
    """Get global smart memory manager instance (alias for compatibility)"""
    return get_smart_price_history() 