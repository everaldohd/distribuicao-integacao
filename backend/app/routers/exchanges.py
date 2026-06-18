"""
Trocas de escala — 1:1, mesmo grupo, com aprovação do gestor e auditoria.

Fluxos:
  Mural (aberta):  offer → (colega) propose → AWAITING_MANAGER → (gestor) approve/reject
  Direta:          direct → (colega) accept/reject → AWAITING_MANAGER → (gestor) approve/reject
  Sempre: o solicitante pode cancel; a antecedência mínima é re-checada em cada etapa.
A execução (swap das atribuições) só ocorre na aprovação do gestor, em transação.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.audit import AuditAction
from app.models.exchange import Exchange, ExchangeStatus, ExchangeType
from app.models.schedule import Assignment, Schedule, ScheduleStatus
from app.models.schedule_type import ScheduleType
from app.models.user import User
from app.routers.deps import get_current_manager, get_current_user
from app.schemas.exchange import DirectCreate, ExchangeOut, OfferCreate, ProposeRequest
from app.services.audit import log_action
from app.services.exchange_validator import get_min_lead_days, validate_exchange
from app.workers.tasks import notify_exchange

logger = get_logger(__name__)
router = APIRouter(prefix="/exchanges", tags=["exchanges"])


# ---------------------------------------------------------------------------
# Config de antecedência (gestor)
# ---------------------------------------------------------------------------

class LeadConfig(BaseModel):
    min_lead_days: int


@router.get("/config", response_model=LeadConfig, dependencies=[Depends(get_current_user)])
def get_exchange_config(db: Session = Depends(get_db)):
    return LeadConfig(min_lead_days=get_min_lead_days(db))


@router.put("/config", response_model=LeadConfig)
def set_exchange_config(data: LeadConfig, db: Session = Depends(get_db),
                        manager: User = Depends(get_current_manager)):
    from app.models.historical_balance import BalanceConfig
    cfg = db.query(BalanceConfig).first()
    if not cfg:
        cfg = BalanceConfig(id=str(uuid.uuid4()))
        db.add(cfg)
    cfg.exchange_min_lead_days = max(0, data.min_lead_days)
    db.commit()
    log_action(db, manager.id, AuditAction.UPDATE, "BalanceConfig", cfg.id,
               new_value={"exchange_min_lead_days": cfg.exchange_min_lead_days},
               description="Antecedência mínima de troca atualizada")
    return LeadConfig(min_lead_days=cfg.exchange_min_lead_days)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_of(db: Session, assignment: Assignment | None) -> str | None:
    if not assignment:
        return None
    st = db.get(ScheduleType, assignment.schedule_type_id)
    return (st.group_name or st.name) if st else None


def _type_name(db: Session, assignment: Assignment | None) -> str | None:
    if not assignment:
        return None
    st = db.get(ScheduleType, assignment.schedule_type_id)
    return st.name if st else None


def _name(db: Session, user_id: str | None) -> str | None:
    if not user_id:
        return None
    u = db.get(User, user_id)
    return u.name if u else None


def _serialize(db: Session, ex: Exchange) -> ExchangeOut:
    req_a = ex.requester_assignment
    tgt_a = ex.target_assignment
    return ExchangeOut(
        id=ex.id, type=ex.type, status=ex.status,
        requester_id=ex.requester_id, requester_name=_name(db, ex.requester_id),
        requester_date=req_a.date if req_a else None, requester_type=_type_name(db, req_a),
        group=_group_of(db, req_a),
        target_id=ex.target_id, target_name=_name(db, ex.target_id),
        target_date=tgt_a.date if tgt_a else None, target_type=_type_name(db, tgt_a),
        validation_passed=ex.validation_passed, validation_errors=ex.validation_errors,
        notes=ex.notes, created_at=ex.created_at, resolved_at=ex.resolved_at,
    )


def _published_assignment_or_400(db: Session, assignment_id: str, owner_id: str) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if not a or a.user_id != owner_id or a.is_gap:
        raise HTTPException(status_code=400, detail="Turno não pertence ao usuário")
    sched = db.get(Schedule, a.schedule_id)
    if not sched or sched.status != ScheduleStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Só é possível trocar turnos de escalas publicadas")
    return a


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

@router.get("/board", response_model=list[ExchangeOut])
def board(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mural: ofertas abertas de outros peritos aguardando proposta."""
    rows = db.query(Exchange).filter(
        Exchange.type == ExchangeType.OPEN.value,
        Exchange.status == ExchangeStatus.OPEN.value,
        Exchange.requester_id != current_user.id,
    ).order_by(Exchange.created_at.desc()).all()
    return [_serialize(db, e) for e in rows]


