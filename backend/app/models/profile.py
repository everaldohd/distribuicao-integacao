import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Profile(Base):
    """Perfil de distribuição: define a cota MÁXIMA por grupo de escala (Plantão/Reserva/Pátio)."""
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # is_default: aplicado a peritos sem perfil. is_custom: limites vêm do próprio perito.
    # is_system: perfis internos que não podem ser excluídos.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    group_limits: Mapped[list["ProfileGroupLimit"]] = relationship("ProfileGroupLimit", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Profile {self.name}>"


class ProfileGroupLimit(Base):
    """Cota máxima de um grupo de escala (Plantão/Reserva/Pátio) dentro de um perfil."""
    __tablename__ = "profile_group_limits"
    __table_args__ = (UniqueConstraint("profile_id", "group_name", name="uq_profile_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped["Profile"] = relationship("Profile", back_populates="group_limits")


class UserGroupLimit(Base):
    """Cota máxima por grupo individual de um perito (usado no perfil Personalizado)."""
    __tablename__ = "user_group_limits"
    __table_args__ = (UniqueConstraint("user_id", "group_name", name="uq_user_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
