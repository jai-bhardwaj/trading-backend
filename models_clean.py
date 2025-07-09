# Updated SQLAlchemy models for cleaned trading system
from sqlalchemy import Column, Boolean, Text, DateTime, JSON, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, nullable=False)
    strategy_type = Column(Text, nullable=False)
    symbols = Column(ARRAY(Text), nullable=False)
    parameters = Column(JSON, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    class_name = Column(Text, nullable=False)
    module_path = Column(Text, nullable=False)
    config_json = Column(JSON, nullable=False)
    status = Column(Text, nullable=False, default="ACTIVE")
    auto_start = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
