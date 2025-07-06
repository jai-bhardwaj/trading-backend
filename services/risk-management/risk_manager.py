#!/usr/bin/env python3
"""
Risk Management Service - Advanced risk controls and monitoring
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import os
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shared.common.error_handling import with_circuit_breaker, with_retry
from shared.common.security import AuditLogger
from shared.common.monitoring import MetricsCollector
from contextlib import asynccontextmanager

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

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.risk_rules = {}
        self.violations = {}
        self.metrics_collector = MetricsCollector(redis_client)
        self.audit_logger = AuditLogger(redis_client)
        
    async def initialize(self):
        """Initialize risk management system"""
        # Load default risk rules
        await self._load_default_rules()
        logger.info("✅ Risk Manager initialized")
    
    async def _load_default_rules(self):
        """Load default risk rules for all users"""
        default_rules = [
            RiskRule(
                rule_id="max_daily_loss",
                user_id="*",  # Apply to all users
                rule_type=RiskRuleType.MAX_DAILY_LOSS,
                value=50000.0,  # 50k daily loss limit
                description="Maximum daily loss limit"
            ),
            RiskRule(
                rule_id="max_position_size",
                user_id="*",
                rule_type=RiskRuleType.MAX_POSITION_SIZE,
                value=100000.0,  # 1L position size limit
                description="Maximum position size per trade"
            ),
            RiskRule(
                rule_id="max_orders_per_day",
                user_id="*",
                rule_type=RiskRuleType.MAX_ORDERS_PER_DAY,
                value=100,  # 100 orders per day
                description="Maximum orders per day"
            ),
            RiskRule(
                rule_id="max_drawdown",
                user_id="*",
                rule_type=RiskRuleType.MAX_DRAWDOWN,
                value=0.20,  # 20% max drawdown
                description="Maximum portfolio drawdown"
            ),
            RiskRule(
                rule_id="concentration_limit",
                user_id="*",
                rule_type=RiskRuleType.CONCENTRATION_LIMIT,
                value=0.25,  # 25% max concentration
                description="Maximum concentration in single stock"
            )
        ]
        
        for rule in default_rules:
            await self.add_risk_rule(rule)
    
    async def add_risk_rule(self, rule: RiskRule):
        """Add a new risk rule"""
        key = f"risk_rule:{rule.user_id}:{rule.rule_id}"
        rule_data = {
            "rule_id": rule.rule_id,
            "user_id": rule.user_id,
            "rule_type": rule.rule_type.value,
            "value": rule.value,
            "description": rule.description,
            "enabled": rule.enabled,
            "created_at": rule.created_at.isoformat()
        }
        
        await self.redis_client.setex(
            key,
            86400 * 30,  # 30 days
            json.dumps(rule_data)
        )
        
        self.risk_rules[key] = rule
        logger.info(f"✅ Added risk rule: {rule.rule_id} for user {rule.user_id}")
    
    async def check_order_risk(self, user_id: str, order_data: Dict) -> Dict[str, Any]:
        """Check if an order meets risk requirements"""
        try:
            violations = []
            
            # Check position size limit
            position_value = order_data.get("quantity", 0) * order_data.get("price", 0)
            position_rule = await self._get_rule(user_id, RiskRuleType.MAX_POSITION_SIZE)
            
            if position_rule and position_value > position_rule.value:
                violations.append({
                    "rule_type": RiskRuleType.MAX_POSITION_SIZE.value,
                    "current_value": position_value,
                    "limit_value": position_rule.value,
                    "severity": RiskLevel.HIGH
                })
            
            # Check daily order count
            daily_orders = await self._get_daily_order_count(user_id)
            order_count_rule = await self._get_rule(user_id, RiskRuleType.MAX_ORDERS_PER_DAY)
            
            if order_count_rule and daily_orders >= order_count_rule.value:
                violations.append({
                    "rule_type": RiskRuleType.MAX_ORDERS_PER_DAY.value,
                    "current_value": daily_orders,
                    "limit_value": order_count_rule.value,
                    "severity": RiskLevel.MEDIUM
                })
            
            # Check concentration limit
            concentration = await self._calculate_concentration(user_id, order_data.get("symbol", ""))
            concentration_rule = await self._get_rule(user_id, RiskRuleType.CONCENTRATION_LIMIT)
            
            if concentration_rule and concentration > concentration_rule.value:
                violations.append({
                    "rule_type": RiskRuleType.CONCENTRATION_LIMIT.value,
                    "current_value": concentration,
                    "limit_value": concentration_rule.value,
                    "severity": RiskLevel.HIGH
                })
            
            # Record violations
            for violation in violations:
                await self._record_violation(user_id, violation)
            
            # Determine overall risk level
            risk_level = self._calculate_risk_level(violations)
            
            # Record metrics
            await self.metrics_collector.record_metric(
                "risk_check",
                1,
                {"user_id": user_id, "risk_level": risk_level.value}
            )
            
            return {
                "allowed": len(violations) == 0,
                "risk_level": risk_level.value,
                "violations": violations,
                "message": "Order blocked due to risk violations" if violations else "Order approved"
            }
            
        except Exception as e:
            logger.error(f"❌ Risk check error: {e}")
            return {
                "allowed": False,
                "risk_level": RiskLevel.CRITICAL.value,
                "violations": [],
                "message": "Risk check failed"
            }
    
    async def check_portfolio_risk(self, user_id: str) -> Dict[str, Any]:
        """Check overall portfolio risk"""
        try:
            violations = []
            
            # Check daily loss
            daily_pnl = await self._get_daily_pnl(user_id)
            daily_loss_rule = await self._get_rule(user_id, RiskRuleType.MAX_DAILY_LOSS)
            
            if daily_loss_rule and abs(daily_pnl) > daily_loss_rule.value:
                violations.append({
                    "rule_type": RiskRuleType.MAX_DAILY_LOSS.value,
                    "current_value": abs(daily_pnl),
                    "limit_value": daily_loss_rule.value,
                    "severity": RiskLevel.CRITICAL
                })
            
            # Check drawdown
            drawdown = await self._calculate_drawdown(user_id)
            drawdown_rule = await self._get_rule(user_id, RiskRuleType.MAX_DRAWDOWN)
            
            if drawdown_rule and drawdown > drawdown_rule.value:
                violations.append({
                    "rule_type": RiskRuleType.MAX_DRAWDOWN.value,
                    "current_value": drawdown,
                    "limit_value": drawdown_rule.value,
                    "severity": RiskLevel.CRITICAL
                })
            
            # Check capital threshold
            capital = await self._get_user_capital(user_id)
            capital_rule = await self._get_rule(user_id, RiskRuleType.MIN_CAPITAL_THRESHOLD)
            
            if capital_rule and capital < capital_rule.value:
                violations.append({
                    "rule_type": RiskRuleType.MIN_CAPITAL_THRESHOLD.value,
                    "current_value": capital,
                    "limit_value": capital_rule.value,
                    "severity": RiskLevel.HIGH
                })
            
            risk_level = self._calculate_risk_level(violations)
            
            return {
                "risk_level": risk_level.value,
                "violations": violations,
                "metrics": {
                    "daily_pnl": daily_pnl,
                    "drawdown": drawdown,
                    "capital": capital
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Portfolio risk check error: {e}")
            return {
                "risk_level": RiskLevel.CRITICAL.value,
                "violations": [],
                "metrics": {}
            }
    
    async def get_risk_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk summary for user"""
        try:
            portfolio_risk = await self.check_portfolio_risk(user_id)
            active_violations = await self._get_active_violations(user_id)
            
            return {
                "user_id": user_id,
                "risk_level": portfolio_risk["risk_level"],
                "active_violations": len(active_violations),
                "portfolio_metrics": portfolio_risk["metrics"],
                "violations": active_violations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Risk summary error: {e}")
            return {
                "user_id": user_id,
                "risk_level": RiskLevel.CRITICAL.value,
                "active_violations": 0,
                "portfolio_metrics": {},
                "violations": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_rule(self, user_id: str, rule_type: RiskRuleType) -> Optional[RiskRule]:
        """Get risk rule for user"""
        # First try user-specific rule
        key = f"risk_rule:{user_id}:{rule_type.value}"
        rule_data = await self.redis_client.get(key)
        
        if rule_data:
            data = json.loads(rule_data)
            return RiskRule(**data)
        
        # Fall back to global rule
        key = f"risk_rule:*:{rule_type.value}"
        rule_data = await self.redis_client.get(key)
        
        if rule_data:
            data = json.loads(rule_data)
            return RiskRule(**data)
        
        return None
    
    async def _get_daily_order_count(self, user_id: str) -> int:
        """Get daily order count for user"""
        key = f"daily_orders:{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
        count = await self.redis_client.get(key)
        return int(count) if count else 0
    
    async def _calculate_concentration(self, user_id: str, symbol: str) -> float:
        """Calculate concentration in a specific symbol"""
        # This would integrate with portfolio service
        # For now, return a mock value
        return 0.15  # 15% concentration
    
    async def _get_daily_pnl(self, user_id: str) -> float:
        """Get daily P&L for user"""
        # This would integrate with portfolio service
        # For now, return a mock value
        return -5000.0  # -5k daily loss
    
    async def _calculate_drawdown(self, user_id: str) -> float:
        """Calculate current drawdown"""
        # This would integrate with portfolio service
        # For now, return a mock value
        return 0.12  # 12% drawdown
    
    async def _get_user_capital(self, user_id: str) -> float:
        """Get user's current capital"""
        # This would integrate with user service
        # For now, return a mock value
        return 95000.0  # 95k capital
    
    async def _record_violation(self, user_id: str, violation: Dict):
        """Record a risk violation"""
        violation_id = f"violation_{int(time.time())}"
        
        violation_data = {
            "violation_id": violation_id,
            "user_id": user_id,
            "rule_type": violation["rule_type"],
            "current_value": violation["current_value"],
            "limit_value": violation["limit_value"],
            "severity": violation["severity"].value,
            "timestamp": datetime.utcnow().isoformat(),
            "resolved": False
        }
        
        await self.redis_client.setex(
            f"risk_violation:{violation_id}",
            86400 * 7,  # 7 days
            json.dumps(violation_data)
        )
        
        # Add to user's violation list
        await self.redis_client.lpush(f"user_violations:{user_id}", violation_id)
        
        # Log violation
        await self.audit_logger.log_security_event(
            "risk_violation",
            user_id,
            violation_data
        )
        
        logger.warning(f"🚨 Risk violation recorded: {violation['rule_type']} for user {user_id}")
    
    async def _get_active_violations(self, user_id: str) -> List[Dict]:
        """Get active violations for user"""
        violation_ids = await self.redis_client.lrange(f"user_violations:{user_id}", 0, -1)
        violations = []
        
        for violation_id in violation_ids:
            if isinstance(violation_id, bytes):
                violation_id = violation_id.decode()
            
            violation_data = await self.redis_client.get(f"risk_violation:{violation_id}")
            if violation_data:
                violation = json.loads(violation_data)
                if not violation.get("resolved", False):
                    violations.append(violation)
        
        return violations
    
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
            severity = RiskLevel(violation["severity"])
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    global redis_client, risk_manager
    
    try:
        logger.info("🚀 Risk Management Service starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url("redis://localhost:6379/6")
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize risk manager
        risk_manager = RiskManager(redis_client)
        await risk_manager.initialize()
        
        logger.info("✅ Risk Management Service ready on port 8006")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Risk Management Service: {e}")
        raise
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
        logger.info("✅ Risk Management Service shutdown complete")

# FastAPI app
app = FastAPI(
    title="Risk Management Service",
    description="Advanced Risk Controls and Monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Global components
redis_client = None
risk_manager = None
security = HTTPBearer()

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify user token"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/dashboard",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("user_id")
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_rules": len(risk_manager.risk_rules) if risk_manager else 0
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.post("/check-order")
async def check_order_risk(
    order_data: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Check if order meets risk requirements"""
    if not risk_manager:
        raise HTTPException(status_code=503, detail="Risk manager not initialized")
    
    try:
        result = await risk_manager.check_order_risk(current_user, order_data)
        return result
        
    except Exception as e:
        logger.error(f"Error checking order risk: {e}")
        raise HTTPException(status_code=500, detail="Failed to check order risk")

@app.get("/portfolio-risk")
async def get_portfolio_risk(current_user: str = Depends(verify_user_token)):
    """Get portfolio risk assessment"""
    if not risk_manager:
        raise HTTPException(status_code=503, detail="Risk manager not initialized")
    
    try:
        result = await risk_manager.check_portfolio_risk(current_user)
        return result
        
    except Exception as e:
        logger.error(f"Error getting portfolio risk: {e}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio risk")

@app.get("/risk-summary")
async def get_risk_summary(current_user: str = Depends(verify_user_token)):
    """Get comprehensive risk summary"""
    if not risk_manager:
        raise HTTPException(status_code=503, detail="Risk manager not initialized")
    
    try:
        result = await risk_manager.get_risk_summary(current_user)
        return result
        
    except Exception as e:
        logger.error(f"Error getting risk summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get risk summary")

@app.post("/rules")
async def add_risk_rule(
    rule_data: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Add a new risk rule"""
    if not risk_manager:
        raise HTTPException(status_code=503, detail="Risk manager not initialized")
    
    try:
        rule = RiskRule(
            rule_id=rule_data["rule_id"],
            user_id=current_user,
            rule_type=RiskRuleType(rule_data["rule_type"]),
            value=rule_data["value"],
            description=rule_data["description"]
        )
        
        await risk_manager.add_risk_rule(rule)
        return {"message": "Risk rule added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding risk rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to add risk rule")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006) 