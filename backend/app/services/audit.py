import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog


def log_action(
    db: Session,
    performed_by_id: str | None,
    action: AuditAction,
    entity_type: str,
    entity_id: str | None = None,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    description: str | None = None,
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
