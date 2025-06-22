"""
Resource Management System
Prevents resource leaks and manages system resources efficiently
"""

import asyncio
import logging
import psutil
import gc
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ResourceUsage:
    """Resource usage metrics"""
    timestamp: datetime
    memory_mb: float
    cpu_percent: float
    open_files: int
    threads_count: int

class ResourceTracker:
    """Tracks system resource usage and detects leaks"""
    
    def __init__(self):
        self.usage_history: List[ResourceUsage] = []
        self.max_history_size = 100
        self.baseline_memory = None
        self.baseline_established = False
        
    def record_usage(self) -> ResourceUsage:
        """Record current resource usage"""
        try:
            process = psutil.Process()
            
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            try:
                open_files = len(process.open_files())
            except:
                open_files = 0
            
            threads_count = process.num_threads()
            
            usage = ResourceUsage(
                timestamp=datetime.now(),
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                open_files=open_files,
                threads_count=threads_count
            )
            
            self.usage_history.append(usage)
            
            if len(self.usage_history) > self.max_history_size:
                self.usage_history = self.usage_history[-self.max_history_size:]
            
            if not self.baseline_established and len(self.usage_history) >= 5:
                self.baseline_memory = sum(u.memory_mb for u in self.usage_history[-5:]) / 5
                self.baseline_established = True
                logger.info(f"📊 Resource baseline: {self.baseline_memory:.1f}MB")
            
            return usage
            
        except Exception as e:
            logger.error(f"❌ Error recording resource usage: {e}")
            return None
    
    def detect_memory_leak(self) -> bool:
        """Detect potential memory leak"""
        if len(self.usage_history) < 10 or not self.baseline_established:
            return False
        
        recent_memory = sum(u.memory_mb for u in self.usage_history[-5:]) / 5
        memory_growth = recent_memory - self.baseline_memory
        
        return memory_growth > 100  # 100MB growth indicates potential leak

class ResourceCleaner:
    """Performs resource cleanup operations"""
    
    def __init__(self):
        self.cleanup_operations = 0
        self.memory_freed_mb = 0.0
        
    async def perform_memory_cleanup(self) -> Dict[str, Any]:
        """Perform memory cleanup"""
        try:
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Force garbage collection
            collected_objects = gc.collect()
            gc.collect()  # Second pass
            
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_freed = max(0, memory_before - memory_after)
            
            self.cleanup_operations += 1
            self.memory_freed_mb += memory_freed
            
            result = {
                'success': True,
                'memory_freed_mb': memory_freed,
                'objects_collected': collected_objects,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"🧹 Memory cleanup: {memory_freed:.1f}MB freed, {collected_objects} objects")
            return result
            
        except Exception as e:
            logger.error(f"❌ Memory cleanup error: {e}")
            return {'success': False, 'error': str(e)}

class ResourceManager:
    """Main resource management system"""
    
    def __init__(self):
        self.tracker = ResourceTracker()
        self.cleaner = ResourceCleaner()
        self.monitoring_active = False
        self.monitoring_interval = 60  # seconds
        
    async def start_monitoring(self):
        """Start resource monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        logger.info("📊 Resource monitoring started")
        asyncio.create_task(self._monitoring_loop())
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring_active = False
        logger.info("📊 Resource monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                usage = self.tracker.record_usage()
                
                if usage and self.tracker.detect_memory_leak():
                    logger.warning("🚨 Memory leak detected - triggering cleanup")
                    await self.cleaner.perform_memory_cleanup()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"❌ Resource monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def force_cleanup(self) -> Dict[str, Any]:
        """Force immediate resource cleanup"""
        logger.info("🧹 Forced resource cleanup")
        return await self.cleaner.perform_memory_cleanup()
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get resource status"""
        current_usage = self.tracker.usage_history[-1] if self.tracker.usage_history else None
        
        return {
            'monitoring_active': self.monitoring_active,
            'current_memory_mb': current_usage.memory_mb if current_usage else 0,
            'current_cpu_percent': current_usage.cpu_percent if current_usage else 0,
            'baseline_memory_mb': self.tracker.baseline_memory,
            'cleanup_operations': self.cleaner.cleanup_operations,
            'total_memory_freed_mb': self.cleaner.memory_freed_mb
        }

# Global instance
_resource_manager = None

def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager
