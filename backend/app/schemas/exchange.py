from datetime import datetime

from pydantic import BaseModel

from app.models.exchange import ExchangeStatus, ExchangeType


class ExchangeCreate(BaseModel):
    type: ExchangeType
    requester_assignment_id: str
    target_id: str | None = None
    target_assignment_id: str | None = None
    notes: str | None = None


class ExchangeOut(BaseModel):
    id: str
    type: ExchangeType
    status: ExchangeStatus
    requester_id: str
    requester_name: str
    requester_assignment_id: str
    target_id: str | None
    target_name: str | None
    target_assignment_id: str | None
    validation_passed: bool | None
    validation_errors: str | None
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class ExchangeAccept(BaseModel):
    target_assignment_id: str
