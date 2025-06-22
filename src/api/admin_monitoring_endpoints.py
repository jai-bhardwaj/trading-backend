"""
Admin Monitoring and Resource Management API Endpoints
"""

from fastapi import HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def add_admin_monitoring_routes(app, production_engine):
    """Add comprehensive admin monitoring routes"""
    
    @app.get("/admin/system/health")
    async def get_system_health():
        """Get comprehensive system health status"""
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            
            dashboard_data = monitor.get_dashboard_data()
            return {
                "success": True,
                "data": dashboard_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ System health endpoint error: {e}")
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
    
    @app.get("/admin/system/dashboard")
    async def get_monitoring_dashboard():
        """Get full monitoring dashboard data"""
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            
            return monitor.get_dashboard_data()
            
        except Exception as e:
            logger.error(f"❌ Dashboard endpoint error: {e}")
            raise HTTPException(status_code=500, detail=f"Dashboard failed: {str(e)}")
    
    @app.post("/admin/monitoring/start")
    async def start_system_monitoring(interval_seconds: int = 60):
        """Start system monitoring"""
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            
            await monitor.start_monitoring(interval_seconds)
            
            return {
                "success": True,
                "message": f"System monitoring started with {interval_seconds}s interval",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Start monitoring error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")
    
    @app.post("/admin/monitoring/stop")
    async def stop_system_monitoring():
        """Stop system monitoring"""
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            
            monitor.stop_monitoring()
            
            return {
                "success": True,
                "message": "System monitoring stopped",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Stop monitoring error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")
    
    @app.get("/admin/resources/status")
    async def get_resource_status():
        """Get current resource usage status"""
        try:
            from src.core.resource_manager import get_resource_manager
            resource_manager = get_resource_manager()
            
            status = resource_manager.get_resource_status()
            return {
                "success": True,
                "data": status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Resource status error: {e}")
            raise HTTPException(status_code=500, detail=f"Resource status failed: {str(e)}")
    
    @app.post("/admin/resources/cleanup")
    async def force_resource_cleanup():
        """Force immediate resource cleanup"""
        try:
            from src.core.resource_manager import get_resource_manager
            resource_manager = get_resource_manager()
            
            cleanup_result = await resource_manager.force_cleanup()
            
            return {
                "success": True,
                "cleanup_result": cleanup_result,
                "message": "Resource cleanup completed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Resource cleanup error: {e}")
            raise HTTPException(status_code=500, detail=f"Resource cleanup failed: {str(e)}")
    
    @app.post("/admin/resources/monitoring/start")
    async def start_resource_monitoring():
        """Start resource monitoring"""
        try:
            from src.core.resource_manager import get_resource_manager
            resource_manager = get_resource_manager()
            
            await resource_manager.start_monitoring()
            
            return {
                "success": True,
                "message": "Resource monitoring started",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Start resource monitoring error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start resource monitoring: {str(e)}")
    
    @app.get("/admin/config/validation")
    async def validate_system_configuration():
        """Validate complete system configuration"""
        try:
            from src.core.config_validator import get_config_validator
            validator = get_config_validator()
            
            validation_result = validator.perform_full_validation()
            
            return {
                "success": True,
                "validation_result": validation_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Config validation error: {e}")
            raise HTTPException(status_code=500, detail=f"Config validation failed: {str(e)}")
    
    @app.get("/admin/system/components")
    async def get_component_status():
        """Get status of individual system components"""
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            
            components = [
                "authentication",
                "memory_manager",
                "order_system", 
                "broker_connection",
                "database"
            ]
            
            component_status = {}
            for component in components:
                component_status[component] = monitor.get_component_health(component).value
            
            return {
                "success": True,
                "components": component_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Component status error: {e}")
            raise HTTPException(status_code=500, detail=f"Component status failed: {str(e)}")
    
    @app.get("/admin/system/uptime")
    async def get_system_uptime():
        """Get system uptime and basic stats"""
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            
            status = monitor.generate_system_status()
            
            return {
                "success": True,
                "uptime_seconds": status.uptime_seconds,
                "uptime_hours": round(status.uptime_seconds / 3600, 2),
                "uptime_days": round(status.uptime_seconds / 86400, 2),
                "overall_health": status.overall_health.value,
                "total_alerts": len(status.alerts),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Uptime endpoint error: {e}")
            raise HTTPException(status_code=500, detail=f"Uptime check failed: {str(e)}")

def add_system_info_routes(app):
    """Add system information routes"""
    
    @app.get("/admin/system/info")
    async def get_system_info():
        """Get comprehensive system information"""
        try:
            import psutil
            import platform
            
            # System information
            system_info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "total_memory_gb": round(psutil.virtual_memory().total / 1024**3, 2),
                "available_memory_gb": round(psutil.virtual_memory().available / 1024**3, 2),
                "disk_usage": {
                    "total_gb": round(psutil.disk_usage('/').total / 1024**3, 2),
                    "free_gb": round(psutil.disk_usage('/').free / 1024**3, 2),
                    "used_percent": psutil.disk_usage('/').percent
                }
            }
            
            return {
                "success": True,
                "system_info": system_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ System info error: {e}")
            raise HTTPException(status_code=500, detail=f"System info failed: {str(e)}")
