import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Eligibility(Base):
    """Define se um usuário é elegível para um tipo de escala."""
    __tablename__ = "eligibilities"
    __table_args__ = (UniqueConstraint("user_id", "schedule_type_id", name="uq_user_type_eligibility"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedule_types.id"), nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="eligibilities")
    schedule_type: Mapped["ScheduleType"] = relationship("ScheduleType", back_populates="eligibilities")
