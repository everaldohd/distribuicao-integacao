from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.models.schedule import ScheduleStatus


class AssignmentOut(BaseModel):
    id: str
    date: date
    schedule_type_id: str
    schedule_type_name: str
    user_id: str | None
    user_name: str | None
    is_gap: bool
    is_manual: bool
    explanation_flags: dict[str, Any] | None

    model_config = {"from_attributes": True}


class ScheduleOut(BaseModel):
    id: str
    year: int
    month: int
    version: int
    status: ScheduleStatus
    simulation_data: dict[str, Any] | None
    published_at: datetime | None
    created_at: datetime
    assignments: list[AssignmentOut] = []

    model_config = {"from_attributes": True}


class ScheduleSummary(BaseModel):
    id: str
    year: int
    month: int
    version: int
    status: ScheduleStatus
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ManualFillRequest(BaseModel):
    user_id: str
    date: date
    schedule_type_id: str


class SimulationResult(BaseModel):
    total_slots: int
    eligible_users: int
    estimated_preferences_fulfilled_pct: float
    estimated_avoided_assigned: int
    expected_gaps: int
    notes: list[str]