@router.get("/mine", response_model=list[ExchangeOut])
def mine(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Trocas em que sou solicitante ou colega envolvido."""
    rows = db.query(Exchange).filter(
        (Exchange.requester_id == current_user.id) | (Exchange.target_id == current_user.id)
    ).order_by(Exchange.created_at.desc()).all()
    return [_serialize(db, e) for e in rows]


@router.get("/pending-approval", response_model=list[ExchangeOut], dependencies=[Depends(get_current_manager)])
def pending_approval(db: Session = Depends(get_db)):
    """Gestor: trocas aceitas pelos peritos, aguardando aprovação."""
    rows = db.query(Exchange).filter(
        Exchange.status == ExchangeStatus.AWAITING_MANAGER.value
    ).order_by(Exchange.created_at.asc()).all()
    return [_serialize(db, e) for e in rows]


# ---------------------------------------------------------------------------
# Criação
# ---------------------------------------------------------------------------

@router.post("/offer", response_model=ExchangeOut, status_code=201)
def create_offer(data: OfferCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Coloca um turno à disposição no mural."""
    a = _published_assignment_or_400(db, data.requester_assignment_id, current_user.id)
    from datetime import date, timedelta
    if a.date < date.today() + timedelta(days=get_min_lead_days(db)):
        raise HTTPException(status_code=400, detail=f"Turno dentro do prazo de antecedência ({get_min_lead_days(db)} dias)")

    ex = Exchange(
        id=str(uuid.uuid4()), type=ExchangeType.OPEN.value, status=ExchangeStatus.OPEN.value,
        requester_id=current_user.id, requester_assignment_id=a.id, notes=data.notes,
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    log_action(db, current_user.id, AuditAction.EXCHANGE, "Exchange", ex.id,
               description=f"Turno {a.date} colocado à disposição")
    return _serialize(db, ex)


@router.post("/direct", response_model=ExchangeOut, status_code=201)
def create_direct(data: DirectCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Solicita troca direta com o turno de um colega."""
    req_a = _published_assignment_or_400(db, data.requester_assignment_id, current_user.id)
    tgt_a = db.get(Assignment, data.target_assignment_id)
    if not tgt_a or tgt_a.is_gap or not tgt_a.user_id:
        raise HTTPException(status_code=400, detail="Turno do colega inválido")

    result = validate_exchange(db, req_a.id, tgt_a.id)
    ex = Exchange(
        id=str(uuid.uuid4()), type=ExchangeType.DIRECT.value,
        status=ExchangeStatus.AWAITING_TARGET.value,
        requester_id=current_user.id, requester_assignment_id=req_a.id,
        target_id=tgt_a.user_id, target_assignment_id=tgt_a.id,
        validation_passed=result.passed, validation_errors=result.errors_str() or None,
        notes=data.notes,
    )
    if not result.passed:
        raise HTTPException(status_code=422, detail=f"Troca viola regras: {result.errors_str()}")
    db.add(ex)
    db.commit()
    db.refresh(ex)
    log_action(db, current_user.id, AuditAction.EXCHANGE, "Exchange", ex.id,
               description=f"Troca direta solicitada a {_name(db, tgt_a.user_id)}")
    notify_exchange.delay(ex.id, "requested")
    return _serialize(db, ex)


# ---------------------------------------------------------------------------
# Resposta do colega
# ---------------------------------------------------------------------------

@router.post("/{exchange_id}/propose", response_model=ExchangeOut)
def propose(exchange_id: str, data: ProposeRequest,
            current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Colega propõe um turno seu (mesmo grupo) para uma oferta aberta do mural."""
    ex = db.get(Exchange, exchange_id)
    if not ex or ex.status != ExchangeStatus.OPEN.value:
        raise HTTPException(status_code=400, detail="Oferta indisponível")
    if ex.requester_id == current_user.id:
        raise HTTPException(status_code=400, detail="Não é possível propor para a própria oferta")

    tgt_a = _published_assignment_or_400(db, data.target_assignment_id, current_user.id)
    result = validate_exchange(db, ex.requester_assignment_id, tgt_a.id)
    if not result.passed:
        raise HTTPException(status_code=422, detail=f"Troca viola regras: {result.errors_str()}")

    ex.target_id = current_user.id
    ex.target_assignment_id = tgt_a.id
    ex.status = ExchangeStatus.AWAITING_MANAGER.value
    ex.validation_passed = True
    ex.validation_errors = None
    db.commit()
    log_action(db, current_user.id, AuditAction.EXCHANGE, "Exchange", ex.id,
               description="Proposta enviada para oferta do mural (aguardando gestor)")
    notify_exchange.delay(ex.id, "proposed")
    return _serialize(db, ex)


@router.post("/{exchange_id}/accept", response_model=ExchangeOut)
def accept(exchange_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Colega aceita uma troca direta → vai para aprovação do gestor."""
    ex = db.get(Exchange, exchange_id)
    if not ex or ex.status != ExchangeStatus.AWAITING_TARGET.value:
        raise HTTPException(status_code=400, detail="Troca indisponível")
    if ex.target_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o colega indicado pode aceitar")

    result = validate_exchange(db, ex.requester_assignment_id, ex.target_assignment_id)
    if not result.passed:
        ex.status = ExchangeStatus.REJECTED.value
        ex.validation_passed = False
        ex.validation_errors = result.errors_str()
        db.commit()
        raise HTTPException(status_code=422, detail=f"Troca viola regras: {result.errors_str()}")

    ex.status = ExchangeStatus.AWAITING_MANAGER.value
    ex.validation_passed = True
    db.commit()
    log_action(db, current_user.id, AuditAction.EXCHANGE, "Exchange", ex.id,
               description="Colega aceitou (aguardando gestor)")
    notify_exchange.delay(ex.id, "accepted")
    return _serialize(db, ex)


@router.post("/{exchange_id}/reject", response_model=ExchangeOut)
def reject(exchange_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Colega recusa uma troca direta."""
    ex = db.get(Exchange, exchange_id)
    if not ex or ex.status != ExchangeStatus.AWAITING_TARGET.value:
        raise HTTPException(status_code=400, detail="Troca indisponível")
    if ex.target_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o colega indicado pode recusar")
    ex.status = ExchangeStatus.REJECTED.value
    ex.resolved_at = datetime.now(UTC)
    db.commit()
    log_action(db, current_user.id, AuditAction.EXCHANGE, "Exchange", ex.id, description="Colega recusou a troca")
    notify_exchange.delay(ex.id, "rejected")
    return _serialize(db, ex)


@router.post("/{exchange_id}/cancel", response_model=ExchangeOut)
def cancel(exchange_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Solicitante cancela a própria troca enquanto não aprovada."""
    ex = db.get(Exchange, exchange_id)
    if not ex or ex.requester_id != current_user.id:
        raise HTTPException(status_code=404, detail="Troca não encontrada")
    if ex.status in (ExchangeStatus.APPROVED.value, ExchangeStatus.REJECTED.value, ExchangeStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail="Troca já resolvida")
    ex.status = ExchangeStatus.CANCELLED.value
    ex.resolved_at = datetime.now(UTC)
    db.commit()
    log_action(db, current_user.id, AuditAction.EXCHANGE, "Exchange", ex.id, description="Troca cancelada pelo solicitante")
    return _serialize(db, ex)


# ---------------------------------------------------------------------------
# Aprovação do gestor (executa a troca)
# ---------------------------------------------------------------------------

@router.post("/{exchange_id}/approve", response_model=ExchangeOut)
def approve(exchange_id: str, manager: User = Depends(get_current_manager), db: Session = Depends(get_db)):
    """Gestor aprova: revalida e executa a troca (swap dos turnos) atomicamente."""
    ex = db.get(Exchange, exchange_id)
    if not ex or ex.status != ExchangeStatus.AWAITING_MANAGER.value:
        raise HTTPException(status_code=400, detail="Troca não está aguardando aprovação")

    result = validate_exchange(db, ex.requester_assignment_id, ex.target_assignment_id)
    if not result.passed:
        ex.status = ExchangeStatus.REJECTED.value
        ex.validation_passed = False
        ex.validation_errors = result.errors_str()
        ex.resolved_at = datetime.now(UTC)
        db.commit()
        log_action(db, manager.id, AuditAction.EXCHANGE, "Exchange", ex.id,
                   description=f"Recusada na aprovação (regras): {result.errors_str()}")
        raise HTTPException(status_code=422, detail=f"Troca viola regras: {result.errors_str()}")

    req_a = db.get(Assignment, ex.requester_assignment_id)
    tgt_a = db.get(Assignment, ex.target_assignment_id)
    antes = {"req_user": req_a.user_id, "tgt_user": tgt_a.user_id,
             "req_date": str(req_a.date), "tgt_date": str(tgt_a.date)}
    # Swap dos responsáveis pelas vagas
    req_a.user_id, tgt_a.user_id = tgt_a.user_id, req_a.user_id
    req_a.is_manual = tgt_a.is_manual = True

    ex.status = ExchangeStatus.APPROVED.value
    ex.approved_by_id = manager.id
    ex.resolved_at = datetime.now(UTC)
    db.commit()
    logger.info("Troca %s aprovada por %s", ex.id, manager.email)
    log_action(db, manager.id, AuditAction.EXCHANGE, "Exchange", ex.id,
               previous_value=antes, description="Troca aprovada e executada")
    notify_exchange.delay(ex.id, "approved")
    return _serialize(db, ex)


@router.post("/{exchange_id}/manager-reject", response_model=ExchangeOut)
def manager_reject(exchange_id: str, manager: User = Depends(get_current_manager), db: Session = Depends(get_db)):
    """Gestor recusa uma troca que aguardava aprovação."""
    ex = db.get(Exchange, exchange_id)
    if not ex or ex.status != ExchangeStatus.AWAITING_MANAGER.value:
        raise HTTPException(status_code=400, detail="Troca não está aguardando aprovação")
    ex.status = ExchangeStatus.REJECTED.value
    ex.approved_by_id = manager.id
    ex.resolved_at = datetime.now(UTC)
    db.commit()
    log_action(db, manager.id, AuditAction.EXCHANGE, "Exchange", ex.id, description="Troca recusada pelo gestor")
    notify_exchange.delay(ex.id, "rejected")
    return _serialize(db, ex)
