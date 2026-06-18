from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.historical_balance import HistoricalBalance
from app.models.eligibility import Eligibility
from app.models.schedule_type import ScheduleType
from app.models.unavailability import Unavailability, UnavailabilityType
from app.models.profile import Profile, ProfileGroupLimit, UserGroupLimit
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserPasswordChange
from app.routers.deps import get_current_user, get_current_manager
from app.services.balance import compute_new_user_initial_balance
from app.services.audit import log_action
from app.models.audit import AuditAction
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/password")
def change_password(
    data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.security import verify_password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Senha alterada com sucesso"}


# --- Manager endpoints ---

@router.get("/", response_model=List[UserOut], dependencies=[Depends(get_current_manager)])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.name).all()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    initial_balance = compute_new_user_initial_balance(db)

    user = User(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        matricula=data.matricula,
        hashed_password=hash_password(data.password),
        is_manager=data.is_manager,
        profile_id=data.profile_id,
    )
    db.add(user)
    db.flush()  # get user.id

    # Saldo inicial = média dos usuários ativos
    if initial_balance is not None:
        balance_entry = HistoricalBalance(
            user_id=user.id,
            year=0,
            month=0,
            delta=initial_balance,
            cumulative_balance=initial_balance,
        )
        db.add(balance_entry)

    db.commit()
    db.refresh(user)
    log_action(db, manager.id, AuditAction.CREATE, "User", user.id,
               new_value={"name": user.name, "email": user.email, "is_manager": user.is_manager},
               description=f"Usuário criado: {user.name}")
    return user


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(get_current_manager)])
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    changes = data.model_dump(exclude_none=True)
    previous = {k: getattr(user, k) for k in changes}
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    log_action(db, manager.id, AuditAction.UPDATE, "User", user.id,
               previous_value=previous, new_value=changes,
               description=f"Usuário atualizado: {user.name}")
    return user


# ---------------------------------------------------------------------------
# Elegibilidades (de quais tipos de escala o usuário pode participar)
# ---------------------------------------------------------------------------

class EligibilityItem(BaseModel):
    schedule_type_id: str
    schedule_type_name: str
    is_eligible: bool


class EligibilitySet(BaseModel):
    eligible_type_ids: List[str]


def _get_user_or_404(user_id: str, db: Session) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.get("/{user_id}/eligibilities", response_model=List[EligibilityItem],
            dependencies=[Depends(get_current_manager)])
