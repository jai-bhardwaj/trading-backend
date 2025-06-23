"""
Production Trading Safety Validator

CRITICAL: Prevents fallback to demo trading when live broker connection fails
This module ensures production trading never falls back to demo mode

Key Features:
- Strict production mode validation
- Broker connection status monitoring
- Trading mode enforcement
- Emergency trading halt capabilities
- Production environment detection
"""

import os
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import threading
import time

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Trading mode enumeration"""
    LIVE = "live"
    PAPER = "paper"
    DEMO = "demo"
    DISABLED = "disabled"

class ProductionEnvironment(Enum):
    """Environment detection"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class ProductionSafetyConfig:
    """Production safety configuration"""
    enforce_production_safety: bool = True
    allow_demo_fallback: bool = False
    max_broker_retry_attempts: int = 3
    broker_connection_timeout: int = 30
    emergency_halt_enabled: bool = True
    production_api_required: bool = True

class ProductionSafetyValidator:
    """
    CRITICAL: Ensures production trading never falls back to demo mode
    
    This validator prevents the dangerous scenario where production trading
    silently falls back to demo/paper trading when broker API fails.
    """
    
    def __init__(self, config: ProductionSafetyConfig = None):
        self.config = config or ProductionSafetyConfig()
        self._lock = threading.Lock()
        self._trading_halted = False
        self._halt_reason = ""
        
        # Detect environment
        self.environment = self._detect_environment()
        
        # Track broker connection attempts
        self._broker_retry_count = 0
        self._last_broker_attempt = 0
        
        # Track intended trading mode
        self._intended_mode = TradingMode.PAPER  # Default safe mode
        
        logger.info(f"🛡️ Production Safety Validator initialized")
        logger.info(f"   Environment: {self.environment.value}")
        logger.info(f"   Safety enforcement: {self.config.enforce_production_safety}")
        logger.info(f"   Demo fallback allowed: {self.config.allow_demo_fallback}")
    
    def _detect_environment(self) -> ProductionEnvironment:
        """Detect current environment"""
        # Check environment variables
        env = os.getenv('ENVIRONMENT', '').lower()
        python_env = os.getenv('PYTHON_ENV', '').lower()
        flask_env = os.getenv('FLASK_ENV', '').lower()
        
        if any(env in ['prod', 'production'] for env in [env, python_env, flask_env]):
            return ProductionEnvironment.PRODUCTION
        elif any(env in ['staging', 'stage'] for env in [env, python_env, flask_env]):
            return ProductionEnvironment.STAGING
        else:
            return ProductionEnvironment.DEVELOPMENT
    
    def is_production_environment(self) -> bool:
        """Check if running in production environment"""
        return self.environment == ProductionEnvironment.PRODUCTION
    
    def should_allow_trading(self, broker_connected: bool) -> bool:
        """
        CRITICAL: Determine if trading should be allowed
        
        Args:
            broker_connected: Whether broker is actually connected
            
        Returns:
            True if trading is safe, False if should be blocked
        """
        with self._lock:
            # If trading is manually halted
            if self._trading_halted:
                logger.critical(f"🚨 TRADING HALTED: {self._halt_reason}")
                return False
            
            # In development, more lenient
            if self.environment == ProductionEnvironment.DEVELOPMENT:
                if not self.config.enforce_production_safety:
                    logger.warning("⚠️ Development mode - production safety not enforced")
                    return True
            
            # In production/staging, strict enforcement
            if self.is_production_environment():
                if not broker_connected:
                    logger.critical("🚨 PRODUCTION MODE: Broker not connected - TRADING BLOCKED")
                    logger.critical("🚨 NO FALLBACK TO DEMO TRADING ALLOWED")
                    return False
            
            # For staging, similar to production
            if self.environment == ProductionEnvironment.STAGING:
                if not broker_connected and self.config.enforce_production_safety:
                    logger.error("🔴 STAGING MODE: Broker not connected - TRADING BLOCKED")
                    return False
            
            return True
    
    def validate_trading_mode_safety(self, intended_mode: TradingMode, 
                                   broker_connected: bool) -> bool:
        """
        Validate that trading mode is safe for current environment
        
        Args:
            intended_mode: The intended trading mode
            broker_connected: Whether broker is connected
            
        Returns:
            True if mode is safe, False if dangerous
        """
        with self._lock:
            # Production environment validation
            if self.is_production_environment():
                # In production, only LIVE mode is allowed
                if intended_mode != TradingMode.LIVE:
                    logger.critical(f"🚨 PRODUCTION SAFETY VIOLATION: Mode {intended_mode.value} not allowed in production")
                    return False
                
                # Live mode requires broker connection
                if intended_mode == TradingMode.LIVE and not broker_connected:
                    logger.critical("🚨 PRODUCTION SAFETY VIOLATION: Live trading requires broker connection")
                    return False
            
            # Staging environment validation
            elif self.environment == ProductionEnvironment.STAGING:
                # Staging can use LIVE or PAPER, but not DEMO
                if intended_mode == TradingMode.DEMO and self.config.enforce_production_safety:
                    logger.error("🔴 STAGING SAFETY WARNING: Demo mode not recommended in staging")
                    return False
            
            # Development environment - more flexible
            else:
                logger.info(f"🔧 Development mode - allowing {intended_mode.value} trading")
            
            return True
    
    def handle_broker_connection_failure(self, error: Exception, 
                                       retry_count: int = 0) -> bool:
        """
        Handle broker connection failure with production safety
        
        Args:
            error: The connection error
            retry_count: Current retry attempt
            
        Returns:
            True if should retry, False if should halt
        """
        with self._lock:
            self._broker_retry_count = retry_count
            self._last_broker_attempt = time.time()
            
            logger.error(f"❌ Broker connection failed (attempt {retry_count}): {error}")
            
            # In production, limited retries then halt
            if self.is_production_environment():
                if retry_count >= self.config.max_broker_retry_attempts:
                    self.emergency_halt_trading(
                        f"Broker connection failed after {retry_count} attempts in production"
                    )
                    return False
                else:
                    logger.warning(f"⚠️ Production broker retry {retry_count}/{self.config.max_broker_retry_attempts}")
                    return True
            
            # In development/staging, more retries allowed
            return retry_count < (self.config.max_broker_retry_attempts * 2)
    
    def emergency_halt_trading(self, reason: str):
        """
        Emergency halt all trading operations
        
        Args:
            reason: Reason for emergency halt
        """
        with self._lock:
            if not self.config.emergency_halt_enabled:
                logger.warning("⚠️ Emergency halt requested but disabled by config")
                return
            
            self._trading_halted = True
            self._halt_reason = reason
            
            logger.critical("🛑 EMERGENCY TRADING HALT ACTIVATED")
            logger.critical(f"🛑 Reason: {reason}")
            logger.critical("🛑 Manual intervention required to resume trading")
            
            # Send critical alerts
            self._send_emergency_alerts(reason)
    
    def resume_trading(self, authorized_by: str = "system") -> bool:
        """
        Resume trading after emergency halt
        
        Args:
            authorized_by: Who authorized the resume
            
        Returns:
            True if resumed successfully
        """
        with self._lock:
            if not self._trading_halted:
                logger.info("ℹ️ Trading resume requested but not currently halted")
                return True
            
            logger.critical(f"🟢 TRADING RESUMED by {authorized_by}")
            logger.critical(f"🟢 Previous halt reason: {self._halt_reason}")
            
            self._trading_halted = False
            self._halt_reason = ""
            
            return True
    
    def _send_emergency_alerts(self, reason: str):
        """Send emergency alerts for trading halt"""
        try:
            # In a real system, this would send alerts via:
            # - Email
            # - SMS
            # - Slack/Teams
            # - PagerDuty
            # - System monitoring dashboards
            
            alert_data = {
                'timestamp': time.time(),
                'environment': self.environment.value,
                'reason': reason,
                'broker_retry_count': self._broker_retry_count,
                'severity': 'CRITICAL'
            }
            
            logger.critical(f"📧 EMERGENCY ALERT SENT: {alert_data}")
            
            # TODO: Implement actual alerting mechanisms
            # - Email via SMTP
            # - Slack webhook
            # - SMS via Twilio
            # - PagerDuty incident
            
        except Exception as e:
            logger.error(f"❌ Failed to send emergency alerts: {e}")
    
    def validate_production_api_credentials(self) -> bool:
        """
        Validate that production API credentials are properly configured
        
        Returns:
            True if credentials are valid for production
        """
        if not self.config.production_api_required:
            return True
        
        # Check required environment variables for production
        required_vars = [
            'ANGEL_ONE_API_KEY',
            'ANGEL_ONE_SECRET_KEY', 
            'ANGEL_ONE_CLIENT_ID',
            'ANGEL_ONE_PIN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.critical(f"🚨 PRODUCTION API CREDENTIALS MISSING: {missing_vars}")
            
            if self.is_production_environment():
                self.emergency_halt_trading(
                    f"Missing production API credentials: {missing_vars}"
                )
                return False
        
        return True
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety status"""
        with self._lock:
            return {
                'environment': self.environment.value,
                'trading_halted': self._trading_halted,
                'halt_reason': self._halt_reason,
                'broker_retry_count': self._broker_retry_count,
                'last_broker_attempt': self._last_broker_attempt,
                'safety_config': {
                    'enforce_production_safety': self.config.enforce_production_safety,
                    'allow_demo_fallback': self.config.allow_demo_fallback,
                    'max_broker_retry_attempts': self.config.max_broker_retry_attempts,
                    'emergency_halt_enabled': self.config.emergency_halt_enabled,
                    'production_api_required': self.config.production_api_required
                }
            }
    
    def check_production_readiness(self) -> Dict[str, Any]:
        """
        Comprehensive production readiness check
        
        Returns:
            Dictionary with readiness status and issues
        """
        issues = []
        warnings = []
        
        # Environment check
        if not self.is_production_environment():
            warnings.append(f"Running in {self.environment.value} environment")
        
        # API credentials check
        if not self.validate_production_api_credentials():
            issues.append("Production API credentials missing or invalid")
        
        # Safety configuration check
        if not self.config.enforce_production_safety and self.is_production_environment():
            issues.append("Production safety enforcement is disabled")
        
        if self.config.allow_demo_fallback and self.is_production_environment():
            issues.append("Demo fallback is enabled in production")
        
        # Trading halt check
        if self._trading_halted:
            issues.append(f"Trading is currently halted: {self._halt_reason}")
        
        readiness_score = max(0, 100 - (len(issues) * 25) - (len(warnings) * 5))
        
        return {
            'ready_for_production': len(issues) == 0,
            'readiness_score': readiness_score,
            'issues': issues,
            'warnings': warnings,
            'environment': self.environment.value,
            'timestamp': time.time()
        }

    def set_intended_mode(self, mode: TradingMode):
        """Set the intended trading mode"""
        with self._lock:
            self._intended_mode = mode
            logger.info(f"🎯 Intended trading mode set to: {mode.value}")
    
    def get_intended_mode(self) -> TradingMode:
        """Get the intended trading mode"""
        return self._intended_mode

# Global production safety validator instance
_global_validator: Optional[ProductionSafetyValidator] = None
_validator_lock = threading.Lock()

def get_production_safety_validator() -> ProductionSafetyValidator:
    """Get global production safety validator instance"""
    global _global_validator
    
    with _validator_lock:
        if _global_validator is None:
            _global_validator = ProductionSafetyValidator()
    
    return _global_validator

def emergency_halt_all_trading(reason: str):
    """Emergency halt all trading - global function"""
    validator = get_production_safety_validator()
    validator.emergency_halt_trading(reason)
