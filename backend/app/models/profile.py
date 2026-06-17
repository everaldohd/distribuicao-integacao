import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Profile(Base):
    """Perfil de distribuição mensal: define cotas de cada tipo de escala."""
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rules: Mapped[list["ProfileRule"]] = relationship("ProfileRule", back_populates="profile", cascade="all, delete-orphan")
    exceptions: Mapped[list["UserProfileException"]] = relationship("UserProfileException", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Profile {self.name}>"


class ProfileRule(Base):
    """Cota de um tipo de escala dentro de um perfil."""
    __tablename__ = "profile_rules"
    __table_args__ = (UniqueConstraint("profile_id", "schedule_type_id", name="uq_profile_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    schedule_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedule_types.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped["Profile"] = relationship("Profile", back_populates="rules")
    schedule_type: Mapped["ScheduleType"] = relationship("ScheduleType", back_populates="profile_rules")


class UserProfileException(Base):
    """Sobrescreve a cota de um tipo de escala para um usuário específico no mês."""
    __tablename__ = "user_profile_exceptions"
    __table_args__ = (UniqueConstraint("user_id", "profile_id", "schedule_type_id", "year", "month", name="uq_exception"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    schedule_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedule_types.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="profile_exceptions")
    profile: Mapped["Profile"] = relationship("Profile", back_populates="exceptions")
    schedule_type: Mapped["ScheduleType"] = relationship("ScheduleType")
