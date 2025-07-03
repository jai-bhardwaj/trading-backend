#!/usr/bin/env python3
"""
HIGH-PERFORMANCE Trading System Benchmark
Targets 10,000+ requests/second with <5ms latency
"""

import asyncio
import aiohttp
import time
import statistics
import json
import psutil
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import high-performance config
try:
    from config.high_performance_config import HighPerformanceConfig, PerformanceAnalyzer
except ImportError:
    # Fallback config if import fails
    class HighPerformanceConfig:
        HTTP_POOL_SIZE = 1000
        HTTP_POOL_PER_HOST = 200
        MAX_CONCURRENT_REQUESTS = 2000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkConfig:
    """High-performance benchmark configuration"""
    
    # Test Parameters
    WARM_UP_DURATION = 10  # seconds
    TEST_DURATION = 60  # seconds
    MAX_CONCURRENT_USERS = 500  # Concurrent requests
    TARGET_RPS = 10000  # Target requests per second
    
    # Connection Settings (NO artificial delays)
    CONNECTION_TIMEOUT = 5.0  # seconds
    REQUEST_TIMEOUT = 2.0  # seconds
    KEEPALIVE_TIMEOUT = 30  # seconds
    
    # Performance Thresholds
    MAX_ACCEPTABLE_LATENCY = 50  # ms
    MIN_ACCEPTABLE_RPS = 5000  # requests/second
    MAX_ERROR_RATE = 1.0  # percent

# High-performance test endpoints
PERFORMANCE_ENDPOINTS = {
    "health_check": {
        "method": "GET",
        "url": "http://localhost:8000/health",
        "expected_status": 200,
        "weight": 10  # Higher weight = more frequent calls
    },
    "market_data": {
        "method": "GET", 
        "url": "http://localhost:8000/market/realtime/RELIANCE",
        "expected_status": 200,
        "weight": 25
    },
    "user_dashboard": {
        "method": "GET",
        "url": "http://localhost:8001/health", 
        "expected_status": 200,
        "weight": 15
    },
    "strategy_status": {
        "method": "GET",
        "url": "http://localhost:8003/health",
        "expected_status": 200,
        "weight": 20
    },
    "order_status": {
        "method": "GET",
        "url": "http://localhost:8004/health",
        "expected_status": 200,
        "weight": 30
    }
}

