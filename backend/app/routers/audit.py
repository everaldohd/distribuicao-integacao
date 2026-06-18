"""
Consulta da trilha de auditoria (gestor).
Lista as ações registradas via `log_action` — quem fez, o quê, quando,
com valores anterior/novo e descrição — para transparência total.
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.user import User
from app.routers.deps import get_current_manager

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEntryOut(BaseModel):
    id: str
    performed_by_id: str | None
    performed_by_name: str | None
    action: AuditAction
    entity_type: str
    entity_id: str | None
    previous_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    description: str | None
    created_at: datetime


@router.get("/", response_model=list[AuditEntryOut], dependencies=[Depends(get_current_manager)])
def list_audit(
    db: Session = Depends(get_db),
    action: AuditAction | None = None,
    entity_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista os registros de auditoria do mais recente ao mais antigo, com filtros opcionais."""
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    rows = q.offset(offset).limit(limit).all()

    # Resolve o nome de quem executou (uma consulta só)
    ids = {r.performed_by_id for r in rows if r.performed_by_id}
    nomes = {u.id: u.name for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}

    return [
        AuditEntryOut(
            id=r.id,
            performed_by_id=r.performed_by_id,
            performed_by_name=nomes.get(r.performed_by_id, "Sistema" if r.performed_by_id is None else "—"),
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            previous_value=r.previous_value,
            new_value=r.new_value,
            description=r.description,
            created_at=r.created_at,
        )
        for r in rows
    ]
