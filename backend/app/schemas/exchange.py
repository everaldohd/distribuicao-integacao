from datetime import date, datetime

from pydantic import BaseModel


class OfferCreate(BaseModel):
    """Coloca um turno próprio à disposição no mural (troca aberta)."""
    requester_assignment_id: str
    notes: str | None = None


class DirectCreate(BaseModel):
    """Solicita troca direta: meu turno (requester) pelo turno de um colega (target)."""
    requester_assignment_id: str
    target_assignment_id: str
    notes: str | None = None


class ProposeRequest(BaseModel):
    """Colega propõe um turno seu (mesmo grupo) para uma oferta aberta."""
    target_assignment_id: str


class ExchangeOut(BaseModel):
    id: str
    type: str
    status: str
    # Lado solicitante
    requester_id: str
    requester_name: str
    requester_date: date | None
    requester_type: str | None
    group: str | None
    # Lado colega (pode estar vazio enquanto a oferta não tem proposta)
    target_id: str | None
    target_name: str | None
    target_date: date | None
    target_type: str | None
    # Meta
    validation_passed: bool | None
    validation_errors: str | None
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None
