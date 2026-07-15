import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    # Matrícula do servidor — usada para identificação na integração com o NEO (SSO)
    matricula: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Força a troca de senha no primeiro login (novos usuários e pós-reset).
    # Vira False quando o próprio usuário troca a senha em PUT /users/me/password.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # FK to Profile — SET NULL: excluir um perfil deixa o usuário "sem perfil"
    # (estado válido e visível na UI), em vez de órfão apontando para id inexistente.
    profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="SET NULL", name="fk_users_profile_id_profiles"),
        nullable=True,
        index=True,
    )

    # Relationships
    eligibilities: Mapped[list["Eligibility"]] = relationship("Eligibility", back_populates="user", cascade="all, delete-orphan")
    unavailabilities: Mapped[list["Unavailability"]] = relationship("Unavailability", foreign_keys="[Unavailability.user_id]", back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[list["UserPreference"]] = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="user")
    historical_balances: Mapped[list["HistoricalBalance"]] = relationship("HistoricalBalance", back_populates="user", cascade="all, delete-orphan")
    exchanges_as_requester: Mapped[list["Exchange"]] = relationship("Exchange", foreign_keys="Exchange.requester_id", back_populates="requester")
    exchanges_as_target: Mapped[list["Exchange"]] = relationship("Exchange", foreign_keys="Exchange.target_id", back_populates="target")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
