from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.models.base import Base
import enum

class NotificationType(enum.Enum):
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    SERVICE_DOWN = "SERVICE_DOWN"
    SERVICE_RESTORED = "SERVICE_RESTORED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"
    RISK_ALERT = "RISK_ALERT"

class AlertLevel(enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Notification(Base):
    __tablename__ = 'notifications'

    notification_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=True)  # Null for system-wide
    notification_type = Column(Enum(NotificationType), nullable=False)
    alert_level = Column(Enum(AlertLevel), default=AlertLevel.INFO)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, default=dict)  # Additional notification data
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications") 