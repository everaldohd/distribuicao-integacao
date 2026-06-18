from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from app.core.database import get_db
from app.models.profile import Profile, ProfileGroupLimit
from app.models.schedule_type import ScheduleType
from app.routers.deps import get_current_user, get_current_manager
import uuid

router = APIRouter(prefix="/profiles", tags=["profiles"])


class GroupLimitOut(BaseModel):
    group_name: str
    max_quantity: int

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    is_custom: bool
    is_system: bool
    group_limits: List[GroupLimitOut] = []

    model_config = {"from_attributes": True}


class ProfileWrite(BaseModel):
    name: str
    description: Optional[str] = None
    limits: Dict[str, int] = {}   # {group_name: max_quantity}


class GroupTypeOut(BaseModel):
    name: str
    weight: int


class GroupOut(BaseModel):
    group_name: str
    types: List[GroupTypeOut]


def _ordered_groups(db: Session) -> List[str]:
    """Grupos na ordem de exibição dos tipos."""
    types = db.query(ScheduleType).order_by(ScheduleType.display_order, ScheduleType.name).all()
    seen: list[str] = []
    for t in types:
        g = t.group_name or t.name
        if g not in seen:
            seen.append(g)
    return seen


@router.get("/", response_model=List[ProfileOut], dependencies=[Depends(get_current_user)])
def list_profiles(db: Session = Depends(get_db)):
    # Ordena: fixos primeiro, depois custom/default no fim
    profiles = db.query(Profile).order_by(Profile.is_custom, Profile.is_default, Profile.name).all()
    return profiles


@router.get("/groups", response_model=List[GroupOut], dependencies=[Depends(get_current_user)])
def list_groups(db: Session = Depends(get_db)):
    types = db.query(ScheduleType).filter(ScheduleType.is_active == True)\
        .order_by(ScheduleType.display_order, ScheduleType.name).all()
    grupos: dict[str, list] = {}
    for t in types:
        g = t.group_name or t.name
        grupos.setdefault(g, []).append(GroupTypeOut(name=t.name, weight=t.group_weight or 1))
    return [GroupOut(group_name=g, types=ts) for g, ts in grupos.items()]


def _set_limits(db: Session, profile: Profile, limits: Dict[str, int]):
    existing = {gl.group_name: gl for gl in profile.group_limits}
    valid_groups = set(_ordered_groups(db))
    for group, qty in limits.items():
        if group not in valid_groups:
            continue
        if group in existing:
            existing[group].max_quantity = qty
        else:
            db.add(ProfileGroupLimit(id=str(uuid.uuid4()), profile_id=profile.id, group_name=group, max_quantity=qty))


@router.post("/", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(data: ProfileWrite, db: Session = Depends(get_db), manager=Depends(get_current_manager)):
    if db.query(Profile).filter(Profile.name == data.name).first():
        raise HTTPException(status_code=400, detail="Já existe um perfil com esse nome")
    profile = Profile(id=str(uuid.uuid4()), name=data.name, description=data.description)
    db.add(profile)
    db.flush()
    _set_limits(db, profile, data.limits)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: str, data: ProfileWrite, db: Session = Depends(get_db), manager=Depends(get_current_manager)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    if profile.is_custom:
        raise HTTPException(status_code=400, detail="O perfil Personalizado é configurado por perito, não aqui")
    profile.name = data.name
    profile.description = data.description
    _set_limits(db, profile, data.limits)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db), manager=Depends(get_current_manager)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    if profile.is_system:
        raise HTTPException(status_code=400, detail="Perfis do sistema não podem ser excluídos")
    # Peritos que usavam este perfil ficam sem perfil (caem no padrão)
    from app.models.user import User
    db.query(User).filter(User.profile_id == profile_id).update({User.profile_id: None})
    db.delete(profile)
    db.commit()
