"""
Critical Error Handler API Endpoints
Provides monitoring and management endpoints for the critical error handling system
"""

from fastapi import HTTPException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def add_error_handler_routes(app, production_engine):
    """Add error handler routes to the FastAPI app"""
    
    @app.get("/admin/error-handler/status")
    async def get_error_handler_status():
        """Get critical error handler status"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            status = error_handler.get_system_status()
            
            return {
                "success": True,
                "error_handler_status": status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting error handler status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

    @app.get("/admin/error-handler/recent-errors")
    async def get_recent_errors(hours: int = 24):
        """Get recent critical errors"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_errors = [
                {
                    'error_id': error.error_id,
                    'timestamp': error.timestamp.isoformat(),
                    'severity': error.severity.value,
                    'category': error.category.value,
                    'message': error.message,
                    'financial_impact': error.financial_impact,
                    'affected_users_count': len(error.affected_users),
                    'recovery_successful': error.recovery_successful
                }
                for error in error_handler.error_history
                if error.timestamp > cutoff_time
            ]
            
            return {
                "success": True,
                "recent_errors": recent_errors,
                "error_count": len(recent_errors),
                "hours_covered": hours,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get errors: {str(e)}")

    @app.post("/admin/error-handler/resolve/{error_id}")
    async def resolve_critical_error(error_id: str, resolution_notes: str = ""):
        """Resolve a critical error with input validation"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            # Validate error resolution data
            from src.core.input_validator import get_input_validator
            validator = get_input_validator()
            
            validated_data = validator.validate_error_resolution_data(error_id, resolution_notes)
            error_id = validated_data["error_id"]
            resolution_notes = validated_data["resolution_notes"]
            
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            success = await error_handler.resolve_critical_error(error_id, resolution_notes)
            
            return {
                "success": success,
                "error_id": error_id,
                "resolution_notes": resolution_notes,
                "trading_resumed": success and error_handler.get_system_status()['trading_allowed'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Error resolving critical error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to resolve error: {str(e)}")

    @app.post("/admin/error-handler/force-resume-trading")
    async def force_resume_trading():
        """Force resume trading (use with caution)"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            # Clear all paused states (WARNING: This is dangerous!)
            error_handler.trading_paused = False
            error_handler.trading_shutdown = False
            error_handler.paused_users.clear()
            error_handler.paused_strategies.clear()
            error_handler.paused_symbols.clear()
            error_handler.critical_errors_active.clear()
            
            logger.warning("🚨 FORCED TRADING RESUME - All error states cleared")
            
            return {
                "success": True,
                "warning": "Trading forcefully resumed - All error states cleared",
                "trading_allowed": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error forcing trading resume: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to force resume: {str(e)}")

    @app.get("/admin/error-handler/rules")
    async def get_error_rules():
        """Get current error handling rules"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            rules = [
                {
                    'pattern': rule.error_pattern,
                    'category': rule.category.value,
                    'severity': rule.severity.value,
                    'action': rule.action.value,
                    'max_occurrences': rule.max_occurrences,
                    'time_window_minutes': rule.time_window_minutes,
                    'requires_human_intervention': rule.requires_human_intervention
                }
                for rule in error_handler.error_rules
            ]
            
            return {
                "success": True,
                "error_rules": rules,
                "rule_count": len(rules),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting error rules: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")

    @app.get("/admin/error-handler/paused-entities")
    async def get_paused_entities():
        """Get currently paused users, strategies, and symbols"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            return {
                "success": True,
                "paused_entities": {
                    "users": list(error_handler.paused_users),
                    "strategies": list(error_handler.paused_strategies),
                    "symbols": list(error_handler.paused_symbols)
                },
                "trading_paused": error_handler.trading_paused,
                "trading_shutdown": error_handler.trading_shutdown,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting paused entities: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get paused entities: {str(e)}")

    @app.post("/admin/error-handler/unpause/{entity_type}/{entity_id}")
    async def unpause_entity(entity_type: str, entity_id: str):
        """Unpause a specific user, strategy, or symbol with input validation"""
        if not production_engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")
        
        try:
            # Validate path parameters
            from src.core.input_validator import get_input_validator
            validator = get_input_validator()
            
            validated_params = validator.validate_path_parameters(
                entity_type=entity_type, 
                entity_id=entity_id
            )
            entity_type = validated_params["entity_type"]
            entity_id = validated_params["entity_id"]
            
            # Validate entity type
            if entity_type not in ['user', 'strategy', 'symbol']:
                raise HTTPException(status_code=400, detail="Invalid entity type. Must be 'user', 'strategy', or 'symbol'")
        
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Parameter validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid request parameters")
        
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            removed = False
            
            if entity_type == 'user':
                if entity_id in error_handler.paused_users:
                    error_handler.paused_users.remove(entity_id)
                    removed = True
            elif entity_type == 'strategy':
                if entity_id in error_handler.paused_strategies:
                    error_handler.paused_strategies.remove(entity_id)
                    removed = True
            elif entity_type == 'symbol':
                if entity_id in error_handler.paused_symbols:
                    error_handler.paused_symbols.remove(entity_id)
                    removed = True
            
            return {
                "success": True,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "was_paused": removed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error unpausing entity: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to unpause entity: {str(e)}")

    logger.info("✅ Critical error handler API endpoints registered") 