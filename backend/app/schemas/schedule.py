from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from app.models.schedule import ScheduleStatus


class AssignmentOut(BaseModel):
    id: str
    date: date
    schedule_type_id: str
    schedule_type_name: str
    user_id: Optional[str]
    user_name: Optional[str]
    is_gap: bool
    is_manual: bool
    explanation_flags: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class ScheduleOut(BaseModel):
    id: str
    year: int
    month: int
    version: int
    status: ScheduleStatus
    simulation_data: Optional[Dict[str, Any]]
    published_at: Optional[datetime]
    created_at: datetime
    assignments: List[AssignmentOut] = []

    model_config = {"from_attributes": True}


class ScheduleSummary(BaseModel):
    id: str
    year: int
    month: int
    version: int
    status: ScheduleStatus
    published_at: Optional[datetime]
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
    notes: List[str]
