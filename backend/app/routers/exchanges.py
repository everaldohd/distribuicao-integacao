from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.core.database import get_db
from app.models.exchange import Exchange, ExchangeType, ExchangeStatus
from app.models.schedule import Assignment
from app.models.user import User
from app.schemas.exchange import ExchangeCreate, ExchangeOut, ExchangeAccept
from app.routers.deps import get_current_user
from app.services.exchange_validator import validate_exchange
from app.workers.tasks import notify_exchange
import uuid

router = APIRouter(prefix="/exchanges", tags=["exchanges"])


@router.get("/", response_model=List[ExchangeOut])
def list_exchanges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Exchange).filter(
        (Exchange.requester_id == current_user.id) | (Exchange.target_id == current_user.id)
    ).order_by(Exchange.created_at.desc()).all()


@router.get("/open", response_model=List[ExchangeOut])
def list_open_exchanges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trocas abertas disponíveis para o usuário atual aceitar."""
    return db.query(Exchange).filter(
        Exchange.type == ExchangeType.OPEN,
        Exchange.status == ExchangeStatus.PENDING,
        Exchange.requester_id != current_user.id,
    ).all()


@router.post("/", response_model=ExchangeOut, status_code=201)
def create_exchange(
    data: ExchangeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verificar que a atribuição pertence ao usuário
    assignment = db.get(Assignment, data.requester_assignment_id)
    if not assignment or assignment.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Atribuição não pertence ao usuário")

    exchange = Exchange(
        id=str(uuid.uuid4()),
        type=data.type,
        requester_id=current_user.id,
        requester_assignment_id=data.requester_assignment_id,
        target_id=data.target_id,
        target_assignment_id=data.target_assignment_id,
        notes=data.notes,
    )

    # Validação imediata se for troca direta
    if data.type == ExchangeType.DIRECT and data.target_assignment_id:
        result = validate_exchange(db, data.requester_assignment_id, data.target_assignment_id)
        exchange.validation_passed = result.passed
        exchange.validation_errors = result.errors_str()
        if not result.passed:
            exchange.status = ExchangeStatus.INVALID

    db.add(exchange)
    db.commit()
    db.refresh(exchange)

    if exchange.status == ExchangeStatus.PENDING and data.target_id:
        notify_exchange.delay(exchange.id, "requested")

    return exchange


@router.post("/{exchange_id}/accept")
def accept_exchange(
    exchange_id: str,
    data: ExchangeAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exchange = db.get(Exchange, exchange_id)
    if not exchange or exchange.status != ExchangeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Troca inválida ou já resolvida")

    # Validar regras rígidas
    result = validate_exchange(db, exchange.requester_assignment_id, data.target_assignment_id)
    if not result.passed:
        exchange.validation_passed = False
        exchange.validation_errors = result.errors_str()
        exchange.status = ExchangeStatus.INVALID
        db.commit()
        raise HTTPException(status_code=422, detail=f"Troca viola regras: {result.errors_str()}")

    # Executar troca de usuários nas atribuições
    req_assignment = db.get(Assignment, exchange.requester_assignment_id)
    tgt_assignment = db.get(Assignment, data.target_assignment_id)
    req_assignment.user_id, tgt_assignment.user_id = tgt_assignment.user_id, req_assignment.user_id

    exchange.target_id = current_user.id
    exchange.target_assignment_id = data.target_assignment_id
    exchange.status = ExchangeStatus.ACCEPTED
    exchange.validation_passed = True
    exchange.resolved_at = datetime.now(timezone.utc)

    db.commit()
    notify_exchange.delay(exchange.id, "accepted")
    return {"message": "Troca aceita e executada"}


@router.post("/{exchange_id}/reject")
def reject_exchange(
    exchange_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exchange = db.get(Exchange, exchange_id)
    if not exchange or exchange.target_id != current_user.id:
        raise HTTPException(status_code=400, detail="Troca não encontrada")
    exchange.status = ExchangeStatus.REJECTED
    exchange.resolved_at = datetime.now(timezone.utc)
    db.commit()
    notify_exchange.delay(exchange.id, "rejected")
    return {"message": "Troca recusada"}
