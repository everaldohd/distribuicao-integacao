import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ScheduleType(Base):
    """Tipo de escala configurável (Plantão 12h, Reserva Manhã, etc.)."""
    __tablename__ = "schedule_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Plantão 12h requer interstício obrigatório no dia seguinte
    requires_rest_day_after: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Grupo de cota (Plantão / Reserva / Pátio) e peso dentro do grupo
    # (Reserva 12h conta como 2 reservas, por isso group_weight = 2)
    group_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    group_weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    eligibilities: Mapped[list["Eligibility"]] = relationship("Eligibility", back_populates="schedule_type")
    profile_rules: Mapped[list["ProfileRule"]] = relationship("ProfileRule", back_populates="schedule_type")
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="schedule_type")
    day_coverages: Mapped[list["DayCoverage"]] = relationship("DayCoverage", back_populates="schedule_type")

    def __repr__(self) -> str:
        return f"<ScheduleType {self.name}>"
