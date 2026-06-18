import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExchangeType(str, PyEnum):
    OPEN = "open"       # turno colocado à disposição no mural
    DIRECT = "direct"   # solicitação direta a um colega específico


class ExchangeStatus(str, PyEnum):
    OPEN = "open"                       # mural: aguardando um colega propor turno
    AWAITING_TARGET = "awaiting_target" # direta: aguardando o colega aceitar
    AWAITING_MANAGER = "awaiting_manager"  # peritos concordaram, aguardando o gestor
    APPROVED = "approved"               # gestor aprovou e a troca foi executada
    REJECTED = "rejected"               # recusada pelo colega ou pelo gestor
    CANCELLED = "cancelled"             # cancelada pelo solicitante
    EXPIRED = "expired"                 # entrou na janela de antecedência / turno passou


class Exchange(Base):
    """Troca de escala 1:1 (mesmo grupo) entre peritos, com aprovação do gestor.

    `status` e `type` são guardados como texto (valores dos enums acima) para
    evitar tipos ENUM rígidos no Postgres.
    """
    __tablename__ = "exchanges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ExchangeStatus.OPEN.value, nullable=False)

    # Quem oferece o turno
    requester_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    requester_assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assignments.id"), nullable=False)

    # Colega (None enquanto a oferta aberta não tem proposta)
    target_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    target_assignment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assignments.id"), nullable=True)

    # Validação automática (regras rígidas)
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    validation_errors: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aprovação do gestor
    approved_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id], back_populates="exchanges_as_requester")
    target: Mapped["User | None"] = relationship("User", foreign_keys=[target_id], back_populates="exchanges_as_target")
    requester_assignment: Mapped["Assignment"] = relationship("Assignment", foreign_keys=[requester_assignment_id])
    target_assignment: Mapped["Assignment | None"] = relationship("Assignment", foreign_keys=[target_assignment_id])
