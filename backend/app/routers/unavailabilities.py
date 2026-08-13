"""Afastamentos autolançados pelo perito (fluxo pré-aprovado com veto do gestor).

O perito lança seu próprio afastamento (regulamentar/legal) na Minha Agenda; ele já
vale de imediato (bloqueia a escala). O gestor vê a lista e pode **negar/remover**;
se não fizer nada, o afastamento permanece. Tudo fica na trilha de auditoria.

Não há mudança de schema: o afastamento é gravado na tabela `unavailabilities`
já existente (created_by == user_id o identifica como autolançado).
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditAction
from app.models.unavailability import Unavailability, UnavailabilityType
from app.models.user import User
from app.routers.deps import get_current_manager, get_current_user
from app.services.audit import log_action

router = APIRouter(prefix="/unavailabilities", tags=["unavailabilities"])

# Afastamento autolançado usa um tipo único (regulamentar/legal). Reutiliza o
# enum existente (sem mexer no banco); a UI o rotula como "Afastamento".
AFASTAMENTO_TYPE = UnavailabilityType.LICENSE


class AfastamentoCreate(BaseModel):
    start_date: date
    end_date: date
    notes: str | None = None


def _serialize(u: Unavailability) -> dict:
    return {
        "id": u.id,
        "user_id": u.user_id,
        "user_name": u.user.name if u.user else "",
        "type": u.type.value,
        "start_date": u.start_date,
        "end_date": u.end_date,
        "notes": u.notes,
        "created_by_id": u.created_by_id,
        "self_requested": u.created_by_id == u.user_id,
        "created_at": u.created_at,
    }


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_own_afastamento(
    data: AfastamentoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Perito lança o próprio afastamento — já vale (pré-aprovado)."""
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="Data final não pode ser anterior à inicial.")
    if data.end_date < date.today():
        raise HTTPException(status_code=400, detail="O afastamento não pode ser inteiramente no passado.")

    unav = Unavailability(
        id=str(uuid.uuid4()),
        user_id=current.id,
        type=AFASTAMENTO_TYPE,
        start_date=data.start_date,
        end_date=data.end_date,
        notes=data.notes,
        created_by_id=current.id,  # == user_id → autolançado
    )
    db.add(unav)
    db.commit()
    db.refresh(unav)
    log_action(db, current.id, AuditAction.CREATE, "Unavailability", unav.id,
               new_value={"start": str(unav.start_date), "end": str(unav.end_date)},
               description=f"Afastamento autolançado ({data.start_date} a {data.end_date})")
    return _serialize(unav)


@router.get("/me")
def list_own(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Afastamentos/indisponibilidades do próprio perito."""
    rows = (
        db.query(Unavailability)
        .filter(Unavailability.user_id == current.id)
        .order_by(Unavailability.start_date.desc())
        .all()
    )
    return [_serialize(u) for u in rows]


@router.get("", dependencies=[Depends(get_current_manager)])
@router.get("/", dependencies=[Depends(get_current_manager)])
def list_all_for_review(
    only_self_requested: bool = True,
    db: Session = Depends(get_db),
):
    """Gestor: lista afastamentos para revisão (por padrão, só os autolançados)."""
    q = db.query(Unavailability)
    if only_self_requested:
        q = q.filter(Unavailability.created_by_id == Unavailability.user_id)
    rows = q.order_by(Unavailability.created_at.desc()).all()
    return [_serialize(u) for u in rows]


@router.delete("/{unav_id}", status_code=204)
def delete_afastamento(
    unav_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Remove um afastamento. O gestor pode negar qualquer um; o perito só cancela
    os que ele mesmo lançou."""
    unav = db.get(Unavailability, unav_id)
    if not unav:
        raise HTTPException(status_code=404, detail="Afastamento não encontrado.")

    is_owner_self = unav.created_by_id == unav.user_id == current.id
    if not (current.is_manager or is_owner_self):
        raise HTTPException(status_code=403, detail="Sem permissão para remover este afastamento.")

    previous = {"user_id": unav.user_id, "start": str(unav.start_date), "end": str(unav.end_date)}
    db.delete(unav)
    db.commit()
    acao = "Afastamento negado pelo gestor" if (current.is_manager and not is_owner_self) else "Afastamento cancelado pelo perito"
    log_action(db, current.id, AuditAction.DELETE, "Unavailability", unav_id,
               previous_value=previous, description=acao)