class HighPerformanceBenchmark:
    """Professional-grade benchmark for trading systems"""
    
    def __init__(self):
        self.config = BenchmarkConfig()
        self.hp_config = HighPerformanceConfig()
        self.results: List[Dict] = []
        self.system_metrics: List[Dict] = []
        self.error_count = 0
        self.total_requests = 0
        
    async def create_optimized_session(self) -> aiohttp.ClientSession:
        """Create optimized HTTP session for maximum performance"""
        
        # High-performance TCP connector
        connector = aiohttp.TCPConnector(
            limit=self.hp_config.HTTP_POOL_SIZE,  # 1000 total connections
            limit_per_host=self.hp_config.HTTP_POOL_PER_HOST,  # 200 per host
            ttl_dns_cache=300,
            ttl_dns_cache_resolved=300,
            use_dns_cache=True,
            keepalive_timeout=self.config.KEEPALIVE_TIMEOUT,
            enable_cleanup_closed=True,
            force_close=False  # Reuse connections
        )
        
        # Optimized timeout settings
        timeout = aiohttp.ClientTimeout(
            total=self.config.REQUEST_TIMEOUT,
            connect=self.config.CONNECTION_TIMEOUT,
            sock_read=self.config.REQUEST_TIMEOUT
        )
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Connection': 'keep-alive',
                'Keep-Alive': 'timeout=30',
                'User-Agent': 'Pinnacle-Trading-Benchmark/2.0'
            }
        )
    
    async def make_high_performance_request(
        self, 
        session: aiohttp.ClientSession, 
        endpoint: Dict
    ) -> Dict:
        """Make optimized HTTP request with performance tracking"""
        
        start_time = time.perf_counter()
        
        try:
            async with session.request(
                endpoint['method'],
                endpoint['url']
            ) as response:
                end_time = time.perf_counter()
                
                # Read response efficiently
                response_text = await response.text()
                
                latency_ms = (end_time - start_time) * 1000
                
                return {
                    'success': True,
                    'status_code': response.status,
                    'latency_ms': latency_ms,
                    'response_size': len(response_text),
                    'timestamp': time.time(),
                    'expected_status': endpoint['expected_status'],
                    'status_match': response.status == endpoint['expected_status']
                }
                
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'Timeout',
                'latency_ms': self.config.REQUEST_TIMEOUT * 1000,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)[:100],
                'latency_ms': 0,
                'timestamp': time.time()
            }
    
    async def high_performance_worker(
        self, 
        session: aiohttp.ClientSession, 
        duration: int,
        worker_id: int
    ) -> List[Dict]:
        """High-performance worker that makes requests continuously"""
        
        worker_results = []
        end_time = time.time() + duration
        request_count = 0
        
        while time.time() < end_time:
            # Select endpoint based on weight (more realistic traffic)
            endpoint = self.select_weighted_endpoint()
            
            # Make request
            result = await self.make_high_performance_request(session, endpoint)
            result['worker_id'] = worker_id
            result['endpoint'] = endpoint['url']
            
            worker_results.append(result)
            request_count += 1
            
            # NO artificial delay - maximum performance
            
        logger.info(f"Worker {worker_id} completed {request_count} requests")
        return worker_results
    
    def select_weighted_endpoint(self) -> Dict:
        """Select endpoint based on weight for realistic traffic distribution"""
        import random
        
        total_weight = sum(config['weight'] for config in PERFORMANCE_ENDPOINTS.values())
        random_value = random.randint(1, total_weight)
        
        cumulative_weight = 0
        for endpoint_name, config in PERFORMANCE_ENDPOINTS.items():
            cumulative_weight += config['weight']
            if random_value <= cumulative_weight:
                return config
        
        # Fallback
        return list(PERFORMANCE_ENDPOINTS.values())[0]
    
    async def monitor_system_performance(self, duration: int):
        """Monitor system performance during benchmark"""
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                self.system_metrics.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_percent': memory.percent,
                    'available_memory_gb': memory.available / (1024**3)
                })
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"System monitoring error: {e}")
    
    async def run_high_performance_test(
        self, 
        concurrent_users: int = None, 
        duration: int = None
    ) -> Dict:
        """Run high-performance load test"""
        
        concurrent_users = concurrent_users or self.config.MAX_CONCURRENT_USERS
        duration = duration or self.config.TEST_DURATION
        
        print("🚀 HIGH-PERFORMANCE TRADING SYSTEM BENCHMARK")
        print("=" * 80)
        print(f"🎯 Target: {self.config.TARGET_RPS:,} requests/second")
        print(f"👥 Concurrent Users: {concurrent_users}")
        print(f"⏱️  Duration: {duration} seconds")
        print(f"🔗 Connection Pool: {self.hp_config.HTTP_POOL_SIZE} total, {self.hp_config.HTTP_POOL_PER_HOST} per host")
        print()
        
        # Start system monitoring
        monitor_task = asyncio.create_task(
            self.monitor_system_performance(duration + 10)
        )
        
        # Create optimized session
        session = await self.create_optimized_session()
        
        try:
            # Warm-up phase
            print("🔥 Warming up system...")
            warmup_tasks = [
                asyncio.create_task(
                    self.high_performance_worker(session, self.config.WARM_UP_DURATION, i)
                ) for i in range(min(50, concurrent_users))
            ]
            await asyncio.gather(*warmup_tasks)
            print("✅ Warm-up completed")
            print()
            
            # Main benchmark
            print("📊 Starting high-performance benchmark...")
            start_time = time.time()
            
            # Create all worker tasks
            worker_tasks = [
                asyncio.create_task(
                    self.high_performance_worker(session, duration, i)
                ) for i in range(concurrent_users)
            ]
            
            # Show real-time progress
            progress_task = asyncio.create_task(
                self.show_realtime_progress(duration, start_time)
            )
            
            # Wait for completion
            all_results = await asyncio.gather(*worker_tasks)
            progress_task.cancel()
            
            end_time = time.time()
            
            # Flatten results
            self.results = [result for worker_results in all_results for result in worker_results]
            
        finally:
            await session.close()
            monitor_task.cancel()
        
        # Calculate and display results
        return self.calculate_performance_metrics(start_time, end_time)
    
    async def show_realtime_progress(self, duration: int, start_time: float):
        """Show real-time progress during benchmark"""
        
        for i in range(duration):
            await asyncio.sleep(1)
            elapsed = time.time() - start_time
            progress = (elapsed / duration) * 100
            
            # Get current RPS estimate
            current_results = len([r for r in self.results if r.get('timestamp', 0) > start_time])
            current_rps = current_results / elapsed if elapsed > 0 else 0
            
            print(f"\r📈 Progress: {progress:.1f}% | RPS: {current_rps:.0f} | Elapsed: {elapsed:.1f}s", end="")
        
        print()  # New line after progress
    
    def calculate_performance_metrics(self, start_time: float, end_time: float) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        total_duration = end_time - start_time
        successful_requests = [r for r in self.results if r.get('success', False)]
        failed_requests = [r for r in self.results if not r.get('success', False)]
        
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Basic metrics
        total_requests = len(self.results)
        successful_count = len(successful_requests)
        failure_rate = (len(failed_requests) / total_requests) * 100
        
        # Performance metrics
        if successful_requests:
            latencies = [r['latency_ms'] for r in successful_requests]
            avg_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            avg_latency = median_latency = p95_latency = p99_latency = min_latency = max_latency = 0
        
        # Throughput
        rps = total_requests / total_duration
        successful_rps = successful_count / total_duration
        
        # System metrics
        if self.system_metrics:
            avg_cpu = statistics.mean([m['cpu_percent'] for m in self.system_metrics])
            max_memory = max([m['memory_used_gb'] for m in self.system_metrics])
            avg_memory = statistics.mean([m['memory_used_gb'] for m in self.system_metrics])
        else:
            avg_cpu = max_memory = avg_memory = 0
        
        # Performance grade
        grade = self.calculate_performance_grade(successful_rps, avg_latency, failure_rate)
        
        results = {
            "benchmark_summary": {
                "total_requests": total_requests,
                "successful_requests": successful_count,
                "failed_requests": len(failed_requests),
                "failure_rate_percent": round(failure_rate, 2),
                "test_duration_seconds": round(total_duration, 2)
            },
            "performance_metrics": {
                "requests_per_second": round(rps, 1),
                "successful_rps": round(successful_rps, 1),
                "average_latency_ms": round(avg_latency, 2),
                "median_latency_ms": round(median_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "p99_latency_ms": round(p99_latency, 2),
                "min_latency_ms": round(min_latency, 2),
                "max_latency_ms": round(max_latency, 2)
            },
            "system_metrics": {
                "average_cpu_percent": round(avg_cpu, 1),
                "average_memory_gb": round(avg_memory, 2),
                "peak_memory_gb": round(max_memory, 2),
                "memory_efficiency": "Excellent" if max_memory < 3.0 else "Good" if max_memory < 3.5 else "Fair"
            },
            "performance_grade": grade
        }
        
        self.display_results(results)
        return results
    
    def calculate_performance_grade(self, rps: float, latency: float, failure_rate: float) -> str:
        """Calculate performance grade based on metrics"""
        
        # RPS scoring
        if rps >= 10000:
            rps_score = 100
        elif rps >= 5000:
            rps_score = 80
        elif rps >= 1000:
            rps_score = 60
        elif rps >= 500:
            rps_score = 40
        else:
            rps_score = 20
        
        # Latency scoring
        if latency <= 5:
            latency_score = 100
        elif latency <= 10:
            latency_score = 80
        elif latency <= 25:
            latency_score = 60
        elif latency <= 50:
            latency_score = 40
        else:
            latency_score = 20
        
        # Reliability scoring
        if failure_rate == 0:
            reliability_score = 100
        elif failure_rate <= 0.1:
            reliability_score = 90
        elif failure_rate <= 1:
            reliability_score = 70
        elif failure_rate <= 5:
            reliability_score = 50
        else:
            reliability_score = 20
        
        # Overall score
        overall_score = (rps_score * 0.4 + latency_score * 0.3 + reliability_score * 0.3)
        
        if overall_score >= 90:
            return "A+ (Excellent)"
        elif overall_score >= 80:
            return "A (Very Good)"
        elif overall_score >= 70:
            return "B+ (Good)"
        elif overall_score >= 60:
            return "B (Fair)"
        else:
            return "C (Needs Improvement)"
    
    def display_results(self, results: Dict):
        """Display comprehensive benchmark results"""
        
        print("\n🏆 HIGH-PERFORMANCE BENCHMARK RESULTS")
        print("=" * 80)
        
        # Summary
        summary = results["benchmark_summary"]
        print(f"📊 BENCHMARK SUMMARY:")
        print(f"   • Total Requests: {summary['total_requests']:,}")
        print(f"   • Successful: {summary['successful_requests']:,}")
        print(f"   • Failed: {summary['failed_requests']:,}")
        print(f"   • Failure Rate: {summary['failure_rate_percent']}%")
        print(f"   • Duration: {summary['test_duration_seconds']}s")
        print()
        
        # Performance
        perf = results["performance_metrics"]
        print(f"⚡ PERFORMANCE METRICS:")
        print(f"   • Throughput: {perf['successful_rps']:.1f} requests/second")
        print(f"   • Average Latency: {perf['average_latency_ms']:.2f}ms")
        print(f"   • Median Latency: {perf['median_latency_ms']:.2f}ms")
        print(f"   • 95th Percentile: {perf['p95_latency_ms']:.2f}ms")
        print(f"   • 99th Percentile: {perf['p99_latency_ms']:.2f}ms")
        print(f"   • Min/Max Latency: {perf['min_latency_ms']:.2f}ms / {perf['max_latency_ms']:.2f}ms")
        print()
        
        # System
        system = results["system_metrics"]
        print(f"🖥️  SYSTEM METRICS:")
        print(f"   • Average CPU: {system['average_cpu_percent']}%")
        print(f"   • Average Memory: {system['average_memory_gb']:.2f}GB")
        print(f"   • Peak Memory: {system['peak_memory_gb']:.2f}GB")
        print(f"   • Memory Efficiency: {system['memory_efficiency']}")
        print()
        
        # Grade
        grade = results["performance_grade"]
        print(f"🏅 PERFORMANCE GRADE: {grade}")
        print()
        
        # Recommendations
        rps = perf['successful_rps']
        latency = perf['average_latency_ms']
        
        print("💡 RECOMMENDATIONS:")
        if rps >= 10000:
            print("   ✅ Excellent throughput achieved!")
        elif rps >= 5000:
            print("   🟡 Good throughput, consider optimizing for 10k+ RPS")
        else:
            print("   🔴 Low throughput - investigate bottlenecks")
        
        if latency <= 5:
            print("   ✅ Excellent latency!")
        elif latency <= 25:
            print("   🟡 Good latency, room for improvement")
        else:
            print("   🔴 High latency - optimize connection pooling")
        
        print("=" * 80)

async def main():
    """Run high-performance benchmark"""
    
    benchmark = HighPerformanceBenchmark()
    
    print("🚀 Pinnacle Trading System - High Performance Benchmark")
    print("Targeting 10,000+ requests/second with <5ms latency")
    print("=" * 80)
    
    # Check system configuration
    analyzer = PerformanceAnalyzer()
    print(analyzer.get_performance_report())
    
    print("\n🔥 Starting benchmark in 3 seconds...")
    await asyncio.sleep(3)
    
    # Run benchmark
    await benchmark.run_high_performance_test(
        concurrent_users=300,  # Optimized for 4GB
        duration=30  # 30 second test
    )

if __name__ == "__main__":
    asyncio.run(main()) 