def get_eligibilities(user_id: str, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    types = db.query(ScheduleType).filter(ScheduleType.is_active == True)\
        .order_by(ScheduleType.display_order, ScheduleType.name).all()
    eligible_ids = {
        e.schedule_type_id
        for e in db.query(Eligibility).filter(
            Eligibility.user_id == user_id, Eligibility.is_eligible == True
        ).all()
    }
    return [
        EligibilityItem(
            schedule_type_id=t.id,
            schedule_type_name=t.name,
            is_eligible=t.id in eligible_ids,
        )
        for t in types
    ]


@router.put("/{user_id}/eligibilities")
def set_eligibilities(user_id: str, data: EligibilitySet, db: Session = Depends(get_db),
                      manager: User = Depends(get_current_manager)):
    user = _get_user_or_404(user_id, db)
    wanted = set(data.eligible_type_ids)
    existing = {e.schedule_type_id: e for e in db.query(Eligibility).filter(Eligibility.user_id == user_id).all()}

    # Atualiza/insere
    for type_id in wanted:
        if type_id in existing:
            existing[type_id].is_eligible = True
        else:
            db.add(Eligibility(id=str(uuid.uuid4()), user_id=user_id, schedule_type_id=type_id, is_eligible=True))
    # Desmarca os não selecionados
    for type_id, e in existing.items():
        if type_id not in wanted:
            e.is_eligible = False

    db.commit()
    log_action(db, manager.id, AuditAction.UPDATE, "Eligibility", user_id,
               new_value={"eligible_type_ids": list(wanted)},
               description=f"Elegibilidades de {user.name}: {len(wanted)} tipo(s)")
    return {"message": f"Elegibilidades atualizadas: {len(wanted)} tipo(s) habilitado(s)"}


# ---------------------------------------------------------------------------
# Indisponibilidades (férias, abono, licença)
# ---------------------------------------------------------------------------

class UnavailabilityOut(BaseModel):
    id: str
    type: UnavailabilityType
    start_date: date
    end_date: date
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class UnavailabilityCreate(BaseModel):
    type: UnavailabilityType = UnavailabilityType.VACATION
    start_date: date
    end_date: date
    notes: Optional[str] = None


@router.get("/{user_id}/unavailabilities", response_model=List[UnavailabilityOut],
            dependencies=[Depends(get_current_manager)])
def list_unavailabilities(user_id: str, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    return db.query(Unavailability).filter(Unavailability.user_id == user_id)\
        .order_by(Unavailability.start_date.desc()).all()


@router.post("/{user_id}/unavailabilities", response_model=UnavailabilityOut, status_code=201)
def add_unavailability(
    user_id: str,
    data: UnavailabilityCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    _get_user_or_404(user_id, db)
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="Data final não pode ser anterior à inicial")
    unav = Unavailability(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=data.type,
        start_date=data.start_date,
        end_date=data.end_date,
        notes=data.notes,
        created_by_id=manager.id,
    )
    db.add(unav)
    db.commit()
    db.refresh(unav)
    log_action(db, manager.id, AuditAction.CREATE, "Unavailability", unav.id,
               new_value={"type": unav.type.value, "start": str(unav.start_date), "end": str(unav.end_date)},
               description=f"{unav.type.value} de {data.start_date} a {data.end_date}")
    return unav


@router.delete("/{user_id}/unavailabilities/{unav_id}", status_code=204)
def delete_unavailability(user_id: str, unav_id: str, db: Session = Depends(get_db),
                          manager: User = Depends(get_current_manager)):
    unav = db.get(Unavailability, unav_id)
    if not unav or unav.user_id != user_id:
        raise HTTPException(status_code=404, detail="Indisponibilidade não encontrada")
    previous = {"type": unav.type.value, "start": str(unav.start_date), "end": str(unav.end_date)}
    db.delete(unav)
    db.commit()
    log_action(db, manager.id, AuditAction.DELETE, "Unavailability", unav_id,
               previous_value=previous, description="Indisponibilidade removida")


# ---------------------------------------------------------------------------
# Limites por grupo (cota máxima de Plantão / Reserva / Pátio) do perito
# ---------------------------------------------------------------------------

class UserLimitsOut(BaseModel):
    profile_id: Optional[str]
    profile_name: str
    is_custom: bool
    limits: dict  # {group_name: max_quantity}


class UserLimitsSet(BaseModel):
    limits: dict  # {group_name: max_quantity}


def _ordered_group_names(db: Session) -> List[str]:
    types = db.query(ScheduleType).order_by(ScheduleType.display_order, ScheduleType.name).all()
    seen: List[str] = []
    for t in types:
        g = t.group_name or t.name
        if g not in seen:
            seen.append(g)
    return seen


def _effective_limits(db: Session, user: User) -> tuple[Optional[Profile], dict]:
    """Retorna (perfil_efetivo, {grupo: limite}) considerando perfil fixo, custom ou padrão."""
    groups = _ordered_group_names(db)
    profile = db.get(Profile, user.profile_id) if user.profile_id else None
    if profile is None:
        profile = db.query(Profile).filter(Profile.is_default == True).first()

    if profile and profile.is_custom:
        base = {l.group_name: l.max_quantity for l in
                db.query(UserGroupLimit).filter(UserGroupLimit.user_id == user.id).all()}
    elif profile:
        base = {l.group_name: l.max_quantity for l in profile.group_limits}
    else:
        base = {}
    return profile, {g: base.get(g, 0) for g in groups}


@router.get("/{user_id}/limits", response_model=UserLimitsOut, dependencies=[Depends(get_current_manager)])
def get_user_limits(user_id: str, db: Session = Depends(get_db)):
    user = _get_user_or_404(user_id, db)
    profile, limits = _effective_limits(db, user)
    return UserLimitsOut(
        profile_id=profile.id if profile else None,
        profile_name=profile.name if profile else "—",
        is_custom=bool(profile and profile.is_custom),
        limits=limits,
    )


@router.put("/{user_id}/limits", response_model=UserLimitsOut)
def set_user_limits(user_id: str, data: UserLimitsSet, db: Session = Depends(get_db),
                    manager: User = Depends(get_current_manager)):
    """Define limites individuais → move o perito para o perfil Personalizado."""
    user = _get_user_or_404(user_id, db)
    custom = db.query(Profile).filter(Profile.is_custom == True).first()
    if not custom:
        raise HTTPException(status_code=500, detail="Perfil Personalizado não configurado")

    user.profile_id = custom.id
    groups = set(_ordered_group_names(db))
    existing = {l.group_name: l for l in db.query(UserGroupLimit).filter(UserGroupLimit.user_id == user_id).all()}
    for group, qty in data.limits.items():
        if group not in groups:
            continue
        if group in existing:
            existing[group].max_quantity = qty
        else:
            db.add(UserGroupLimit(id=str(uuid.uuid4()), user_id=user_id, group_name=group, max_quantity=qty))
    db.commit()
    db.refresh(user)
    profile, limits = _effective_limits(db, user)
    log_action(db, manager.id, AuditAction.UPDATE, "UserGroupLimit", user_id,
               new_value={"limits": dict(data.limits)},
               description=f"Cotas individuais de {user.name} (→ Personalizado)")
    return UserLimitsOut(
        profile_id=profile.id if profile else None,
        profile_name=profile.name if profile else "—",
        is_custom=True,
        limits=limits,
    )
