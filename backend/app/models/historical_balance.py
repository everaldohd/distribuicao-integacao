import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HistoricalBalance(Base):
    """Saldo histórico acumulado de compensação por usuário."""
    __tablename__ = "historical_balances"
    __table_args__ = (UniqueConstraint("user_id", "year", "month", name="uq_balance_user_month"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    # Pontos ganhos/perdidos neste mês
    delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Saldo acumulado após este mês (após normalização)
    cumulative_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Detalhamento dos eventos
    events_count_no_schedule: Mapped[int] = mapped_column(Integer, default=0)
    events_count_desired_fulfilled: Mapped[int] = mapped_column(Integer, default=0)
    events_count_avoided_assigned: Mapped[int] = mapped_column(Integer, default=0)
    events_count_common: Mapped[int] = mapped_column(Integer, default=0)
    # Fator de normalização aplicado ao fechar o mês
    normalization_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="historical_balances")


class BalanceConfig(Base):
    """Valores configuráveis para o saldo de compensação (singleton)."""
    __tablename__ = "balance_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    month_no_schedule: Mapped[int] = mapped_column(Integer, default=-10, nullable=False)
    desired_date_fulfilled: Mapped[int] = mapped_column(Integer, default=-5, nullable=False)
    common_schedule: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avoided_date_assigned: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    # Fator multiplicador do limite de dias de preferência (limite = cota_grupo × fator)
    preference_factor: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    updated_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
