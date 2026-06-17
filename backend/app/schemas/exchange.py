from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.exchange import ExchangeType, ExchangeStatus


class ExchangeCreate(BaseModel):
    type: ExchangeType
    requester_assignment_id: str
    target_id: Optional[str] = None
    target_assignment_id: Optional[str] = None
    notes: Optional[str] = None


class ExchangeOut(BaseModel):
    id: str
    type: ExchangeType
    status: ExchangeStatus
    requester_id: str
    requester_name: str
    requester_assignment_id: str
    target_id: Optional[str]
    target_name: Optional[str]
    target_assignment_id: Optional[str]
    validation_passed: Optional[bool]
    validation_errors: Optional[str]
    notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ExchangeAccept(BaseModel):
    target_assignment_id: str
