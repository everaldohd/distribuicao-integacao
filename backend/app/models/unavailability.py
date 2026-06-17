import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Date, ForeignKey, DateTime, func, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UnavailabilityType(str, PyEnum):
    VACATION = "vacation"
    BONUS_LEAVE = "bonus_leave"
    LICENSE = "license"


class Unavailability(Base):
    """Período em que o usuário não pode ser escalado (férias, abono, licença)."""
    __tablename__ = "unavailabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[UnavailabilityType] = mapped_column(Enum(UnavailabilityType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="unavailabilities")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
