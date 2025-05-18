from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str  # username field for OAuth2 compatibility
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class StrategyBase(BaseModel):
    name: str
    margin: float
    marginType: str
    basePrice: float
    status: str


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    margin: Optional[float] = None
    marginType: Optional[str] = None
    basePrice: Optional[float] = None
    status: Optional[str] = None


class Strategy(StrategyBase):
    id: str
    lastUpdated: datetime
    user_id: str

    class Config:
        from_attributes = True


class Message(BaseModel):
    message: str


class OrderBase(BaseModel):
    symbol: str
    order_type: str
    quantity: int
    price: float
    strategy_id: str


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    exchange_order_id: Optional[str] = None
    exchange_status: Optional[str] = None
    exchange_message: Optional[str] = None


class Order(OrderBase):
    id: str
    user_id: str
    status: str
    order_time: datetime
    last_updated: datetime
    exchange_order_id: Optional[str] = None
    exchange_status: Optional[str] = None
    exchange_message: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class OrderResponse(BaseModel):
    message: str
    order: Optional[Order] = None
