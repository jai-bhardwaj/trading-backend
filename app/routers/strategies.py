from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.strategy import Strategy, StrategyStatus
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class StrategyBase(BaseModel):
    name: str
    symbol: str
    entry_price: float
    quantity: int


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(StrategyBase):
    pass


class StrategyResponse(StrategyBase):
    id: int
    exit_price: float | None
    status: str
    pnl: float
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


@router.get("/strategies", response_model=List[StrategyResponse])
async def get_strategies(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    strategies = db.query(Strategy).filter(Strategy.user_id == current_user.id).all()
    return strategies


@router.post(
    "/strategies", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED
)
async def create_strategy(
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db_strategy = Strategy(**strategy.model_dump(), user_id=current_user.id)
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy


@router.put("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    strategy: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db_strategy = (
        db.query(Strategy)
        .filter(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
        .first()
    )

    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    for key, value in strategy.model_dump().items():
        setattr(db_strategy, key, value)

    db.commit()
    db.refresh(db_strategy)
    return db_strategy


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db_strategy = (
        db.query(Strategy)
        .filter(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
        .first()
    )

    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    db.delete(db_strategy)
    db.commit()


@router.post("/strategies/{strategy_id}/mock_active")
async def mock_active_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db_strategy = (
        db.query(Strategy)
        .filter(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
        .first()
    )

    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    db_strategy.status = StrategyStatus.ACTIVE
    db.commit()
    db.refresh(db_strategy)
    return {"message": "Strategy set to active"}
