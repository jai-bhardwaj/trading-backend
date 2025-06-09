"""
Risk Management System for Algorithmic Trading

This module provides comprehensive risk management capabilities including
position limits, drawdown controls, exposure limits, and real-time monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.base import Order, Position, Balance, Trade, User, Strategy as StrategyModel
from app.strategies.signals import StrategySignal
from app.models.base import AssetClass
from app.utils.timezone_utils import ist_utcnow as datetime_now  # IST replacement for datetime.utcnow

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskCheckResult(Enum):
    """Risk check results"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"

@dataclass
class RiskLimits:
    """Risk limits configuration"""
    # Position limits
    max_position_size_pct: float = 0.1  # 10% of portfolio
    max_position_value: float = 100000  # Maximum position value
    max_positions_per_symbol: int = 1   # Max positions per symbol
    max_total_positions: int = 10       # Max total positions
    
    # Exposure limits
    max_sector_exposure_pct: float = 0.3  # 30% per sector
    max_asset_class_exposure_pct: float = 0.5  # 50% per asset class
    max_strategy_exposure_pct: float = 0.2  # 20% per strategy
    max_total_exposure_pct: float = 0.8  # 80% total exposure
    
    # Loss limits
    max_daily_loss_pct: float = 0.02    # 2% daily loss
    max_weekly_loss_pct: float = 0.05   # 5% weekly loss
    max_monthly_loss_pct: float = 0.1   # 10% monthly loss
    max_drawdown_pct: float = 0.15      # 15% max drawdown
    
    # Order limits
    max_order_value: float = 50000      # Maximum single order value
    max_orders_per_minute: int = 10     # Rate limiting
    max_orders_per_hour: int = 100      # Hourly limit
    
    # Volatility limits
    max_symbol_volatility: float = 0.5  # 50% daily volatility
    min_liquidity_volume: float = 10000 # Minimum daily volume
    
    # Time-based limits
    trading_start_time: str = "09:15"   # Market open
    trading_end_time: str = "15:30"     # Market close
    max_position_hold_days: int = 30    # Max holding period

@dataclass
class RiskCheckContext:
    """Context for risk checks"""
    user_id: str
    strategy_id: Optional[str] = None
    signal: Optional[StrategySignal] = None
    order_value: float = 0.0
    current_balance: float = 0.0
    current_positions: List[Dict] = field(default_factory=list)
    recent_orders: List[Dict] = field(default_factory=list)
    market_conditions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RiskViolation:
    """Risk violation details"""
    rule_name: str
    severity: RiskLevel
    message: str
    current_value: float
    limit_value: float
    suggested_action: str
    timestamp: datetime = field(default_factory=datetime_now)

