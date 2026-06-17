from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from app.core.database import get_db
from app.models.preference import UserPreference, PreferenceType
from app.models.user import User
from app.routers.deps import get_current_user
import uuid

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferenceIn:
    pass


from pydantic import BaseModel


class PreferenceCreate(BaseModel):
    year: int
    month: int
    date: date
    type: PreferenceType


class PreferenceOut(BaseModel):
    id: str
    year: int
    month: int
    date: date
    type: PreferenceType

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[PreferenceOut])
def list_my_preferences(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id,
        UserPreference.year == year,
        UserPreference.month == month,
    ).all()


@router.post("/", response_model=PreferenceOut, status_code=201)
def add_preference(
    data: PreferenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id,
        UserPreference.year == data.year,
        UserPreference.month == data.month,
        UserPreference.date == data.date,
        UserPreference.type == data.type,
    ).first()
    if existing:
        return existing
    pref = UserPreference(id=str(uuid.uuid4()), user_id=current_user.id, **data.model_dump())
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


@router.delete("/{pref_id}", status_code=204)
def delete_preference(
    pref_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pref = db.get(UserPreference, pref_id)
    if not pref or pref.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Preferência não encontrada")
    db.delete(pref)
    db.commit()
