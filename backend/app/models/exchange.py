import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExchangeType(str, PyEnum):
    OPEN = "open"       # disponibiliza para todos elegíveis
    DIRECT = "direct"   # solicita troca para usuário específico


class ExchangeStatus(str, PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    INVALID = "invalid"   # bloqueada por regra operacional


class Exchange(Base):
    """Solicitação de troca de escala entre usuários."""
    __tablename__ = "exchanges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[ExchangeType] = mapped_column(Enum(ExchangeType), nullable=False)
    status: Mapped[ExchangeStatus] = mapped_column(Enum(ExchangeStatus), default=ExchangeStatus.PENDING, nullable=False)

    # Quem oferece
    requester_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    requester_assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assignments.id"), nullable=False)

    # Quem recebe (None = troca aberta)
    target_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    target_assignment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assignments.id"), nullable=True)

    # Validação automática
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    validation_errors: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id], back_populates="exchanges_as_requester")
    target: Mapped["User | None"] = relationship("User", foreign_keys=[target_id], back_populates="exchanges_as_target")
    requester_assignment: Mapped["Assignment"] = relationship("Assignment", foreign_keys=[requester_assignment_id])
    target_assignment: Mapped["Assignment | None"] = relationship("Assignment", foreign_keys=[target_assignment_id])
