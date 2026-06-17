import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Date, ForeignKey, DateTime, func, UniqueConstraint, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DayCategory(str, PyEnum):
    WORKDAY = "workday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


class CalendarStatus(str, PyEnum):
    DRAFT = "draft"
    OPEN = "open"       # preferências abertas
    LOCKED = "locked"   # geração em andamento ou publicada


class OperationalCalendar(Base):
    """Calendário mensal configurado pelo gestor."""
    __tablename__ = "operational_calendars"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_calendar_year_month"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CalendarStatus] = mapped_column(Enum(CalendarStatus), default=CalendarStatus.DRAFT, nullable=False)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    days: Mapped[list["CalendarDay"]] = relationship("CalendarDay", back_populates="calendar", cascade="all, delete-orphan", order_by="CalendarDay.date")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="calendar")

    def __repr__(self) -> str:
        return f"<OperationalCalendar {self.year}/{self.month:02d}>"


class CalendarDay(Base):
    """Um dia dentro do calendário mensal com sua categoria e cobertura."""
    __tablename__ = "calendar_days"
    __table_args__ = (UniqueConstraint("calendar_id", "date", name="uq_calendar_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    calendar_id: Mapped[str] = mapped_column(String(36), ForeignKey("operational_calendars.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category: Mapped[DayCategory] = mapped_column(Enum(DayCategory), nullable=False)
    category_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    calendar: Mapped["OperationalCalendar"] = relationship("OperationalCalendar", back_populates="days")
    coverages: Mapped[list["DayCoverage"]] = relationship("DayCoverage", back_populates="day", cascade="all, delete-orphan")


class DayCoverage(Base):
    """Quantas vagas de cada tipo de escala existem em um dia específico."""
    __tablename__ = "day_coverages"
    __table_args__ = (UniqueConstraint("day_id", "schedule_type_id", name="uq_day_type_coverage"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    day_id: Mapped[str] = mapped_column(String(36), ForeignKey("calendar_days.id", ondelete="CASCADE"), nullable=False)
    schedule_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("schedule_types.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Se foi alterado manualmente pelo gestor
    is_overridden: Mapped[bool] = mapped_column(default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    day: Mapped["CalendarDay"] = relationship("CalendarDay", back_populates="coverages")
    schedule_type: Mapped["ScheduleType"] = relationship("ScheduleType", back_populates="day_coverages")
