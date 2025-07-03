#!/usr/bin/env python3
"""
Pinnacle Trading System - Professional Performance Benchmark

Enterprise-grade performance testing and validation tool for trading systems.
Provides comprehensive load testing, latency analysis, and system validation.

Usage:
    python3 tools/performance-benchmark.py [--quick] [--intensive] [--custom]

Features:
    • Load testing with configurable parameters
    • Real-time performance monitoring
    • Professional reporting with grades
    • 4GB RAM optimized testing
    • Comprehensive system validation

Author: Pinnacle Trading Systems
License: MIT
"""

import asyncio
import aiohttp
import json
import os
import platform
import psutil
import statistics
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse

# Professional configuration
VERSION = "1.0.0"
BENCHMARK_TIMEOUT_SECONDS = 30
DEFAULT_TEST_DURATION_SECONDS = 60
DEFAULT_CONCURRENT_USERS = 25
MEMORY_OPTIMIZED_USERS = 15

# Test endpoints configuration
TEST_ENDPOINTS = {
    'health': {
        'url': 'http://localhost:8000/health',
        'method': 'GET',
        'weight': 30,
        'expected_status': 200
    },
    'marketplace': {
        'url': 'http://localhost:8000/marketplace',
        'method': 'GET', 
        'weight': 25,
        'expected_status': 200
    },
    'market_data': {
        'url': 'http://localhost:8002/health',
        'method': 'GET',
        'weight': 20,
        'expected_status': 200
    },
    'strategy_engine': {
        'url': 'http://localhost:8003/health',
        'method': 'GET',
        'weight': 15,
        'expected_status': 200
    },
    'order_service': {
        'url': 'http://localhost:8004/health',
        'method': 'GET',
        'weight': 10,
        'expected_status': 200
    }
}

# Performance grade thresholds
PERFORMANCE_THRESHOLDS = {
    'latency_ms': {
        'A+': 20,
        'A': 50,
        'B+': 100,
        'B': 200,
        'C': 500,
        'D': 1000
    },
    'success_rate': {
        'A+': 99.5,
        'A': 99.0,
        'B+': 98.0,
        'B': 95.0,
        'C': 90.0,
        'D': 80.0
    },
    'throughput_rps': {
        'A+': 25,
        'A': 20,
        'B+': 15,
        'B': 10,
        'C': 5,
        'D': 1
    }
}

