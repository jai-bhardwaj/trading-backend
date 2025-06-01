"""
Risk Management Configuration

This module provides configurable risk management settings for different
environments, user types, and trading scenarios.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from app.core.risk_manager import RiskLimits
from app.core.order_executor import ExecutionConfig

class UserTier(Enum):
    """User tier levels with different risk limits"""
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    PROFESSIONAL = "PROFESSIONAL"
    INSTITUTIONAL = "INSTITUTIONAL"

class Environment(Enum):
    """Trading environments"""
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"

@dataclass
class RiskProfile:
    """Risk profile configuration"""
    name: str
    description: str
    risk_limits: RiskLimits
    execution_config: ExecutionConfig

class RiskConfigManager:
    """
    Risk configuration manager for different user tiers and environments
    """
    
    def __init__(self):
        self._profiles = self._initialize_risk_profiles()
    
    def _initialize_risk_profiles(self) -> Dict[str, RiskProfile]:
        """Initialize predefined risk profiles"""
        profiles = {}
        
        # Basic User Profile
        profiles["basic"] = RiskProfile(
            name="Basic User",
            description="Conservative risk limits for basic users",
            risk_limits=RiskLimits(
                # Position limits
                max_position_size_pct=0.05,        # 5% max position
                max_position_value=25000,          # $25k max position
                max_positions_per_symbol=1,        # 1 position per symbol
                max_total_positions=5,             # 5 total positions
                
                # Exposure limits
                max_sector_exposure_pct=0.2,       # 20% per sector
                max_asset_class_exposure_pct=0.3,  # 30% per asset class
                max_strategy_exposure_pct=0.15,    # 15% per strategy
                max_total_exposure_pct=0.5,        # 50% total exposure
                
                # Loss limits
                max_daily_loss_pct=0.01,           # 1% daily loss
                max_weekly_loss_pct=0.03,          # 3% weekly loss
                max_monthly_loss_pct=0.05,         # 5% monthly loss
                max_drawdown_pct=0.1,              # 10% max drawdown
                
                # Order limits
                max_order_value=10000,             # $10k max order
                max_orders_per_minute=3,           # 3 orders per minute
                max_orders_per_hour=50,            # 50 orders per hour
                
                # Volatility limits
                max_symbol_volatility=0.3,         # 30% daily volatility
                min_liquidity_volume=50000,        # 50k minimum volume
                
                # Time limits
                trading_start_time="09:15",
                trading_end_time="15:30",
                max_position_hold_days=7           # 7 days max hold
            ),
            execution_config=ExecutionConfig(
                max_retries=2,
                retry_delay_seconds=2.0,
                timeout_seconds=20.0,
                enable_risk_checks=True,
                enable_circuit_breaker=True,
                circuit_breaker_failure_threshold=3,
                circuit_breaker_timeout_seconds=60,
                enable_audit_logging=True,
                enable_real_time_monitoring=True
            )
        )
        
        # Premium User Profile
        profiles["premium"] = RiskProfile(
            name="Premium User",
            description="Moderate risk limits for premium users",
            risk_limits=RiskLimits(
                # Position limits
                max_position_size_pct=0.1,         # 10% max position
                max_position_value=100000,         # $100k max position
                max_positions_per_symbol=2,        # 2 positions per symbol
                max_total_positions=15,            # 15 total positions
                
                # Exposure limits
                max_sector_exposure_pct=0.3,       # 30% per sector
                max_asset_class_exposure_pct=0.5,  # 50% per asset class
                max_strategy_exposure_pct=0.2,     # 20% per strategy
                max_total_exposure_pct=0.8,        # 80% total exposure
                
                # Loss limits
                max_daily_loss_pct=0.02,           # 2% daily loss
                max_weekly_loss_pct=0.05,          # 5% weekly loss
                max_monthly_loss_pct=0.1,          # 10% monthly loss
                max_drawdown_pct=0.15,             # 15% max drawdown
                
                # Order limits
                max_order_value=50000,             # $50k max order
                max_orders_per_minute=10,          # 10 orders per minute
                max_orders_per_hour=200,           # 200 orders per hour
                
                # Volatility limits
                max_symbol_volatility=0.5,         # 50% daily volatility
                min_liquidity_volume=25000,        # 25k minimum volume
                
                # Time limits
                trading_start_time="09:15",
                trading_end_time="15:30",
                max_position_hold_days=30          # 30 days max hold
            ),
            execution_config=ExecutionConfig(
                max_retries=3,
                retry_delay_seconds=1.0,
                timeout_seconds=30.0,
                enable_risk_checks=True,
                enable_circuit_breaker=True,
                circuit_breaker_failure_threshold=5,
                circuit_breaker_timeout_seconds=60,
                enable_audit_logging=True,
                enable_real_time_monitoring=True
            )
        )
        
        # Professional User Profile
        profiles["professional"] = RiskProfile(
            name="Professional User",
            description="Higher risk limits for professional traders",
            risk_limits=RiskLimits(
                # Position limits
                max_position_size_pct=0.2,         # 20% max position
                max_position_value=500000,         # $500k max position
                max_positions_per_symbol=5,        # 5 positions per symbol
                max_total_positions=50,            # 50 total positions
                
                # Exposure limits
                max_sector_exposure_pct=0.5,       # 50% per sector
                max_asset_class_exposure_pct=0.8,  # 80% per asset class
                max_strategy_exposure_pct=0.3,     # 30% per strategy
                max_total_exposure_pct=1.0,        # 100% total exposure
                
                # Loss limits
                max_daily_loss_pct=0.05,           # 5% daily loss
                max_weekly_loss_pct=0.1,           # 10% weekly loss
                max_monthly_loss_pct=0.2,          # 20% monthly loss
                max_drawdown_pct=0.25,             # 25% max drawdown
                
                # Order limits
                max_order_value=200000,            # $200k max order
                max_orders_per_minute=30,          # 30 orders per minute
                max_orders_per_hour=1000,          # 1000 orders per hour
                
                # Volatility limits
                max_symbol_volatility=1.0,         # 100% daily volatility
                min_liquidity_volume=10000,        # 10k minimum volume
                
                # Time limits
                trading_start_time="09:00",        # Extended hours
                trading_end_time="16:00",
                max_position_hold_days=90          # 90 days max hold
            ),
            execution_config=ExecutionConfig(
                max_retries=5,
                retry_delay_seconds=0.5,
                timeout_seconds=45.0,
                enable_risk_checks=True,
                enable_circuit_breaker=True,
                circuit_breaker_failure_threshold=10,
                circuit_breaker_timeout_seconds=30,
                enable_audit_logging=True,
                enable_real_time_monitoring=True
            )
        )
        
        # Institutional Profile
        profiles["institutional"] = RiskProfile(
            name="Institutional",
            description="High limits for institutional clients",
            risk_limits=RiskLimits(
                # Position limits
                max_position_size_pct=0.5,         # 50% max position
                max_position_value=5000000,        # $5M max position
                max_positions_per_symbol=20,       # 20 positions per symbol
                max_total_positions=200,           # 200 total positions
                
                # Exposure limits
                max_sector_exposure_pct=1.0,       # 100% per sector
                max_asset_class_exposure_pct=1.0,  # 100% per asset class
                max_strategy_exposure_pct=0.5,     # 50% per strategy
                max_total_exposure_pct=2.0,        # 200% total exposure (leverage)
                
                # Loss limits
                max_daily_loss_pct=0.1,            # 10% daily loss
                max_weekly_loss_pct=0.2,           # 20% weekly loss
                max_monthly_loss_pct=0.3,          # 30% monthly loss
                max_drawdown_pct=0.4,              # 40% max drawdown
                
                # Order limits
                max_order_value=1000000,           # $1M max order
                max_orders_per_minute=100,         # 100 orders per minute
                max_orders_per_hour=5000,          # 5000 orders per hour
                
                # Volatility limits
                max_symbol_volatility=2.0,         # 200% daily volatility
                min_liquidity_volume=1000,         # 1k minimum volume
                
                # Time limits
                trading_start_time="08:00",        # Extended hours
                trading_end_time="18:00",
                max_position_hold_days=365         # 1 year max hold
            ),
            execution_config=ExecutionConfig(
                max_retries=10,
                retry_delay_seconds=0.1,
                timeout_seconds=60.0,
                enable_risk_checks=True,
                enable_circuit_breaker=True,
                circuit_breaker_failure_threshold=20,
                circuit_breaker_timeout_seconds=15,
                enable_audit_logging=True,
                enable_real_time_monitoring=True
            )
        )
        
        # Development/Testing Profile
        profiles["development"] = RiskProfile(
            name="Development",
            description="Relaxed limits for development and testing",
            risk_limits=RiskLimits(
                # Position limits
                max_position_size_pct=1.0,         # 100% max position
                max_position_value=1000000,        # $1M max position
                max_positions_per_symbol=10,       # 10 positions per symbol
                max_total_positions=100,           # 100 total positions
                
                # Exposure limits
                max_sector_exposure_pct=2.0,       # 200% per sector
                max_asset_class_exposure_pct=2.0,  # 200% per asset class
                max_strategy_exposure_pct=1.0,     # 100% per strategy
                max_total_exposure_pct=5.0,        # 500% total exposure
                
                # Loss limits
                max_daily_loss_pct=1.0,            # 100% daily loss
                max_weekly_loss_pct=1.0,           # 100% weekly loss
                max_monthly_loss_pct=1.0,          # 100% monthly loss
                max_drawdown_pct=1.0,              # 100% max drawdown
                
                # Order limits
                max_order_value=10000000,          # $10M max order
                max_orders_per_minute=1000,        # 1000 orders per minute
                max_orders_per_hour=50000,         # 50k orders per hour
                
                # Volatility limits
                max_symbol_volatility=10.0,        # 1000% daily volatility
                min_liquidity_volume=1,            # 1 minimum volume
                
                # Time limits
                trading_start_time="00:00",        # 24/7 trading
                trading_end_time="23:59",
                max_position_hold_days=3650        # 10 years max hold
            ),
            execution_config=ExecutionConfig(
                max_retries=1,
                retry_delay_seconds=0.1,
                timeout_seconds=5.0,
                enable_risk_checks=False,          # Disable for testing
                enable_circuit_breaker=False,      # Disable for testing
                circuit_breaker_failure_threshold=1000,
                circuit_breaker_timeout_seconds=1,
                enable_audit_logging=True,
                enable_real_time_monitoring=False
            )
        )
        
        return profiles
    
    def get_profile(self, profile_name: str) -> Optional[RiskProfile]:
        """Get risk profile by name"""
        return self._profiles.get(profile_name.lower())
    
    def get_profile_for_user_tier(self, user_tier: UserTier) -> RiskProfile:
        """Get risk profile based on user tier"""
        tier_mapping = {
            UserTier.BASIC: "basic",
            UserTier.PREMIUM: "premium",
            UserTier.PROFESSIONAL: "professional",
            UserTier.INSTITUTIONAL: "institutional"
        }
        
        profile_name = tier_mapping.get(user_tier, "basic")
        return self._profiles[profile_name]
    
    def get_profile_for_environment(self, environment: Environment) -> RiskProfile:
        """Get risk profile based on environment"""
        if environment in [Environment.DEVELOPMENT, Environment.TESTING]:
            return self._profiles["development"]
        elif environment == Environment.STAGING:
            return self._profiles["basic"]  # Conservative for staging
        else:  # Production
            return self._profiles["premium"]  # Default production profile
    
    def list_profiles(self) -> Dict[str, str]:
        """List all available profiles"""
        return {
            name: profile.description 
            for name, profile in self._profiles.items()
        }
    
    def create_custom_profile(self, name: str, description: str, 
                            risk_limits: RiskLimits, 
                            execution_config: ExecutionConfig) -> None:
        """Create a custom risk profile"""
        self._profiles[name.lower()] = RiskProfile(
            name=name,
            description=description,
            risk_limits=risk_limits,
            execution_config=execution_config
        )
    
    def update_profile_limits(self, profile_name: str, 
                            limit_updates: Dict[str, Any]) -> bool:
        """Update specific limits in a profile"""
        profile = self._profiles.get(profile_name.lower())
        if not profile:
            return False
        
        # Update risk limits
        for key, value in limit_updates.items():
            if hasattr(profile.risk_limits, key):
                setattr(profile.risk_limits, key, value)
        
        return True
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        import os
        
        env = os.getenv("TRADING_ENVIRONMENT", "DEVELOPMENT").upper()
        
        config = {
            "DEVELOPMENT": {
                "enable_paper_trading": True,
                "enable_risk_checks": False,
                "log_level": "DEBUG",
                "enable_monitoring": False
            },
            "TESTING": {
                "enable_paper_trading": True,
                "enable_risk_checks": True,
                "log_level": "INFO",
                "enable_monitoring": False
            },
            "STAGING": {
                "enable_paper_trading": True,
                "enable_risk_checks": True,
                "log_level": "INFO",
                "enable_monitoring": True
            },
            "PRODUCTION": {
                "enable_paper_trading": False,
                "enable_risk_checks": True,
                "log_level": "WARNING",
                "enable_monitoring": True
            }
        }
        
        return config.get(env, config["DEVELOPMENT"])

# Global risk config manager
risk_config_manager = RiskConfigManager()

# Convenience functions
def get_risk_profile(profile_name: str) -> Optional[RiskProfile]:
    """Get risk profile by name"""
    return risk_config_manager.get_profile(profile_name)

def get_user_tier_profile(user_tier: UserTier) -> RiskProfile:
    """Get risk profile for user tier"""
    return risk_config_manager.get_profile_for_user_tier(user_tier)

def get_environment_profile(environment: Environment) -> RiskProfile:
    """Get risk profile for environment"""
    return risk_config_manager.get_profile_for_environment(environment) 