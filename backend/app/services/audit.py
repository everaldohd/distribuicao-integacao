from sqlalchemy.orm import Session
from app.models.audit import AuditLog, AuditAction
from typing import Optional
import uuid


def log_action(
    db: Session,
    performed_by_id: Optional[str],
    action: AuditAction,
    entity_type: str,
    entity_id: Optional[str] = None,
    previous_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    description: Optional[str] = None,
):
    log = AuditLog(
        id=str(uuid.uuid4()),
        performed_by_id=performed_by_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
        description=description,
    )
    db.add(log)
    db.commit()
