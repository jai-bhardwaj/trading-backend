#!/usr/bin/env python3
"""
Pinnacle Trading System - Professional Memory Analyzer

Enterprise-grade memory analysis and optimization tool for resource-constrained environments.
Provides comprehensive memory monitoring, optimization recommendations, and system validation.

Usage:
    python3 tools/memory-analyzer.py [--profile] [--optimize] [--report]

Features:
    • Real-time memory monitoring
    • Service-level memory analysis
    • Optimization recommendations
    • Professional reporting
    • 4GB RAM validation

Author: Pinnacle Trading Systems
License: MIT
"""

import asyncio
import json
import os
import platform
import psutil
import requests
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Professional configuration
VERSION = "1.0.0"
ANALYSIS_DURATION_SECONDS = 60
SAMPLE_INTERVAL_SECONDS = 2
MEMORY_WARNING_THRESHOLD_MB = 3000
MEMORY_CRITICAL_THRESHOLD_MB = 3500

# Memory targets for 4GB system (in MB)
MEMORY_TARGETS = {
    'gateway-service': 150,
    'market-data-service': 200,
    'strategy-engine-service': 300,
    'order-management-service': 150,
    'user-authentication-service': 100,  # Disabled by default
    'notification-service': 100,          # Disabled by default
    'frontend': 200,
    'redis': 32,
    'system_buffer': 500,
    'total_budget': 2500
}

# Service configuration
SERVICE_PORTS = {
    'gateway-service': 8000,
    'market-data-service': 8002,
    'strategy-engine-service': 8003,
    'order-management-service': 8004,
    'user-authentication-service': 8001,
    'notification-service': 8005
}

