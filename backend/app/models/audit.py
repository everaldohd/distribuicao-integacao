import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, ForeignKey, DateTime, func, Enum, Text, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AuditAction(str, PyEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PUBLISH = "publish"
    GENERATE = "generate"
    SIMULATE = "simulate"
    EXCHANGE = "exchange"
    MANUAL_FILL = "manual_fill"


class AuditLog(Base):
    """Registro de todas as ações operacionais relevantes."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    performed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # ex: "Schedule", "Assignment", "Profile"
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    previous_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    performed_by: Mapped["User | None"] = relationship("User", foreign_keys=[performed_by_id])


class SolverAudit(Base):
    """Registro matemático da execução do solver CP-SAT."""
    __tablename__ = "solver_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schedule_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Inputs
    eligible_users_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    preferences_desired_count: Mapped[int] = mapped_column(Integer, default=0)
    preferences_avoid_count: Mapped[int] = mapped_column(Integer, default=0)
    # Outputs
    preferences_fulfilled_count: Mapped[int] = mapped_column(Integer, default=0)
    avoided_dates_assigned_count: Mapped[int] = mapped_column(Integer, default=0)
    gaps_count: Mapped[int] = mapped_column(Integer, default=0)
    # Solver metadata
    solver_status: Mapped[str] = mapped_column(String(50), nullable=False)  # OPTIMAL, FEASIBLE, INFEASIBLE
    objective_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full solver parameters snapshot
    solver_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="solver_audit")
