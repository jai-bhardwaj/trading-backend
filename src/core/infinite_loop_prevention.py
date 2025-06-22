"""
Infinite Loop Prevention System
Prevents infinite loops in trading strategies and system components
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import signal
import sys

logger = logging.getLogger(__name__)

class LoopMonitor:
    """Monitor and prevent infinite loops"""
    
    def __init__(self):
        self.active_loops: Dict[str, Dict[str, Any]] = {}
        self.loop_timeouts: Dict[str, float] = {}
        self.max_loop_duration = 300  # 5 minutes default
        self.check_interval = 5  # Check every 5 seconds
        self.monitoring_active = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start loop monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loops, daemon=True)
            self.monitor_thread.start()
            logger.info("🔄 Loop monitoring started")
    
    def stop_monitoring(self):
        """Stop loop monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.info("🔄 Loop monitoring stopped")
    
    def register_loop(self, loop_id: str, max_duration: float = None):
        """Register a loop for monitoring"""
        if max_duration is None:
            max_duration = self.max_loop_duration
        
        self.active_loops[loop_id] = {
            'start_time': time.time(),
            'last_heartbeat': time.time(),
            'max_duration': max_duration,
            'iterations': 0
        }
        
    def heartbeat(self, loop_id: str):
        """Send heartbeat from loop"""
        if loop_id in self.active_loops:
            self.active_loops[loop_id]['last_heartbeat'] = time.time()
            self.active_loops[loop_id]['iterations'] += 1
    
    def unregister_loop(self, loop_id: str):
        """Unregister loop when completed"""
        if loop_id in self.active_loops:
            duration = time.time() - self.active_loops[loop_id]['start_time']
            iterations = self.active_loops[loop_id]['iterations']
            logger.debug(f"🔄 Loop {loop_id} completed: {duration:.1f}s, {iterations} iterations")
            del self.active_loops[loop_id]
    
    def _monitor_loops(self):
        """Monitor active loops for infinite loops"""
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                for loop_id, loop_info in list(self.active_loops.items()):
                    duration = current_time - loop_info['start_time']
                    
                    # Check for timeout
                    if duration > loop_info['max_duration']:
                        logger.error(f"🚨 Infinite loop detected: {loop_id}")
                        logger.error(f"   Duration: {duration:.1f}s (limit: {loop_info['max_duration']}s)")
                        logger.error(f"   Iterations: {loop_info['iterations']}")
                        
                        # Take action to prevent infinite loop
                        self._handle_infinite_loop(loop_id, loop_info)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Loop monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def _handle_infinite_loop(self, loop_id: str, loop_info: Dict[str, Any]):
        """Handle detected infinite loop"""
        # Log critical information
        logger.critical(f"🚨 INFINITE LOOP EMERGENCY: {loop_id}")
        
        # Remove from monitoring to prevent repeated alerts
        if loop_id in self.active_loops:
            del self.active_loops[loop_id]
        
        # Could implement more aggressive measures here if needed
        # For now, just log and alert

def loop_timeout(max_duration: float = 300, loop_id: str = None):
    """Decorator to prevent infinite loops"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal loop_id
            if loop_id is None:
                loop_id = f"{func.__name__}_{int(time.time())}"
            
            monitor = get_loop_monitor()
            monitor.register_loop(loop_id, max_duration)
            
            try:
                # Execute function with timeout protection
                start_time = time.time()
                result = func(*args, **kwargs)
                
                # Check if function took too long
                duration = time.time() - start_time
                if duration > max_duration:
                    logger.warning(f"⚠️ Function {func.__name__} took {duration:.1f}s (limit: {max_duration}s)")
                
                return result
                
            finally:
                monitor.unregister_loop(loop_id)
        
        return wrapper
    return decorator

def safe_while_loop(condition: Callable, max_iterations: int = 10000, max_duration: float = 60):
    """Safe while loop with automatic break conditions"""
    def loop_wrapper():
        iterations = 0
        start_time = time.time()
        loop_id = f"safe_while_{int(start_time)}"
        
        monitor = get_loop_monitor()
        monitor.register_loop(loop_id, max_duration)
        
        try:
            while condition() and iterations < max_iterations:
                # Check time limit
                if time.time() - start_time > max_duration:
                    logger.warning(f"⚠️ While loop timeout after {max_duration}s")
                    break
                
                # Send heartbeat
                monitor.heartbeat(loop_id)
                
                # Yield control
                yield iterations
                iterations += 1
            
            if iterations >= max_iterations:
                logger.warning(f"⚠️ While loop iteration limit reached: {max_iterations}")
                
        finally:
            monitor.unregister_loop(loop_id)
    
    return loop_wrapper()

def safe_for_loop(iterable, max_duration: float = 60):
    """Safe for loop with timeout protection"""
    start_time = time.time()
    loop_id = f"safe_for_{int(start_time)}"
    
    monitor = get_loop_monitor()
    monitor.register_loop(loop_id, max_duration)
    
    try:
        for i, item in enumerate(iterable):
            # Check time limit
            if time.time() - start_time > max_duration:
                logger.warning(f"⚠️ For loop timeout after {max_duration}s at iteration {i}")
                break
            
            # Send heartbeat every 100 iterations
            if i % 100 == 0:
                monitor.heartbeat(loop_id)
            
            yield item
            
    finally:
        monitor.unregister_loop(loop_id)

# Global instance
_loop_monitor = None

def get_loop_monitor() -> LoopMonitor:
    """Get global loop monitor instance"""
    global _loop_monitor
    if _loop_monitor is None:
        _loop_monitor = LoopMonitor()
        _loop_monitor.start_monitoring()
    return _loop_monitor
