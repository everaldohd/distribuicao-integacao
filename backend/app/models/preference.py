import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Date, ForeignKey, DateTime, func, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PreferenceType(str, PyEnum):
    DESIRED = "desired"
    AVOID = "avoid"


class UserPreference(Base):
    """Preferências de datas informadas pelo usuário antes da geração da escala."""
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", "year", "month", "date", "type", name="uq_user_preference"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[PreferenceType] = mapped_column(Enum(PreferenceType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="preferences")
