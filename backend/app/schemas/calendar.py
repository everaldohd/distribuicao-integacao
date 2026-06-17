from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from app.models.operational_calendar import DayCategory, CalendarStatus


class CalendarCreate(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)


class DayCoverageOut(BaseModel):
    schedule_type_id: str
    schedule_type_name: str
    quantity: int
    is_overridden: bool
    override_reason: Optional[str]
    original_quantity: Optional[int]

    model_config = {"from_attributes": True}


class CalendarDayOut(BaseModel):
    id: str
    date: date
    category: DayCategory
    category_override_reason: Optional[str]
    coverages: List[DayCoverageOut]

    model_config = {"from_attributes": True}


class CalendarOut(BaseModel):
    id: str
    year: int
    month: int
    status: CalendarStatus
    days: List[CalendarDayOut]

    model_config = {"from_attributes": True}


class DayOverrideRequest(BaseModel):
    category: Optional[DayCategory] = None
    category_reason: Optional[str] = None
    # cobertura: dict {schedule_type_id: quantity}
    coverage_overrides: Optional[dict[str, int]] = None
    coverage_reason: Optional[str] = None


class CoverageTemplateSet(BaseModel):
    """Define o modelo de cobertura padrão para uma categoria de dia."""
    category: DayCategory
    coverages: dict[str, int]  # {schedule_type_id: quantity}
