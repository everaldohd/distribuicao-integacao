import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Date, ForeignKey, DateTime, func, Enum, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ScheduleStatus(str, PyEnum):
    DRAFT = "draft"
    SIMULATED = "simulated"
    GENERATED = "generated"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Schedule(Base):
    """Versão de escala para um mês. Imutável após publicação (nova versão é criada)."""
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    calendar_id: Mapped[str] = mapped_column(String(36), ForeignKey("operational_calendars.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(Enum(ScheduleStatus), default=ScheduleStatus.DRAFT, nullable=False)
    # Identificação rápida
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    # Dados da simulação / geração
    simulation_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    calendar: Mapped["OperationalCalendar"] = relationship("OperationalCalendar", back_populates="schedules")
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="schedule", cascade="all, delete-orphan")
    solver_audit: Mapped["SolverAudit | None"] = relationship("SolverAudit", back_populates="schedule", uselist=False)

    def __repr__(self) -> str:
        return f"<Schedule {self.year}/{self.month:02d} v{self.version} [{self.status}]>"


class Assignment(Base):
    """Atribuição de escala: usuário + tipo + data dentro de uma escala."""
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schedule_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)  # None = buraco
    schedule_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedule_types.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_gap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # True = buraco na escala
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # True = preenchido manualmente
    # Explicabilidade: flags indicando por que o usuário foi escolhido
    explanation_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="assignments")
    user: Mapped["User | None"] = relationship("User", back_populates="assignments")
    schedule_type: Mapped["ScheduleType"] = relationship("ScheduleType", back_populates="assignments")