class ProfessionalPerformanceBenchmark:
    """Enterprise-grade performance benchmarking system."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = []
        self.system_metrics = []
        self.errors = []
        
    def display_professional_header(self):
        """Display professional benchmark header."""
        header = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                 PINNACLE PERFORMANCE BENCHMARK v{VERSION}                      ║
║                    Professional System Validation                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📊 SYSTEM INFORMATION:
   • Platform: {platform.system()} {platform.release()}
   • Python: {sys.version.split()[0]}
   • Total RAM: {psutil.virtual_memory().total / 1024**3:.1f} GB
   • Available RAM: {psutil.virtual_memory().available / 1024**3:.1f} GB
   • CPU Cores: {psutil.cpu_count()}

🎯 BENCHMARK SCOPE:
   • API Gateway performance validation
   • Service endpoint health testing
   • Load testing with concurrent users
   • Memory pressure analysis
   • Professional performance grading
        """
        print(header)
    
    def check_system_readiness(self) -> bool:
        """Check if trading system is ready for benchmarking."""
        print("🔍 Checking system readiness...")
        
        ready_services = 0
        total_services = len(TEST_ENDPOINTS)
        
        for service_name, config in TEST_ENDPOINTS.items():
            try:
                # Quick health check
                import requests
                response = requests.get(config['url'], timeout=5)
                if response.status_code == config['expected_status']:
                    print(f"   ✅ {service_name}: Ready")
                    ready_services += 1
                else:
                    print(f"   ❌ {service_name}: Not responding (HTTP {response.status_code})")
            except Exception as e:
                print(f"   ❌ {service_name}: Connection failed ({str(e)[:50]}...)")
        
        readiness_percentage = (ready_services / total_services) * 100
        
        if ready_services == total_services:
            print(f"✅ System ready: All {total_services} services responding")
            return True
        elif ready_services >= total_services * 0.8:
            print(f"⚠️  Partial readiness: {ready_services}/{total_services} services ({readiness_percentage:.1f}%)")
            print("   Proceeding with available services...")
            return True
        else:
            print(f"❌ System not ready: Only {ready_services}/{total_services} services ({readiness_percentage:.1f}%)")
            print("   Start the trading system with: ./scripts/start-trading-system.sh start")
            return False
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint_config: Dict) -> Dict:
        """Make a single HTTP request and measure performance."""
        start_time = time.time()
        
        try:
            async with session.request(
                endpoint_config['method'],
                endpoint_config['url'],
                timeout=aiohttp.ClientTimeout(total=BENCHMARK_TIMEOUT_SECONDS)
            ) as response:
                end_time = time.time()
                
                # Read response body
                response_body = await response.text()
                
                return {
                    'success': True,
                    'status_code': response.status,
                    'latency_ms': round((end_time - start_time) * 1000, 2),
                    'response_size': len(response_body),
                    'timestamp': datetime.now().isoformat(),
                    'expected_status': endpoint_config['expected_status'],
                    'status_match': response.status == endpoint_config['expected_status']
                }
                
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'Timeout',
                'latency_ms': BENCHMARK_TIMEOUT_SECONDS * 1000,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)[:100],
                'latency_ms': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    async def monitor_system_metrics(self, duration_seconds: int):
        """Monitor system metrics during benchmark."""
        metrics = []
        
        for _ in range(duration_seconds // 2):  # Sample every 2 seconds
            try:
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                metrics.append({
                    'timestamp': datetime.now().isoformat(),
                    'memory_used_mb': round(memory.used / 1024 / 1024, 2),
                    'memory_percent': round(memory.percent, 2),
                    'cpu_percent': round(cpu_percent, 2),
                    'available_memory_mb': round(memory.available / 1024 / 1024, 2)
                })
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Warning: Metrics collection error: {e}")
                
        return metrics
    
    async def run_load_test(self, concurrent_users: int, duration_seconds: int) -> Dict:
        """Run comprehensive load test."""
        print(f"🚀 Starting load test...")
        print(f"   • Concurrent Users: {concurrent_users}")
        print(f"   • Duration: {duration_seconds} seconds")
        print(f"   • Target Endpoints: {len(TEST_ENDPOINTS)}")
        print()
        
        # Start system monitoring
        metrics_task = asyncio.create_task(
            self.monitor_system_metrics(duration_seconds)
        )
        
        # Prepare request tasks
        async def user_session():
            """Simulate a single user session."""
            session_results = []
            
            connector = aiohttp.TCPConnector(
                limit=5,  # Limit connections for 4GB optimization
                limit_per_host=2,
                ttl_dns_cache=300,
                ttl_dns_cache_resolved=300
            )
            
            async with aiohttp.ClientSession(connector=connector) as session:
                end_time = time.time() + duration_seconds
                
                while time.time() < end_time:
                    # Select endpoint based on weight
                    import random
                    total_weight = sum(config['weight'] for config in TEST_ENDPOINTS.values())
                    random_value = random.randint(1, total_weight)
                    
                    cumulative_weight = 0
                    selected_endpoint = None
                    
                    for endpoint_name, config in TEST_ENDPOINTS.items():
                        cumulative_weight += config['weight']
                        if random_value <= cumulative_weight:
                            selected_endpoint = (endpoint_name, config)
                            break
                    
                    if selected_endpoint:
                        endpoint_name, endpoint_config = selected_endpoint
                        result = await self.make_request(session, endpoint_config)
                        result['endpoint'] = endpoint_name
                        session_results.append(result)
                    
                    # Small delay to prevent overwhelming (4GB optimization)
                    await asyncio.sleep(0.1)
                    
            return session_results
        
        # Start user sessions
        print("📊 Load test in progress...")
        user_tasks = [asyncio.create_task(user_session()) for _ in range(concurrent_users)]
        
        # Show progress
        for i in range(duration_seconds):
            await asyncio.sleep(1)
            print(f"\r   Progress: {i+1}/{duration_seconds} seconds ({(i+1)/duration_seconds*100:.1f}%)", end="")
        
        print("\n")
        
        # Collect results
        print("🔍 Collecting results...")
        all_results = []
        for completed_task in await asyncio.gather(*user_tasks):
            all_results.extend(completed_task)
        
        # Stop monitoring
        system_metrics = await metrics_task
        
        print("✅ Load test completed")
        
        return {
            'requests': all_results,
            'system_metrics': system_metrics,
            'test_config': {
                'concurrent_users': concurrent_users,
                'duration_seconds': duration_seconds,
                'endpoints_tested': list(TEST_ENDPOINTS.keys())
            }
        }
    
    def analyze_performance_results(self, test_results: Dict) -> Dict:
        """Analyze performance test results."""
        requests = test_results['requests']
        system_metrics = test_results['system_metrics']
        
        if not requests:
            return {'error': 'No requests completed'}
        
        # Request analysis
        successful_requests = [r for r in requests if r.get('success', False)]
        failed_requests = [r for r in requests if not r.get('success', False)]
        
        total_requests = len(requests)
        success_count = len(successful_requests)
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        # Latency analysis
        latencies = [r['latency_ms'] for r in successful_requests if 'latency_ms' in r]
        
        if latencies:
            avg_latency = round(statistics.mean(latencies), 2)
            median_latency = round(statistics.median(latencies), 2)
            p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
            p99_latency = round(sorted(latencies)[int(len(latencies) * 0.99)], 2)
            min_latency = round(min(latencies), 2)
            max_latency = round(max(latencies), 2)
        else:
            avg_latency = median_latency = p95_latency = p99_latency = min_latency = max_latency = 0
        
        # Throughput analysis
        test_duration = test_results['test_config']['duration_seconds']
        requests_per_second = round(total_requests / test_duration, 2) if test_duration > 0 else 0
        successful_rps = round(success_count / test_duration, 2) if test_duration > 0 else 0
        
        # Endpoint analysis
        endpoint_stats = {}
        for endpoint_name in TEST_ENDPOINTS.keys():
            endpoint_requests = [r for r in requests if r.get('endpoint') == endpoint_name]
            endpoint_successes = [r for r in endpoint_requests if r.get('success', False)]
            
            if endpoint_requests:
                endpoint_success_rate = len(endpoint_successes) / len(endpoint_requests) * 100
                endpoint_latencies = [r['latency_ms'] for r in endpoint_successes if 'latency_ms' in r]
                endpoint_avg_latency = statistics.mean(endpoint_latencies) if endpoint_latencies else 0
                
                endpoint_stats[endpoint_name] = {
                    'total_requests': len(endpoint_requests),
                    'successful_requests': len(endpoint_successes),
                    'success_rate': round(endpoint_success_rate, 2),
                    'avg_latency_ms': round(endpoint_avg_latency, 2),
                    'requests_per_second': round(len(endpoint_requests) / test_duration, 2)
                }
        
        # System metrics analysis
        if system_metrics:
            memory_usage = [m['memory_used_mb'] for m in system_metrics]
            cpu_usage = [m['cpu_percent'] for m in system_metrics]
            
            system_analysis = {
                'peak_memory_mb': round(max(memory_usage), 2) if memory_usage else 0,
                'avg_memory_mb': round(statistics.mean(memory_usage), 2) if memory_usage else 0,
                'peak_cpu_percent': round(max(cpu_usage), 2) if cpu_usage else 0,
                'avg_cpu_percent': round(statistics.mean(cpu_usage), 2) if cpu_usage else 0,
                'memory_variance_mb': round(max(memory_usage) - min(memory_usage), 2) if memory_usage else 0
            }
        else:
            system_analysis = {}
        
        # Error analysis
        error_types = {}
        for req in failed_requests:
            error = req.get('error', 'Unknown')
            error_types[error] = error_types.get(error, 0) + 1
        
        return {
            'summary': {
                'total_requests': total_requests,
                'successful_requests': success_count,
                'failed_requests': len(failed_requests),
                'success_rate_percent': round(success_rate, 2),
                'requests_per_second': requests_per_second,
                'successful_rps': successful_rps
            },
            'latency': {
                'average_ms': avg_latency,
                'median_ms': median_latency,
                'p95_ms': p95_latency,
                'p99_ms': p99_latency,
                'min_ms': min_latency,
                'max_ms': max_latency
            },
            'endpoints': endpoint_stats,
            'system': system_analysis,
            'errors': error_types
        }
    
    def calculate_performance_grade(self, analysis: Dict) -> Tuple[str, str]:
        """Calculate professional performance grade."""
        if 'error' in analysis:
            return "F", "Analysis failed"
        
        summary = analysis['summary']
        latency = analysis['latency']
        
        # Calculate individual component grades
        grades = []
        
        # Latency grade (40% weight)
        avg_latency = latency['average_ms']
        for grade, threshold in PERFORMANCE_THRESHOLDS['latency_ms'].items():
            if avg_latency <= threshold:
                grades.append((grade, 40))
                break
        else:
            grades.append(("F", 40))
        
        # Success rate grade (35% weight)
        success_rate = summary['success_rate_percent']
        for grade, threshold in PERFORMANCE_THRESHOLDS['success_rate'].items():
            if success_rate >= threshold:
                grades.append((grade, 35))
                break
        else:
            grades.append(("F", 35))
        
        # Throughput grade (25% weight)
        throughput = summary['successful_rps']
        for grade, threshold in PERFORMANCE_THRESHOLDS['throughput_rps'].items():
            if throughput >= threshold:
                grades.append((grade, 25))
                break
        else:
            grades.append(("F", 25))
        
        # Calculate weighted average
        grade_values = {"A+": 95, "A": 90, "B+": 85, "B": 80, "C": 70, "D": 60, "F": 0}
        weighted_score = sum(grade_values[grade] * weight / 100 for grade, weight in grades)
        
        # Convert back to letter grade
        if weighted_score >= 95:
            final_grade = "A+"
            description = "Excellent - Production ready"
        elif weighted_score >= 90:
            final_grade = "A"
            description = "Very good - Minor optimizations possible"
        elif weighted_score >= 85:
            final_grade = "B+"
            description = "Good - Some optimization opportunities"
        elif weighted_score >= 80:
            final_grade = "B"
            description = "Acceptable - Optimization recommended"
        elif weighted_score >= 70:
            final_grade = "C"
            description = "Needs improvement - Performance issues detected"
        elif weighted_score >= 60:
            final_grade = "D"
            description = "Poor - Significant optimization required"
        else:
            final_grade = "F"
            description = "Critical - System may be unstable"
        
        return final_grade, description
    
    def generate_professional_report(self, test_results: Dict, analysis: Dict):
        """Generate comprehensive professional report."""
        print("\n" + "="*80)
        print("📊 PROFESSIONAL PERFORMANCE BENCHMARK REPORT")
        print("="*80)
        
        # Executive Summary
        grade, grade_description = self.calculate_performance_grade(analysis)
        
        print(f"\n🎯 EXECUTIVE SUMMARY:")
        print(f"   • Benchmark Period: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   • Test Duration: {test_results['test_config']['duration_seconds']} seconds")
        print(f"   • Concurrent Users: {test_results['test_config']['concurrent_users']}")
        print(f"   • Performance Grade: {grade} ({grade_description})")
        print(f"   • System Status: {'✅ Production Ready' if grade in ['A+', 'A'] else '⚠️ Needs Attention' if grade in ['B+', 'B'] else '🚨 Critical Issues'}")
        
        # Performance Summary
        summary = analysis['summary']
        latency = analysis['latency']
        
        print(f"\n⚡ PERFORMANCE SUMMARY:")
        print(f"   • Total Requests: {summary['total_requests']:,}")
        print(f"   • Successful Requests: {summary['successful_requests']:,}")
        print(f"   • Success Rate: {summary['success_rate_percent']:.2f}%")
        print(f"   • Throughput: {summary['successful_rps']:.2f} requests/second")
        print(f"   • Average Latency: {latency['average_ms']:.2f}ms")
        print(f"   • 95th Percentile: {latency['p95_ms']:.2f}ms")
        
        # Endpoint Performance
        endpoints = analysis['endpoints']
        if endpoints:
            print(f"\n🔧 ENDPOINT PERFORMANCE:")
            for endpoint_name, stats in endpoints.items():
                status = "✅" if stats['success_rate'] >= 99 else "⚠️" if stats['success_rate'] >= 95 else "🚨"
                print(f"   {status} {endpoint_name:20}: {stats['avg_latency_ms']:6.1f}ms avg, {stats['success_rate']:5.1f}% success, {stats['requests_per_second']:5.1f} rps")
        
        # System Resource Usage
        system = analysis.get('system', {})
        if system:
            print(f"\n💾 SYSTEM RESOURCE USAGE:")
            memory_status = "✅" if system['peak_memory_mb'] < 3000 else "⚠️" if system['peak_memory_mb'] < 3500 else "🚨"
            cpu_status = "✅" if system['peak_cpu_percent'] < 80 else "⚠️" if system['peak_cpu_percent'] < 90 else "🚨"
            
            print(f"   {memory_status} Peak Memory: {system['peak_memory_mb']:,.0f} MB")
            print(f"   {memory_status} Average Memory: {system['avg_memory_mb']:,.0f} MB")
            print(f"   {cpu_status} Peak CPU: {system['peak_cpu_percent']:.1f}%")
            print(f"   {cpu_status} Average CPU: {system['avg_cpu_percent']:.1f}%")
        
        # Performance Analysis
        print(f"\n📈 DETAILED LATENCY ANALYSIS:")
        print(f"   • Minimum: {latency['min_ms']:.2f}ms")
        print(f"   • Average: {latency['average_ms']:.2f}ms")
        print(f"   • Median: {latency['median_ms']:.2f}ms")
        print(f"   • 95th Percentile: {latency['p95_ms']:.2f}ms")
        print(f"   • 99th Percentile: {latency['p99_ms']:.2f}ms")
        print(f"   • Maximum: {latency['max_ms']:.2f}ms")
        
        # Error Analysis
        errors = analysis.get('errors', {})
        if errors:
            print(f"\n🚨 ERROR ANALYSIS:")
            for error_type, count in errors.items():
                error_rate = (count / summary['total_requests']) * 100
                print(f"   • {error_type}: {count} occurrences ({error_rate:.2f}%)")
    else:
            print(f"\n✅ ERROR ANALYSIS:")
            print(f"   • No errors detected during benchmark")
        
        # 4GB RAM Compliance
        print(f"\n🎖️ 4GB RAM COMPLIANCE:")
        compliance_items = [
            ("Request Success Rate", summary['success_rate_percent'] >= 95),
            ("Average Latency", latency['average_ms'] <= 100),
            ("Memory Usage", system.get('peak_memory_mb', 0) <= 3500),
            ("CPU Efficiency", system.get('peak_cpu_percent', 0) <= 90),
            ("Throughput Target", summary['successful_rps'] >= 10)
        ]
        
        for item, passed in compliance_items:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} {item}")
        
        # Recommendations
        print(f"\n🎯 OPTIMIZATION RECOMMENDATIONS:")
    recommendations = []
    
        if latency['average_ms'] > 100:
            recommendations.append("⚠️  High latency detected - optimize service response times")
        if summary['success_rate_percent'] < 99:
            recommendations.append("⚠️  Error rate above target - investigate failed requests")
        if system.get('peak_memory_mb', 0) > 3000:
            recommendations.append("⚠️  Memory usage high - consider optimization")
        if summary['successful_rps'] < 20:
            recommendations.append("📊 Throughput below optimal - check for bottlenecks")
    
    if not recommendations:
            recommendations.extend([
                "✅ Performance meets all targets",
                "✅ System ready for production deployment",
                "✅ Continue monitoring during live trading"
            ])
        
        for recommendation in recommendations:
            print(f"   {recommendation}")
        
        # Final Assessment
        overall_pass = all(passed for _, passed in compliance_items)
        print(f"\n🏆 OVERALL ASSESSMENT:")
        if overall_pass and grade in ['A+', 'A']:
            print("   🎉 EXCELLENT: System demonstrates production-grade performance")
            print("   🚀 READY: Approved for live trading deployment")
        elif overall_pass:
            print("   ✅ GOOD: System meets performance requirements")
            print("   📋 MONITOR: Continue performance monitoring")
        else:
            print("   ⚠️  OPTIMIZATION REQUIRED: Address performance issues before production")
            print("   🔧 ACTION: Review recommendations and re-test")
        
        print("\n" + "="*80)
        print(f"📄 Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 For optimization guides: docs/memory-optimization-guide.md")
        print("="*80)

