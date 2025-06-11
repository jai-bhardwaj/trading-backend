#!/usr/bin/env python3
"""
Trading System Capacity Monitor

This script monitors your trading system's capacity and provides alerts
when approaching limits.
"""

import time
import psutil
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any

class CapacityMonitor:
    """Monitor system capacity and strategy performance"""
    
    def __init__(self):
        self.cpu_threshold = 80.0  # Alert if CPU > 80%
        self.memory_threshold = 85.0  # Alert if memory > 85%
        self.load_threshold = 3.0  # Alert if load average > 3.0
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Docker container stats
            docker_stats = self.get_docker_stats()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_available_mb': memory_available_mb,
                'load_average': load_avg,
                'docker_stats': docker_stats,
                'alerts': self.check_alerts(cpu_percent, memory_percent, load_avg)
            }
        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def get_docker_stats(self) -> Dict[str, Dict[str, str]]:
        """Get Docker container resource usage"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format',
                'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return {}
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            stats = {}
            
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        name = parts[0].strip()
                        if 'trading' in name:  # Only trading-related containers
                            stats[name] = {
                                'cpu_percent': parts[1].strip(),
                                'memory_usage': parts[2].strip(),
                                'memory_percent': parts[3].strip()
                            }
            
            return stats
        except Exception as e:
            return {'error': str(e)}
    
    def check_alerts(self, cpu: float, memory: float, load: float) -> List[str]:
        """Check for alerts based on thresholds"""
        alerts = []
        
        if cpu > self.cpu_threshold:
            alerts.append(f"🔥 HIGH CPU: {cpu:.1f}% (threshold: {self.cpu_threshold}%)")
        
        if memory > self.memory_threshold:
            alerts.append(f"🧠 HIGH MEMORY: {memory:.1f}% (threshold: {self.memory_threshold}%)")
        
        if load > self.load_threshold:
            alerts.append(f"⚡ HIGH LOAD: {load:.2f} (threshold: {self.load_threshold})")
        
        return alerts
    
    def estimate_strategy_capacity(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate remaining strategy capacity"""
        cpu_percent = current_metrics.get('cpu_percent', 0)
        memory_percent = current_metrics.get('memory_percent', 0)
        
        # Conservative estimates based on analysis
        cpu_per_strategy = 5.0  # 5% CPU per strategy
        memory_per_strategy_mb = 10  # 10MB per strategy
        
        # Calculate remaining capacity
        remaining_cpu = max(0, self.cpu_threshold - cpu_percent)
        remaining_memory_mb = current_metrics.get('memory_available_mb', 0)
        
        # Strategy limits
        cpu_based_limit = int(remaining_cpu / cpu_per_strategy)
        memory_based_limit = int(remaining_memory_mb / memory_per_strategy_mb)
        
        # Conservative estimate
        safe_limit = min(cpu_based_limit, memory_based_limit)
        
        return {
            'cpu_based_limit': cpu_based_limit,
            'memory_based_limit': memory_based_limit,
            'safe_additional_strategies': max(0, safe_limit),
            'bottleneck': 'CPU' if cpu_based_limit < memory_based_limit else 'Memory',
            'current_cpu_usage': cpu_percent,
            'current_memory_usage': memory_percent
        }
    
    def generate_report(self) -> str:
        """Generate a capacity report"""
        metrics = self.get_system_metrics()
        capacity = self.estimate_strategy_capacity(metrics)
        
        report = f"""
📊 TRADING SYSTEM CAPACITY REPORT
{'='*50}
🕒 Time: {metrics.get('timestamp', 'Unknown')}

🖥️  SYSTEM METRICS:
   CPU: {metrics.get('cpu_percent', 0):.1f}%
   Memory: {metrics.get('memory_percent', 0):.1f}%
   Available RAM: {metrics.get('memory_available_mb', 0):.0f}MB
   Load Average: {metrics.get('load_average', 0):.2f}

📈 CAPACITY ESTIMATION:
   Additional Strategies (CPU-limited): {capacity['cpu_based_limit']}
   Additional Strategies (Memory-limited): {capacity['memory_based_limit']}
   Safe Additional Strategies: {capacity['safe_additional_strategies']}
   Primary Bottleneck: {capacity['bottleneck']}

🐳 DOCKER CONTAINERS:"""
        
        docker_stats = metrics.get('docker_stats', {})
        if docker_stats:
            for name, stats in docker_stats.items():
                if isinstance(stats, dict):
                    report += f"\n   {name}: CPU {stats.get('cpu_percent', 'N/A')}, Memory {stats.get('memory_usage', 'N/A')}"
        
        alerts = metrics.get('alerts', [])
        if alerts:
            report += f"\n\n🚨 ALERTS:\n"
            for alert in alerts:
                report += f"   {alert}\n"
        else:
            report += f"\n\n✅ All systems within normal parameters"
        
        return report
    
    def monitor_continuous(self, interval: int = 60, duration: int = 3600):
        """Run continuous monitoring"""
        print(f"🔍 Starting continuous monitoring (interval: {interval}s, duration: {duration}s)")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                print("\n" + self.generate_report())
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")

def main():
    """Main function"""
    import sys
    
    monitor = CapacityMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        # Continuous monitoring mode
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 3600
        monitor.monitor_continuous(interval, duration)
    else:
        # Single report mode
        print(monitor.generate_report())

if __name__ == "__main__":
    main() 