class RiskManager:
    """
    Comprehensive risk management system
    
    This class provides multiple layers of risk checks including:
    - Position size and exposure limits
    - Loss and drawdown controls
    - Order rate limiting
    - Market condition checks
    - Real-time monitoring
    """
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.violation_history: List[RiskViolation] = []
        self.order_timestamps: Dict[str, List[datetime]] = {}  # Rate limiting
        
    def check_order_risk(self, db: Session, context: RiskCheckContext) -> Tuple[RiskCheckResult, List[RiskViolation], Dict[str, Any]]:
        """
        Comprehensive risk check for order placement
        
        Args:
            db: Database session
            context: Risk check context
            
        Returns:
            Tuple of (result, violations, modifications)
        """
        violations = []
        modifications = {}
        
        try:
            # 1. Basic validation checks
            violations.extend(self._check_basic_validation(context))
            
            # 2. Position size and exposure checks
            violations.extend(self._check_position_limits(db, context))
            
            # 3. Loss and drawdown checks
            violations.extend(self._check_loss_limits(db, context))
            
            # 4. Order rate limiting
            violations.extend(self._check_order_rate_limits(context))
            
            # 5. Market condition checks
            violations.extend(self._check_market_conditions(context))
            
            # 6. Time-based checks
            violations.extend(self._check_trading_hours())
            
            # 7. Liquidity and volatility checks
            violations.extend(self._check_liquidity_volatility(db, context))
            
            # Determine overall result
            result = self._determine_risk_result(violations, modifications)
            
            # Log violations
            for violation in violations:
                self.violation_history.append(violation)
                logger.warning(f"Risk violation: {violation.rule_name} - {violation.message}")
            
            return result, violations, modifications
            
        except Exception as e:
            logger.error(f"Error in risk check: {e}")
            violation = RiskViolation(
                rule_name="SYSTEM_ERROR",
                severity=RiskLevel.CRITICAL,
                message=f"Risk check system error: {str(e)}",
                current_value=0,
                limit_value=0,
                suggested_action="REJECT_ORDER"
            )
            return RiskCheckResult.REJECTED, [violation], {}
    
    def _check_basic_validation(self, context: RiskCheckContext) -> List[RiskViolation]:
        """Basic validation checks"""
        violations = []
        
        # Check order value
        if context.order_value <= 0:
            violations.append(RiskViolation(
                rule_name="INVALID_ORDER_VALUE",
                severity=RiskLevel.HIGH,
                message="Order value must be positive",
                current_value=context.order_value,
                limit_value=0,
                suggested_action="REJECT_ORDER"
            ))
        
        # Check maximum order value
        if context.order_value > self.risk_limits.max_order_value:
            violations.append(RiskViolation(
                rule_name="MAX_ORDER_VALUE_EXCEEDED",
                severity=RiskLevel.HIGH,
                message=f"Order value {context.order_value} exceeds maximum {self.risk_limits.max_order_value}",
                current_value=context.order_value,
                limit_value=self.risk_limits.max_order_value,
                suggested_action="REDUCE_ORDER_SIZE"
            ))
        
        # Check sufficient balance
        if context.order_value > context.current_balance:
            violations.append(RiskViolation(
                rule_name="INSUFFICIENT_BALANCE",
                severity=RiskLevel.CRITICAL,
                message=f"Insufficient balance. Required: {context.order_value}, Available: {context.current_balance}",
                current_value=context.current_balance,
                limit_value=context.order_value,
                suggested_action="REJECT_ORDER"
            ))
        
        return violations
    
    def _check_position_limits(self, db: Session, context: RiskCheckContext) -> List[RiskViolation]:
        """Check position size and exposure limits"""
        violations = []
        
        # Check position size as percentage of portfolio
        position_pct = context.order_value / context.current_balance if context.current_balance > 0 else 0
        if position_pct > self.risk_limits.max_position_size_pct:
            violations.append(RiskViolation(
                rule_name="MAX_POSITION_SIZE_EXCEEDED",
                severity=RiskLevel.HIGH,
                message=f"Position size {position_pct:.2%} exceeds maximum {self.risk_limits.max_position_size_pct:.2%}",
                current_value=position_pct,
                limit_value=self.risk_limits.max_position_size_pct,
                suggested_action="REDUCE_POSITION_SIZE"
            ))
        
        # Check total number of positions
        total_positions = len(context.current_positions)
        if total_positions >= self.risk_limits.max_total_positions:
            violations.append(RiskViolation(
                rule_name="MAX_TOTAL_POSITIONS_EXCEEDED",
                severity=RiskLevel.MEDIUM,
                message=f"Total positions {total_positions} exceeds maximum {self.risk_limits.max_total_positions}",
                current_value=total_positions,
                limit_value=self.risk_limits.max_total_positions,
                suggested_action="CLOSE_EXISTING_POSITIONS"
            ))
        
        # Check symbol-specific position limits
        if context.signal:
            symbol_positions = [p for p in context.current_positions if p.get('symbol') == context.signal.symbol]
            if len(symbol_positions) >= self.risk_limits.max_positions_per_symbol:
                violations.append(RiskViolation(
                    rule_name="MAX_SYMBOL_POSITIONS_EXCEEDED",
                    severity=RiskLevel.MEDIUM,
                    message=f"Positions for {context.signal.symbol} exceed maximum {self.risk_limits.max_positions_per_symbol}",
                    current_value=len(symbol_positions),
                    limit_value=self.risk_limits.max_positions_per_symbol,
                    suggested_action="AVOID_ADDITIONAL_POSITIONS"
                ))
        
        # Check total exposure
        total_exposure = sum(abs(p.get('quantity', 0) * p.get('average_price', 0)) for p in context.current_positions)
        total_exposure_pct = total_exposure / context.current_balance if context.current_balance > 0 else 0
        if total_exposure_pct > self.risk_limits.max_total_exposure_pct:
            violations.append(RiskViolation(
                rule_name="MAX_TOTAL_EXPOSURE_EXCEEDED",
                severity=RiskLevel.HIGH,
                message=f"Total exposure {total_exposure_pct:.2%} exceeds maximum {self.risk_limits.max_total_exposure_pct:.2%}",
                current_value=total_exposure_pct,
                limit_value=self.risk_limits.max_total_exposure_pct,
                suggested_action="REDUCE_EXPOSURE"
            ))
        
        return violations
    
    def _check_loss_limits(self, db: Session, context: RiskCheckContext) -> List[RiskViolation]:
        """Check loss and drawdown limits"""
        violations = []
        
        try:
            # Calculate daily P&L
            today = datetime_now().date()
            daily_trades = db.query(Trade).filter(
                and_(
                    Trade.user_id == context.user_id,
                    func.date(Trade.created_at) == today
                )
            ).all()
            
            daily_pnl = sum(trade.pnl for trade in daily_trades if trade.pnl)
            daily_loss_pct = abs(daily_pnl) / context.current_balance if context.current_balance > 0 and daily_pnl < 0 else 0
            
            if daily_loss_pct > self.risk_limits.max_daily_loss_pct:
                violations.append(RiskViolation(
                    rule_name="MAX_DAILY_LOSS_EXCEEDED",
                    severity=RiskLevel.CRITICAL,
                    message=f"Daily loss {daily_loss_pct:.2%} exceeds maximum {self.risk_limits.max_daily_loss_pct:.2%}",
                    current_value=daily_loss_pct,
                    limit_value=self.risk_limits.max_daily_loss_pct,
                    suggested_action="STOP_TRADING_TODAY"
                ))
            
            # Calculate weekly P&L
            week_start = today - timedelta(days=today.weekday())
            weekly_trades = db.query(Trade).filter(
                and_(
                    Trade.user_id == context.user_id,
                    func.date(Trade.created_at) >= week_start
                )
            ).all()
            
            weekly_pnl = sum(trade.pnl for trade in weekly_trades if trade.pnl)
            weekly_loss_pct = abs(weekly_pnl) / context.current_balance if context.current_balance > 0 and weekly_pnl < 0 else 0
            
            if weekly_loss_pct > self.risk_limits.max_weekly_loss_pct:
                violations.append(RiskViolation(
                    rule_name="MAX_WEEKLY_LOSS_EXCEEDED",
                    severity=RiskLevel.HIGH,
                    message=f"Weekly loss {weekly_loss_pct:.2%} exceeds maximum {self.risk_limits.max_weekly_loss_pct:.2%}",
                    current_value=weekly_loss_pct,
                    limit_value=self.risk_limits.max_weekly_loss_pct,
                    suggested_action="REDUCE_POSITION_SIZES"
                ))
            
        except Exception as e:
            logger.error(f"Error checking loss limits: {e}")
        
        return violations
    
    def _check_order_rate_limits(self, context: RiskCheckContext) -> List[RiskViolation]:
        """Check order rate limiting"""
        violations = []
        current_time = datetime_now()
        
        # Initialize user order history if not exists
        if context.user_id not in self.order_timestamps:
            self.order_timestamps[context.user_id] = []
        
        user_orders = self.order_timestamps[context.user_id]
        
        # Clean old timestamps
        one_hour_ago = current_time - timedelta(hours=1)
        one_minute_ago = current_time - timedelta(minutes=1)
        
        user_orders[:] = [ts for ts in user_orders if ts > one_hour_ago]
        
        # Check minute rate limit
        recent_orders = [ts for ts in user_orders if ts > one_minute_ago]
        if len(recent_orders) >= self.risk_limits.max_orders_per_minute:
            violations.append(RiskViolation(
                rule_name="MAX_ORDERS_PER_MINUTE_EXCEEDED",
                severity=RiskLevel.MEDIUM,
                message=f"Orders per minute {len(recent_orders)} exceeds maximum {self.risk_limits.max_orders_per_minute}",
                current_value=len(recent_orders),
                limit_value=self.risk_limits.max_orders_per_minute,
                suggested_action="WAIT_BEFORE_NEXT_ORDER"
            ))
        
        # Check hourly rate limit
        if len(user_orders) >= self.risk_limits.max_orders_per_hour:
            violations.append(RiskViolation(
                rule_name="MAX_ORDERS_PER_HOUR_EXCEEDED",
                severity=RiskLevel.HIGH,
                message=f"Orders per hour {len(user_orders)} exceeds maximum {self.risk_limits.max_orders_per_hour}",
                current_value=len(user_orders),
                limit_value=self.risk_limits.max_orders_per_hour,
                suggested_action="STOP_TRADING_FOR_HOUR"
            ))
        
        # Add current timestamp if no violations
        if not violations:
            user_orders.append(current_time)
        
        return violations
    
    def _check_market_conditions(self, context: RiskCheckContext) -> List[RiskViolation]:
        """Check market conditions"""
        violations = []
        
        market_conditions = context.market_conditions
        
        # Check market volatility
        if 'volatility' in market_conditions:
            volatility = market_conditions['volatility']
            if volatility > self.risk_limits.max_symbol_volatility:
                violations.append(RiskViolation(
                    rule_name="HIGH_MARKET_VOLATILITY",
                    severity=RiskLevel.MEDIUM,
                    message=f"Market volatility {volatility:.2%} exceeds maximum {self.risk_limits.max_symbol_volatility:.2%}",
                    current_value=volatility,
                    limit_value=self.risk_limits.max_symbol_volatility,
                    suggested_action="REDUCE_POSITION_SIZE"
                ))
        
        # Check liquidity
        if 'volume' in market_conditions:
            volume = market_conditions['volume']
            if volume < self.risk_limits.min_liquidity_volume:
                violations.append(RiskViolation(
                    rule_name="LOW_LIQUIDITY",
                    severity=RiskLevel.MEDIUM,
                    message=f"Volume {volume} below minimum {self.risk_limits.min_liquidity_volume}",
                    current_value=volume,
                    limit_value=self.risk_limits.min_liquidity_volume,
                    suggested_action="AVOID_LARGE_ORDERS"
                ))
        
        return violations
    
    def _check_trading_hours(self) -> List[RiskViolation]:
        """Check if trading is allowed at current time"""
        violations = []
        
        current_time = datetime_now().time()
        start_time = datetime.strptime(self.risk_limits.trading_start_time, "%H:%M").time()
        end_time = datetime.strptime(self.risk_limits.trading_end_time, "%H:%M").time()
        
        if not (start_time <= current_time <= end_time):
            violations.append(RiskViolation(
                rule_name="OUTSIDE_TRADING_HOURS",
                severity=RiskLevel.HIGH,
                message=f"Trading outside allowed hours {self.risk_limits.trading_start_time}-{self.risk_limits.trading_end_time}",
                current_value=current_time.hour + current_time.minute/60,
                limit_value=start_time.hour + start_time.minute/60,
                suggested_action="WAIT_FOR_MARKET_OPEN"
            ))
        
        return violations
    
    def _check_liquidity_volatility(self, db: Session, context: RiskCheckContext) -> List[RiskViolation]:
        """Check liquidity and volatility for specific symbol"""
        violations = []
        
        if not context.signal:
            return violations
        
        # This would typically fetch real market data
        # For now, we'll use placeholder logic
        
        return violations
    
    def _determine_risk_result(self, violations: List[RiskViolation], modifications: Dict[str, Any]) -> RiskCheckResult:
        """Determine overall risk check result"""
        if not violations:
            return RiskCheckResult.APPROVED
        
        # Check for critical violations
        critical_violations = [v for v in violations if v.severity == RiskLevel.CRITICAL]
        if critical_violations:
            return RiskCheckResult.REJECTED
        
        # Check for high severity violations
        high_violations = [v for v in violations if v.severity == RiskLevel.HIGH]
        if high_violations:
            return RiskCheckResult.REJECTED
        
        # Medium violations might be acceptable with modifications
        medium_violations = [v for v in violations if v.severity == RiskLevel.MEDIUM]
        if medium_violations:
            return RiskCheckResult.REQUIRES_APPROVAL
        
        # Low violations can be approved with warnings
        return RiskCheckResult.APPROVED
    
    def get_risk_summary(self, user_id: str) -> Dict[str, Any]:
        """Get risk summary for user"""
        recent_violations = [v for v in self.violation_history 
                           if v.timestamp > datetime_now() - timedelta(hours=24)]
        
        return {
            'total_violations_24h': len(recent_violations),
            'critical_violations_24h': len([v for v in recent_violations if v.severity == RiskLevel.CRITICAL]),
            'high_violations_24h': len([v for v in recent_violations if v.severity == RiskLevel.HIGH]),
            'recent_violations': recent_violations[-10:],  # Last 10 violations
            'risk_limits': {
                'max_position_size_pct': self.risk_limits.max_position_size_pct,
                'max_daily_loss_pct': self.risk_limits.max_daily_loss_pct,
                'max_total_exposure_pct': self.risk_limits.max_total_exposure_pct,
                'max_order_value': self.risk_limits.max_order_value
            }
        }
    
    def update_risk_limits(self, new_limits: Dict[str, Any]) -> None:
        """Update risk limits configuration"""
        for key, value in new_limits.items():
            if hasattr(self.risk_limits, key):
                setattr(self.risk_limits, key, value)
                logger.info(f"Updated risk limit {key} to {value}")
            else:
                logger.warning(f"Unknown risk limit parameter: {key}")

# Global risk manager instance
risk_manager = RiskManager() 