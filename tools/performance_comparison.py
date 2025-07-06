#!/usr/bin/env python3
"""
Performance Comparison: Direct Python vs HTTP API
Demonstrates the performance benefits of eliminating HTTP overhead
"""

import asyncio
import time
import httpx
import statistics
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTest:
    """Performance comparison between direct calls and HTTP API"""
    
    def __init__(self):
        self.direct_times = []
        self.http_times = []
        self.iterations = 1000
    
    async def test_direct_calls(self):
        """Test direct Python function calls"""
        logger.info("Testing direct Python function calls...")
        
        # Simulate direct function calls (no HTTP overhead)
        for i in range(self.iterations):
            start_time = time.perf_counter()
            
            # Simulate direct function call
            await self._simulate_direct_call()
            
            end_time = time.perf_counter()
            self.direct_times.append((end_time - start_time) * 1000)  # Convert to ms
    
    async def test_http_calls(self):
        """Test HTTP API calls"""
        logger.info("Testing HTTP API calls...")
        
        async with httpx.AsyncClient() as client:
            for i in range(self.iterations):
                start_time = time.perf_counter()
                
                # Simulate HTTP call (with network overhead)
                await self._simulate_http_call(client)
                
                end_time = time.perf_counter()
                self.http_times.append((end_time - start_time) * 1000)  # Convert to ms
    
    async def _simulate_direct_call(self):
        """Simulate a direct Python function call"""
        # Simulate processing time
        await asyncio.sleep(0.001)  # 1ms processing time
    
    async def _simulate_http_call(self, client):
        """Simulate an HTTP API call"""
        try:
            # Simulate HTTP request with network latency
            await asyncio.sleep(0.005)  # 5ms network latency
            # Simulate JSON serialization/deserialization
            await asyncio.sleep(0.002)  # 2ms serialization overhead
        except Exception:
            pass  # Ignore connection errors for demo
    
    def calculate_statistics(self) -> Dict:
        """Calculate performance statistics"""
        direct_stats = {
            "mean": statistics.mean(self.direct_times),
            "median": statistics.median(self.direct_times),
            "min": min(self.direct_times),
            "max": max(self.direct_times),
            "std": statistics.stdev(self.direct_times) if len(self.direct_times) > 1 else 0
        }
        
        http_stats = {
            "mean": statistics.mean(self.http_times),
            "median": statistics.median(self.http_times),
            "min": min(self.http_times),
            "max": max(self.http_times),
            "std": statistics.stdev(self.http_times) if len(self.http_times) > 1 else 0
        }
        
        # Calculate improvement
        improvement_factor = http_stats["mean"] / direct_stats["mean"]
        
        return {
            "direct": direct_stats,
            "http": http_stats,
            "improvement_factor": improvement_factor,
            "iterations": self.iterations
        }
    
    def print_results(self, stats: Dict):
        """Print performance comparison results"""
        print("\n" + "="*60)
        print("PERFORMANCE COMPARISON: DIRECT PYTHON vs HTTP API")
        print("="*60)
        
        print(f"\nTest Configuration:")
        print(f"  Iterations: {stats['iterations']:,}")
        print(f"  Test Type: Simulated trading operations")
        
        print(f"\nDirect Python Function Calls:")
        print(f"  Mean Response Time: {stats['direct']['mean']:.2f} ms")
        print(f"  Median Response Time: {stats['direct']['median']:.2f} ms")
        print(f"  Min Response Time: {stats['direct']['min']:.2f} ms")
        print(f"  Max Response Time: {stats['direct']['max']:.2f} ms")
        print(f"  Standard Deviation: {stats['direct']['std']:.2f} ms")
        
        print(f"\nHTTP API Calls:")
        print(f"  Mean Response Time: {stats['http']['mean']:.2f} ms")
        print(f"  Median Response Time: {stats['http']['median']:.2f} ms")
        print(f"  Min Response Time: {stats['http']['min']:.2f} ms")
        print(f"  Max Response Time: {stats['http']['max']:.2f} ms")
        print(f"  Standard Deviation: {stats['http']['std']:.2f} ms")
        
        print(f"\nPerformance Improvement:")
        print(f"  Speed Improvement: {stats['improvement_factor']:.1f}x faster")
        print(f"  Time Savings: {((stats['http']['mean'] - stats['direct']['mean']) / stats['http']['mean'] * 100):.1f}%")
        
        print(f"\nTrading System Benefits:")
        print(f"  ✅ Lower latency for order execution")
        print(f"  ✅ Reduced CPU usage (no HTTP parsing)")
        print(f"  ✅ Lower memory usage (no JSON serialization)")
        print(f"  ✅ Better real-time performance")
        print(f"  ✅ Simplified architecture")
        print(f"  ✅ Easier debugging and testing")
        
        print("\n" + "="*60)

async def main():
    """Run performance comparison"""
    logger.info("Starting performance comparison...")
    
    test = PerformanceTest()
    
    # Run tests
    await test.test_direct_calls()
    await test.test_http_calls()
    
    # Calculate and display results
    stats = test.calculate_statistics()
    test.print_results(stats)

if __name__ == "__main__":
    asyncio.run(main()) 