async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Professional performance benchmark for Pinnacle Trading System"
    )
    parser.add_argument("--quick", action="store_true", help="Quick test (30s, 10 users)")
    parser.add_argument("--intensive", action="store_true", help="Intensive test (120s, 50 users)")
    parser.add_argument("--users", type=int, help="Custom concurrent users")
    parser.add_argument("--duration", type=int, help="Custom duration in seconds")
    
    args = parser.parse_args()
    
    # Determine test parameters
    if args.quick:
        concurrent_users = 10
        duration_seconds = 30
    elif args.intensive:
        concurrent_users = 50
        duration_seconds = 120
    else:
        # Memory-optimized default for 4GB systems
        concurrent_users = args.users or MEMORY_OPTIMIZED_USERS
        duration_seconds = args.duration or DEFAULT_TEST_DURATION_SECONDS
    
    benchmark = ProfessionalPerformanceBenchmark()
    
    try:
        benchmark.display_professional_header()
        
        # Check system readiness
        if not benchmark.check_system_readiness():
            sys.exit(1)
        
        # Run benchmark
        test_results = await benchmark.run_load_test(concurrent_users, duration_seconds)
        
        # Analyze results
        analysis = benchmark.analyze_performance_results(test_results)
        
        # Generate report
        benchmark.generate_professional_report(test_results, analysis)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 