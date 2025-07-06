#!/usr/bin/env python3
"""
Risk Management Module - Risk controls and monitoring
Modular component for risk management operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskRuleType(Enum):
    MAX_POSITION_SIZE = "MAX_POSITION_SIZE"
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    MAX_ORDERS_PER_DAY = "MAX_ORDERS_PER_DAY"
    MIN_CAPITAL_THRESHOLD = "MIN_CAPITAL_THRESHOLD"
    MAX_LEVERAGE = "MAX_LEVERAGE"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"

@dataclass
class RiskRule:
    """Risk management rule"""
    rule_id: str
    user_id: str
    rule_type: RiskRuleType
    value: float
    description: str
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class RiskViolation:
    """Risk violation record"""
    violation_id: str
    user_id: str
    rule_id: str
    rule_type: RiskRuleType
    current_value: float
    limit_value: float
    severity: RiskLevel
    timestamp: datetime
    resolved: bool = False

class RiskManagementModule:
    """Modular risk management system"""
    
    def __init__(self):
        self.risk_rules: Dict[str, RiskRule] = {}
        self.violations: Dict[str, RiskViolation] = {}
        self.user_capital: Dict[str, float] = {}
        self.daily_pnl: Dict[str, float] = {}
        self.order_counts: Dict[str, int] = {}
        
    async def initialize(self):
        """Initialize risk management module"""
        logger.info("🚀 Initializing Risk Management Module...")
        
        # Load default risk rules
        await self._load_default_rules()
        
        logger.info("✅ Risk Management Module initialized")
    
    async def _load_default_rules(self):
        """Load default risk rules"""
        default_rules = [
            RiskRule(
                rule_id="max_position_size",
                user_id="default",
                rule_type=RiskRuleType.MAX_POSITION_SIZE,
                value=100000.0,
                description="Maximum position size per symbol"
            ),
            RiskRule(
                rule_id="max_daily_loss",
                user_id="default",
                rule_type=RiskRuleType.MAX_DAILY_LOSS,
                value=50000.0,
                description="Maximum daily loss limit"
            ),
            RiskRule(
                rule_id="max_orders_per_day",
                user_id="default",
                rule_type=RiskRuleType.MAX_ORDERS_PER_DAY,
                value=100,
                description="Maximum orders per day"
            ),
            RiskRule(
                rule_id="min_capital_threshold",
                user_id="default",
                rule_type=RiskRuleType.MIN_CAPITAL_THRESHOLD,
                value=10000.0,
                description="Minimum capital threshold"
            ),
            RiskRule(
                rule_id="concentration_limit",
                user_id="default",
                rule_type=RiskRuleType.CONCENTRATION_LIMIT,
                value=0.3,
                description="Maximum concentration in single symbol (30%)"
            )
        ]
        
        for rule in default_rules:
            self.risk_rules[rule.rule_id] = rule
    
    async def add_risk_rule(self, rule: RiskRule):
        """Add a new risk rule"""
        self.risk_rules[rule.rule_id] = rule
        logger.info(f"Added risk rule: {rule.rule_id} for user {rule.user_id}")
    
    async def check_order_risk(self, user_id: str, order_data: Dict) -> Dict[str, Any]:
        """Check if order meets risk requirements"""
        try:
            violations = []
            
            # Check position size limit
            position_size_rule = await self._get_rule(user_id, RiskRuleType.MAX_POSITION_SIZE)
            if position_size_rule:
                position_value = order_data["quantity"] * order_data["price"]
                if position_value > position_size_rule.value:
                    violations.append({
                        "rule_type": "MAX_POSITION_SIZE",
                        "current_value": position_value,
                        "limit_value": position_size_rule.value,
                        "severity": RiskLevel.HIGH
                    })
            
            # Check daily order count
            order_count_rule = await self._get_rule(user_id, RiskRuleType.MAX_ORDERS_PER_DAY)
            if order_count_rule:
                current_count = self.order_counts.get(user_id, 0)
                if current_count >= order_count_rule.value:
                    violations.append({
                        "rule_type": "MAX_ORDERS_PER_DAY",
                        "current_value": current_count,
                        "limit_value": order_count_rule.value,
                        "severity": RiskLevel.MEDIUM
                    })
            
            # Check capital threshold
            capital_rule = await self._get_rule(user_id, RiskRuleType.MIN_CAPITAL_THRESHOLD)
            if capital_rule:
                user_capital = self.user_capital.get(user_id, 0)
                if user_capital < capital_rule.value:
                    violations.append({
                        "rule_type": "MIN_CAPITAL_THRESHOLD",
                        "current_value": user_capital,
                        "limit_value": capital_rule.value,
                        "severity": RiskLevel.CRITICAL
                    })
            
            # Record violations
            for violation in violations:
                await self._record_violation(user_id, violation)
            
            return {
                "approved": len(violations) == 0,
                "violations": violations,
                "risk_level": self._calculate_risk_level(violations)
            }
            
        except Exception as e:
            logger.error(f"Error checking order risk: {e}")
            return {
                "approved": False,
                "error": str(e),
                "violations": []
            }
    
    async def check_portfolio_risk(self, user_id: str, positions: List[Dict]) -> Dict[str, Any]:
        """Check portfolio risk"""
        try:
            violations = []
            total_value = sum(pos["position_value"] for pos in positions)
            
            # Check concentration limits
            concentration_rule = await self._get_rule(user_id, RiskRuleType.CONCENTRATION_LIMIT)
            if concentration_rule and total_value > 0:
                for position in positions:
                    concentration = position["position_value"] / total_value
                    if concentration > concentration_rule.value:
                        violations.append({
                            "rule_type": "CONCENTRATION_LIMIT",
                            "symbol": position["symbol"],
                            "current_value": concentration,
                            "limit_value": concentration_rule.value,
                            "severity": RiskLevel.MEDIUM
                        })
            
            # Check daily loss
            daily_loss_rule = await self._get_rule(user_id, RiskRuleType.MAX_DAILY_LOSS)
            if daily_loss_rule:
                daily_pnl = self.daily_pnl.get(user_id, 0)
                if daily_pnl < -daily_loss_rule.value:
                    violations.append({
                        "rule_type": "MAX_DAILY_LOSS",
                        "current_value": abs(daily_pnl),
                        "limit_value": daily_loss_rule.value,
                        "severity": RiskLevel.HIGH
                    })
            
            return {
                "risk_level": self._calculate_risk_level(violations),
                "violations": violations,
                "total_value": total_value,
                "daily_pnl": self.daily_pnl.get(user_id, 0)
            }
            
        except Exception as e:
            logger.error(f"Error checking portfolio risk: {e}")
            return {
                "error": str(e),
                "violations": []
            }
    
    async def get_risk_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            # Get active violations
            active_violations = await self._get_active_violations(user_id)
            
            # Calculate risk metrics
            risk_level = self._calculate_risk_level(active_violations)
            
            # Get user capital
            user_capital = self.user_capital.get(user_id, 0)
            daily_pnl = self.daily_pnl.get(user_id, 0)
            
            return {
                "user_id": user_id,
                "risk_level": risk_level.value,
                "active_violations": len(active_violations),
                "user_capital": user_capital,
                "daily_pnl": daily_pnl,
                "order_count": self.order_counts.get(user_id, 0),
                "violations": [
                    {
                        "rule_type": v["rule_type"],
                        "severity": v["severity"].value,
                        "current_value": v["current_value"],
                        "limit_value": v["limit_value"]
                    }
                    for v in active_violations
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {"error": str(e)}
    
    async def _get_rule(self, user_id: str, rule_type: RiskRuleType) -> Optional[RiskRule]:
        """Get risk rule for user and type"""
        for rule in self.risk_rules.values():
            if rule.user_id in [user_id, "default"] and rule.rule_type == rule_type:
                return rule
        return None
    
    async def _record_violation(self, user_id: str, violation_data: Dict):
        """Record a risk violation"""
        violation_id = f"violation_{int(time.time() * 1000)}"
        
        violation = RiskViolation(
            violation_id=violation_id,
            user_id=user_id,
            rule_id=violation_data["rule_type"],
            rule_type=RiskRuleType(violation_data["rule_type"]),
            current_value=violation_data["current_value"],
            limit_value=violation_data["limit_value"],
            severity=RiskLevel(violation_data["severity"]),
            timestamp=datetime.utcnow()
        )
        
        self.violations[violation_id] = violation
        logger.warning(f"Risk violation recorded: {violation_data['rule_type']} for user {user_id}")
    
    async def _get_active_violations(self, user_id: str) -> List[Dict]:
        """Get active violations for user"""
        active_violations = []
        
        for violation in self.violations.values():
            if violation.user_id == user_id and not violation.resolved:
                active_violations.append({
                    "rule_type": violation.rule_type.value,
                    "current_value": violation.current_value,
                    "limit_value": violation.limit_value,
                    "severity": violation.severity
                })
        
        return active_violations
    
    def _calculate_risk_level(self, violations: List[Dict]) -> RiskLevel:
        """Calculate overall risk level based on violations"""
        if not violations:
            return RiskLevel.LOW
        
        # Count violations by severity
        severity_counts = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 0,
            RiskLevel.HIGH: 0,
            RiskLevel.CRITICAL: 0
        }
        
        for violation in violations:
            severity = violation["severity"]
            severity_counts[severity] += 1
        
        # Determine overall risk level
        if severity_counts[RiskLevel.CRITICAL] > 0:
            return RiskLevel.CRITICAL
        elif severity_counts[RiskLevel.HIGH] > 0:
            return RiskLevel.HIGH
        elif severity_counts[RiskLevel.MEDIUM] > 0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def update_user_capital(self, user_id: str, capital: float):
        """Update user capital"""
        self.user_capital[user_id] = capital
    
    async def update_daily_pnl(self, user_id: str, pnl: float):
        """Update daily P&L"""
        self.daily_pnl[user_id] = pnl
    
    async def increment_order_count(self, user_id: str):
        """Increment daily order count"""
        self.order_counts[user_id] = self.order_counts.get(user_id, 0) + 1
    
    async def stop(self):
        """Stop risk management module"""
        logger.info("🔄 Risk Management Module stopped")

# Global risk management module instance
risk_management_module = RiskManagementModule() 