class ProfessionalMemoryAnalyzer:
    """Enterprise-grade memory analysis system."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.samples = []
        self.service_processes = {}
        self.recommendations = []
        
    def display_professional_header(self):
        """Display professional analysis header."""
        header = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    PINNACLE MEMORY ANALYZER v{VERSION}                         ║
║                     Professional System Analysis                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📊 SYSTEM INFORMATION:
   • Platform: {platform.system()} {platform.release()}
   • Python: {sys.version.split()[0]}
   • Analysis Duration: {ANALYSIS_DURATION_SECONDS} seconds
   • Sample Interval: {SAMPLE_INTERVAL_SECONDS} seconds
   • Memory Budget: {MEMORY_TARGETS['total_budget']} MB (4GB optimized)

🎯 ANALYSIS SCOPE:
   • System memory utilization
   • Service-level memory consumption  
   • Memory optimization opportunities
   • Performance bottleneck identification
   • 4GB RAM compliance validation
        """
        print(header)
    
    def get_system_memory_info(self) -> Dict:
        """Get comprehensive system memory information."""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
            return {
            'timestamp': datetime.now().isoformat(),
            'total_mb': round(memory.total / 1024 / 1024, 2),
            'available_mb': round(memory.available / 1024 / 1024, 2),
            'used_mb': round(memory.used / 1024 / 1024, 2),
            'used_percent': round(memory.percent, 2),
            'swap_total_mb': round(swap.total / 1024 / 1024, 2),
            'swap_used_mb': round(swap.used / 1024 / 1024, 2),
            'swap_percent': round(swap.percent, 2) if swap.total > 0 else 0
        }
    
    def discover_trading_services(self) -> Dict:
        """Discover running trading system services."""
        services = {}
        
        for service_name, port in SERVICE_PORTS.items():
            try:
                # Check if service is responding
                response = requests.get(
                    f"http://localhost:{port}/health", 
                    timeout=2
                )
                if response.status_code == 200:
                    # Find process by port
                    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
                        try:
                            connections = proc.connections()
                            for conn in connections:
                                if conn.laddr.port == port:
                                    services[service_name] = {
                                        'pid': proc.pid,
                                        'port': port,
                                        'process': proc,
                                        'status': 'running',
                                        'memory_mb': round(proc.memory_info().rss / 1024 / 1024, 2),
                                        'cpu_percent': round(proc.cpu_percent(interval=0.1), 2)
                                    }
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                            
            except requests.RequestException:
                services[service_name] = {
                    'status': 'not_running',
                    'port': port
                }
                
        return services
    
    def get_redis_memory_usage(self) -> Optional[float]:
        """Get Redis memory usage."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            info = r.info('memory')
            return round(info['used_memory'] / 1024 / 1024, 2)
        except Exception:
            return None
    
    def analyze_frontend_memory(self) -> Optional[Dict]:
        """Analyze Next.js frontend memory usage."""
        frontend_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline())
                if 'next' in cmdline.lower() or 'node' in proc.name().lower():
                    if 'start' in cmdline or '3000' in cmdline:
                        frontend_processes.append({
                            'pid': proc.pid,
                            'name': proc.name(),
                            'memory_mb': round(proc.memory_info().rss / 1024 / 1024, 2),
                            'cpu_percent': round(proc.cpu_percent(interval=0.1), 2)
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if frontend_processes:
            total_memory = sum(p['memory_mb'] for p in frontend_processes)
            return {
                'processes': frontend_processes,
                'total_memory_mb': round(total_memory, 2),
                'process_count': len(frontend_processes)
            }
        return None
    
    async def collect_memory_sample(self) -> Dict:
        """Collect comprehensive memory sample."""
        system_memory = self.get_system_memory_info()
        services = self.discover_trading_services()
        redis_memory = self.get_redis_memory_usage()
        frontend_info = self.analyze_frontend_memory()
        
        # Calculate service memory totals
        service_memory_total = sum(
            service['memory_mb'] for service in services.values() 
            if service.get('memory_mb', 0) > 0
        )
        
        frontend_memory = frontend_info['total_memory_mb'] if frontend_info else 0
        redis_memory_mb = redis_memory if redis_memory else 0
        
        sample = {
            'timestamp': datetime.now().isoformat(),
            'system': system_memory,
            'services': services,
            'redis_memory_mb': redis_memory_mb,
            'frontend': frontend_info,
            'totals': {
                'service_memory_mb': round(service_memory_total, 2),
                'frontend_memory_mb': round(frontend_memory, 2),
                'redis_memory_mb': round(redis_memory_mb, 2),
                'trading_system_total_mb': round(
                    service_memory_total + frontend_memory + redis_memory_mb, 2
                )
            }
        }
        
        return sample
    
    async def run_memory_analysis(self):
        """Run comprehensive memory analysis."""
        print("🔍 Starting professional memory analysis...")
        print(f"   Duration: {ANALYSIS_DURATION_SECONDS} seconds")
        print(f"   Sampling every {SAMPLE_INTERVAL_SECONDS} seconds")
        print()
        
        # Initial sample
        initial_sample = await self.collect_memory_sample()
        self.samples.append(initial_sample)
        
        # Live monitoring
        for i in range(1, ANALYSIS_DURATION_SECONDS // SAMPLE_INTERVAL_SECONDS):
            await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)
            
            sample = await self.collect_memory_sample()
            self.samples.append(sample)
            
            # Display live update
            system_used = sample['system']['used_mb']
            trading_total = sample['totals']['trading_system_total_mb']
            
            print(f"\r📊 Sample {i+1:2d}: System {system_used:,}MB | Trading System {trading_total:,}MB", end="")
        
        print("\n")
        print("✅ Memory analysis completed")
    
    def analyze_performance_trends(self) -> Dict:
        """Analyze memory performance trends."""
        if len(self.samples) < 2:
            return {}
            
        # Calculate trends
        system_memory_trend = []
        trading_memory_trend = []
        
        for sample in self.samples:
            system_memory_trend.append(sample['system']['used_mb'])
            trading_memory_trend.append(sample['totals']['trading_system_total_mb'])
        
        # Statistical analysis
        system_avg = round(sum(system_memory_trend) / len(system_memory_trend), 2)
        system_max = round(max(system_memory_trend), 2)
        system_min = round(min(system_memory_trend), 2)
        
        trading_avg = round(sum(trading_memory_trend) / len(trading_memory_trend), 2)
        trading_max = round(max(trading_memory_trend), 2)
        trading_min = round(min(trading_memory_trend), 2)
        
        return {
            'system_memory': {
                'average_mb': system_avg,
                'peak_mb': system_max,
                'minimum_mb': system_min,
                'variance_mb': round(system_max - system_min, 2)
            },
            'trading_system': {
                'average_mb': trading_avg,
                'peak_mb': trading_max,
                'minimum_mb': trading_min,
                'variance_mb': round(trading_max - trading_min, 2)
            }
        }
    
    def generate_optimization_recommendations(self) -> List[str]:
        """Generate professional optimization recommendations."""
        recommendations = []
        
        if not self.samples:
            return ["No memory samples collected for analysis"]
        
        latest_sample = self.samples[-1]
        trends = self.analyze_performance_trends()
        
        # System memory analysis
        system_used = latest_sample['system']['used_mb']
        total_memory = latest_sample['system']['total_mb']
        
        if system_used > MEMORY_CRITICAL_THRESHOLD_MB:
            recommendations.append("🚨 CRITICAL: System memory usage exceeds safe threshold")
            recommendations.append("   → Immediately restart system to clear memory leaks")
            recommendations.append("   → Consider upgrading to 8GB+ RAM for production use")
        elif system_used > MEMORY_WARNING_THRESHOLD_MB:
            recommendations.append("⚠️  WARNING: High system memory usage detected")
            recommendations.append("   → Monitor memory trends closely")
            recommendations.append("   → Consider closing non-essential applications")
        
        # Service-level analysis
        services = latest_sample['services']
        for service_name, service_info in services.items():
            if service_info.get('memory_mb', 0) > 0:
                target_memory = MEMORY_TARGETS.get(service_name, 200)
                actual_memory = service_info['memory_mb']
                
                if actual_memory > target_memory * 1.5:
                    recommendations.append(f"⚠️  {service_name}: Memory usage {actual_memory}MB exceeds target {target_memory}MB")
                    recommendations.append(f"   → Consider restarting {service_name}")
                elif actual_memory > target_memory * 1.2:
                    recommendations.append(f"📊 {service_name}: Memory usage {actual_memory}MB above optimal {target_memory}MB")
        
        # Redis analysis
        redis_memory = latest_sample['redis_memory_mb']
        if redis_memory and redis_memory > 10:
            recommendations.append(f"📊 Redis: Memory usage {redis_memory}MB above 8MB target")
            recommendations.append("   → Consider reducing cache TTL or clearing cache")
        
        # Trading system total analysis
        trading_total = latest_sample['totals']['trading_system_total_mb']
        if trading_total > MEMORY_TARGETS['total_budget']:
            recommendations.append(f"🚨 Trading system total {trading_total}MB exceeds budget {MEMORY_TARGETS['total_budget']}MB")
            recommendations.append("   → Immediate optimization required")
        elif trading_total > MEMORY_TARGETS['total_budget'] * 0.8:
            recommendations.append(f"⚠️  Trading system using {trading_total}MB ({trading_total/MEMORY_TARGETS['total_budget']*100:.1f}% of budget)")
            recommendations.append("   → Consider proactive optimization")
        
        # Performance trends
        if trends and trends['system_memory']['variance_mb'] > 500:
            recommendations.append("📈 High memory variance detected - possible memory leaks")
            recommendations.append("   → Enable detailed process monitoring")
        
        # 4GB compliance
        if total_memory < 4096:
            recommendations.append(f"⚠️  System has {total_memory/1024:.1f}GB RAM - below 4GB minimum")
            recommendations.append("   → Upgrade system memory for optimal performance")
        
        if not recommendations:
            recommendations.append("✅ System memory usage is optimal")
            recommendations.append("✅ All services within target memory limits")
            recommendations.append("✅ Ready for production deployment")
        
        return recommendations
    
    def calculate_memory_grade(self) -> Tuple[str, str]:
        """Calculate professional memory performance grade."""
        if not self.samples:
            return "F", "No data available"
        
        latest_sample = self.samples[-1]
        trading_total = latest_sample['totals']['trading_system_total_mb']
        system_used = latest_sample['system']['used_mb']
        
        # Grade calculation based on multiple factors
        score = 100
        
        # Trading system memory efficiency (50% weight)
        efficiency_ratio = trading_total / MEMORY_TARGETS['total_budget']
        if efficiency_ratio > 1.0:
            score -= 30  # Exceeds budget
        elif efficiency_ratio > 0.9:
            score -= 15  # Close to budget
        elif efficiency_ratio > 0.8:
            score -= 5   # Good usage
        # Below 0.8 is excellent
        
        # System memory pressure (30% weight)
        if system_used > MEMORY_CRITICAL_THRESHOLD_MB:
            score -= 25
        elif system_used > MEMORY_WARNING_THRESHOLD_MB:
            score -= 15
        elif system_used > 2500:
            score -= 5
        
        # Service compliance (20% weight)
        services = latest_sample['services']
        over_budget_services = 0
        for service_name, service_info in services.items():
            if service_info.get('memory_mb', 0) > 0:
                target = MEMORY_TARGETS.get(service_name, 200)
                if service_info['memory_mb'] > target * 1.2:
                    over_budget_services += 1
        
        if over_budget_services > 0:
            score -= (over_budget_services * 5)
        
        # Convert score to grade
        if score >= 95:
            return "A+", "Excellent - Production ready"
        elif score >= 90:
            return "A", "Very good - Minor optimizations recommended"
        elif score >= 80:
            return "B+", "Good - Some optimization opportunities"
        elif score >= 70:
            return "B", "Acceptable - Optimization recommended"
        elif score >= 60:
            return "C", "Needs improvement - Memory pressure detected"
        elif score >= 50:
            return "D", "Poor - Significant optimization required"
        else:
            return "F", "Critical - System may be unstable"
    
    def generate_professional_report(self):
        """Generate comprehensive professional report."""
        if not self.samples:
            print("❌ No memory samples available for report generation")
            return
        
        print("\n" + "="*80)
        print("📊 PROFESSIONAL MEMORY ANALYSIS REPORT")
        print("="*80)
        
        # Executive Summary
        latest_sample = self.samples[-1]
        trends = self.analyze_performance_trends()
        grade, grade_description = self.calculate_memory_grade()
        
        print(f"\n🎯 EXECUTIVE SUMMARY:")
        print(f"   • Analysis Period: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   • Samples Collected: {len(self.samples)}")
        print(f"   • Memory Grade: {grade} ({grade_description})")
        print(f"   • System Status: {'✅ Stable' if grade in ['A+', 'A', 'B+'] else '⚠️ Needs Attention' if grade in ['B', 'C'] else '🚨 Critical'}")
        
        # Memory Allocation Summary
        print(f"\n💾 MEMORY ALLOCATION SUMMARY:")
        trading_total = latest_sample['totals']['trading_system_total_mb']
        system_used = latest_sample['system']['used_mb']
        system_total = latest_sample['system']['total_mb']
        
        print(f"   • System Total RAM: {system_total:,.0f} MB ({system_total/1024:.1f} GB)")
        print(f"   • System Used RAM: {system_used:,.0f} MB ({system_used/system_total*100:.1f}%)")
        print(f"   • Trading System: {trading_total:,.0f} MB ({trading_total/MEMORY_TARGETS['total_budget']*100:.1f}% of budget)")
        print(f"   • Available RAM: {latest_sample['system']['available_mb']:,.0f} MB")
        
        # Service Breakdown
        print(f"\n🔧 SERVICE MEMORY BREAKDOWN:")
        services = latest_sample['services']
        
        for service_name in SERVICE_PORTS.keys():
            if service_name in services and services[service_name].get('memory_mb', 0) > 0:
                service = services[service_name]
                target = MEMORY_TARGETS.get(service_name, 200)
                actual = service['memory_mb']
                status = "✅" if actual <= target * 1.2 else "⚠️" if actual <= target * 1.5 else "🚨"
                print(f"   {status} {service_name:25}: {actual:6.1f} MB (target: {target} MB)")
            else:
                print(f"   ⚪ {service_name:25}: Not running")
        
        # Infrastructure Services
        redis_memory = latest_sample['redis_memory_mb']
        frontend_memory = latest_sample['totals']['frontend_memory_mb']
        
        if redis_memory:
            status = "✅" if redis_memory <= 10 else "⚠️"
            print(f"   {status} {'Redis Cache':25}: {redis_memory:6.1f} MB (target: 8 MB)")
        
        if frontend_memory:
            status = "✅" if frontend_memory <= 250 else "⚠️"
            print(f"   {status} {'Next.js Frontend':25}: {frontend_memory:6.1f} MB (target: 200 MB)")
        
        # Performance Trends
        if trends:
            print(f"\n📈 PERFORMANCE TRENDS:")
            system_trend = trends['system_memory']
            trading_trend = trends['trading_system']
            
            print(f"   • System Memory:")
            print(f"     → Peak: {system_trend['peak_mb']:,.0f} MB")
            print(f"     → Average: {system_trend['average_mb']:,.0f} MB") 
            print(f"     → Variance: {system_trend['variance_mb']:,.0f} MB")
            
            print(f"   • Trading System:")
            print(f"     → Peak: {trading_trend['peak_mb']:,.0f} MB")
            print(f"     → Average: {trading_trend['average_mb']:,.0f} MB")
            print(f"     → Variance: {trading_trend['variance_mb']:,.0f} MB")
        
        # Optimization Recommendations
        recommendations = self.generate_optimization_recommendations()
        print(f"\n🎯 OPTIMIZATION RECOMMENDATIONS:")
        for recommendation in recommendations:
            print(f"   {recommendation}")
        
        # 4GB Compliance Assessment
        print(f"\n🎖️ 4GB RAM COMPLIANCE:")
        compliance_items = [
            ("Total Memory Budget", trading_total <= MEMORY_TARGETS['total_budget']),
            ("System Memory Pressure", system_used <= MEMORY_WARNING_THRESHOLD_MB),
            ("Service Memory Targets", all(
                services[svc].get('memory_mb', 0) <= MEMORY_TARGETS.get(svc, 200) * 1.5
                for svc in services if services[svc].get('memory_mb', 0) > 0
            )),
            ("Redis Memory Limit", redis_memory <= 12 if redis_memory else True),
            ("Frontend Memory Limit", frontend_memory <= 250 if frontend_memory else True)
        ]
        
        for item, passed in compliance_items:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} {item}")
        
        # Final Assessment
        overall_pass = all(passed for _, passed in compliance_items)
        print(f"\n🏆 OVERALL ASSESSMENT:")
        if overall_pass and grade in ['A+', 'A']:
            print("   🎉 EXCELLENT: System is optimally configured for 4GB deployment")
            print("   🚀 READY: Production deployment recommended")
        elif overall_pass:
            print("   ✅ GOOD: System meets 4GB requirements with minor optimizations")
            print("   📋 MONITOR: Continue monitoring memory trends")
        else:
            print("   ⚠️  OPTIMIZATION REQUIRED: System needs tuning for 4GB deployment")
            print("   🔧 ACTION: Address recommendations before production use")
        
        print("\n" + "="*80)
        print(f"📄 Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 For optimization guides: docs/memory-optimization-guide.md")
        print("="*80)

async def main():
    """Main execution function."""
    analyzer = ProfessionalMemoryAnalyzer()
    
    try:
        analyzer.display_professional_header()
        await analyzer.run_memory_analysis()
        analyzer.generate_professional_report()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Analysis interrupted by user")
        if analyzer.samples:
            print("Generating partial report...")
            analyzer.generate_professional_report()
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 