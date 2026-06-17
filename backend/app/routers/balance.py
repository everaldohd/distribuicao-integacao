from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.historical_balance import HistoricalBalance, BalanceConfig
from app.models.user import User
from app.routers.deps import get_current_user, get_current_manager
from pydantic import BaseModel

router = APIRouter(prefix="/balance", tags=["balance"])


class BalanceOut(BaseModel):
    year: int
    month: int
    delta: float
    cumulative_balance: float
    events_count_no_schedule: int
    events_count_desired_fulfilled: int
    events_count_avoided_assigned: int

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    user_id: str
    user_name: str
    cumulative_balance: float
    rank: int


class BalanceConfigOut(BaseModel):
    month_no_schedule: int
    desired_date_fulfilled: int
    common_schedule: int
    avoided_date_assigned: int

    model_config = {"from_attributes": True}


class BalanceConfigUpdate(BaseModel):
    month_no_schedule: int
    desired_date_fulfilled: int
    common_schedule: int
    avoided_date_assigned: int


@router.get("/me", response_model=List[BalanceOut])
def my_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(HistoricalBalance).filter(
        HistoricalBalance.user_id == current_user.id
    ).order_by(HistoricalBalance.year.desc(), HistoricalBalance.month.desc()).all()


@router.get("/leaderboard", response_model=List[LeaderboardEntry], dependencies=[Depends(get_current_user)])
def leaderboard(db: Session = Depends(get_db)):
    from sqlalchemy import func
    # Último saldo acumulado por usuário
    subq = db.query(
        HistoricalBalance.user_id,
        func.max(HistoricalBalance.cumulative_balance).label("balance"),
    ).group_by(HistoricalBalance.user_id).subquery()

    results = db.query(User.id, User.name, subq.c.balance).join(
        subq, User.id == subq.c.user_id
    ).filter(User.is_active == True).order_by(subq.c.balance.desc()).all()

    return [
        LeaderboardEntry(user_id=r[0], user_name=r[1], cumulative_balance=r[2] or 0.0, rank=i + 1)
        for i, r in enumerate(results)
    ]


@router.get("/config", response_model=BalanceConfigOut, dependencies=[Depends(get_current_user)])
def get_config(db: Session = Depends(get_db)):
    cfg = db.query(BalanceConfig).first()
    if not cfg:
        from app.core.config import settings
        return BalanceConfigOut(
            month_no_schedule=settings.BALANCE_MONTH_NO_SCHEDULE,
            desired_date_fulfilled=settings.BALANCE_DESIRED_DATE_FULFILLED,
            common_schedule=settings.BALANCE_COMMON_SCHEDULE,
            avoided_date_assigned=settings.BALANCE_AVOIDED_DATE_ASSIGNED,
        )
    return cfg


@router.put("/config", response_model=BalanceConfigOut)
def update_config(
    data: BalanceConfigUpdate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    cfg = db.query(BalanceConfig).first()
    if not cfg:
        import uuid
        cfg = BalanceConfig(id=str(uuid.uuid4()), **data.model_dump(), updated_by_id=manager.id)
        db.add(cfg)
    else:
        for field, value in data.model_dump().items():
            setattr(cfg, field, value)
        cfg.updated_by_id = manager.id
    db.commit()
    db.refresh(cfg)
    return cfg
