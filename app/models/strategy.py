from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class StrategyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    symbol = Column(String, index=True)
    margin = Column(Float, nullable=False)
    marginType = Column(String, nullable=False)  # 'rupees' or 'percentage'
    basePrice = Column(Float, nullable=False)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.ACTIVE, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lastUpdated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship with User
    user = relationship("User", back_populates="strategies")

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "margin": self.margin,
            "marginType": self.marginType,
            "basePrice": self.basePrice,
            "status": self.status.value if isinstance(self.status, enum.Enum) else self.status,
            "lastUpdated": self.lastUpdated,
            "user_id": self.user_id
        }
