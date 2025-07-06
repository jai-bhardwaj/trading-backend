from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.models.base import Base
import enum

class RuleType(enum.Enum):
    MAX_POSITION_SIZE = "MAX_POSITION_SIZE"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"
    MAX_ORDERS_PER_DAY = "MAX_ORDERS_PER_DAY"
    MIN_CAPITAL_THRESHOLD = "MIN_CAPITAL_THRESHOLD"

class RiskRule(Base):
    __tablename__ = 'risk_rules'

    rule_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    rule_type = Column(Enum(RuleType), nullable=False)
    rule_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    is_violated = Column(Boolean, default=False)
    violation_message = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="risk_rules") 