from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date
from pydantic import BaseModel
from app.core.database import get_db
from app.core.config import settings
from app.models.preference import UserPreference, PreferenceType
from app.models.schedule_type import ScheduleType
from app.models.profile import Profile, ProfileGroupLimit, UserGroupLimit
from app.models.operational_calendar import OperationalCalendar
from app.models.historical_balance import BalanceConfig
from app.models.user import User
from app.routers.deps import get_current_user, get_current_manager
import uuid

router = APIRouter(prefix="/preferences", tags=["preferences"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _factor(db: Session) -> int:
    cfg = db.query(BalanceConfig).first()
    return cfg.preference_factor if cfg and cfg.preference_factor else 2


def _group_limits_for(db: Session, user: User) -> Dict[str, int]:
    """Cota máxima por grupo (Plantão/Reserva/Pátio) do perito."""
    profile = db.get(Profile, user.profile_id) if user.profile_id else None
    if profile is None:
        profile = db.query(Profile).filter(Profile.is_default == True).first()
    if profile and profile.is_custom:
        return {l.group_name: l.max_quantity for l in
                db.query(UserGroupLimit).filter(UserGroupLimit.user_id == user.id).all()}
    if profile:
        return {l.group_name: l.max_quantity for l in profile.group_limits}
    return {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PreferenceCreate(BaseModel):
    year: int
    month: int
    date: date
    schedule_type_id: str
    type: PreferenceType


class PreferenceOut(BaseModel):
    id: str
    year: int
    month: int
    date: date
    schedule_type_id: Optional[str]
    type: PreferenceType

    model_config = {"from_attributes": True}


class ModalityOut(BaseModel):
    schedule_type_id: str
    name: str
    group_name: str


class OptionsOut(BaseModel):
    factor: int
    modalities: List[ModalityOut]
    group_caps: Dict[str, int]                 # {group: cota_grupo * fator}
    availability: Dict[str, List[str]]         # {schedule_type_id: [datas ISO]}
    preferences: List[PreferenceOut]
    calendar_open: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/options", response_model=OptionsOut)
def get_options(year: int, month: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tudo que a tela de preferências do perito precisa: modalidades, limites, disponibilidade."""
    factor = _factor(db)
    glimits = _group_limits_for(db, current_user)

    # Modalidades = tipos cujo grupo tem cota > 0 para este perito
    types = db.query(ScheduleType).filter(ScheduleType.is_active == True)\
        .order_by(ScheduleType.display_order, ScheduleType.name).all()
    modalities = []
    for t in types:
        g = t.group_name or t.name
        if glimits.get(g, 0) > 0:
            modalities.append(ModalityOut(schedule_type_id=t.id, name=t.name, group_name=g))

    group_caps = {g: lim * factor for g, lim in glimits.items() if lim > 0}

    # Disponibilidade: dias do calendário do mês com cobertura > 0 por tipo
    cal = db.query(OperationalCalendar).filter(
        OperationalCalendar.year == year, OperationalCalendar.month == month
    ).first()
    availability: Dict[str, List[str]] = {}
    calendar_open = bool(cal and cal.status.value == "open")
    if cal:
        for day in cal.days:
            for cov in day.coverages:
                if cov.quantity > 0:
                    availability.setdefault(cov.schedule_type_id, []).append(day.date.isoformat())

    prefs = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id,
        UserPreference.year == year, UserPreference.month == month,
    ).all()

    return OptionsOut(
        factor=factor,
        modalities=modalities,
        group_caps=group_caps,
        availability=availability,
        preferences=prefs,
        calendar_open=calendar_open,
    )


@router.get("/", response_model=List[PreferenceOut])
def list_my_preferences(year: int, month: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id,
        UserPreference.year == year, UserPreference.month == month,
    ).all()


@router.post("/", response_model=PreferenceOut, status_code=201)
def add_preference(data: PreferenceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stype = db.get(ScheduleType, data.schedule_type_id)
    if not stype:
        raise HTTPException(status_code=404, detail="Tipo de escala não encontrado")
    group = stype.group_name or stype.name

    glimits = _group_limits_for(db, current_user)
    cap = glimits.get(group, 0) * _factor(db)
    if cap <= 0:
        raise HTTPException(status_code=400, detail="Seu perfil não permite preferências para esta modalidade")

    # Conta preferências já marcadas no mesmo grupo e mesmo tipo (desejo/evitar), separadamente
    existing = db.query(UserPreference).join(
        ScheduleType, ScheduleType.id == UserPreference.schedule_type_id
    ).filter(
        UserPreference.user_id == current_user.id,
        UserPreference.year == data.year, UserPreference.month == data.month,
        UserPreference.type == data.type,
        ScheduleType.group_name == group,
    ).all()

    # Já existe exatamente esta marcação? retorna idempotente
    for e in existing:
        if e.date == data.date and e.schedule_type_id == data.schedule_type_id:
            return e

    if len(existing) >= cap:
        raise HTTPException(status_code=400,
                            detail=f"Limite de {cap} dia(s) de '{data.type.value}' para o grupo {group} atingido")

    pref = UserPreference(
        id=str(uuid.uuid4()), user_id=current_user.id,
        year=data.year, month=data.month, date=data.date,
        schedule_type_id=data.schedule_type_id, type=data.type,
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


@router.delete("/{pref_id}", status_code=204)
def delete_preference(pref_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pref = db.get(UserPreference, pref_id)
    if not pref or pref.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Preferência não encontrada")
    db.delete(pref)
    db.commit()


# ---------------------------------------------------------------------------
# Config do fator (gestor)
# ---------------------------------------------------------------------------

class FactorOut(BaseModel):
    preference_factor: int


class FactorSet(BaseModel):
    preference_factor: int


@router.get("/config", response_model=FactorOut, dependencies=[Depends(get_current_user)])
def get_pref_config(db: Session = Depends(get_db)):
    return FactorOut(preference_factor=_factor(db))


@router.put("/config", response_model=FactorOut)
def set_pref_config(data: FactorSet, db: Session = Depends(get_db), manager: User = Depends(get_current_manager)):
    cfg = db.query(BalanceConfig).first()
    if not cfg:
        cfg = BalanceConfig(id=str(uuid.uuid4()))
        db.add(cfg)
    cfg.preference_factor = max(0, data.preference_factor)
    db.commit()
    return FactorOut(preference_factor=cfg.preference_factor)
