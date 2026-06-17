from pydantic import BaseModel, Field
from typing import Optional


class ScheduleTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    requires_rest_day_after: bool = False
    display_order: int = 0


class ScheduleTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    requires_rest_day_after: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class ScheduleTypeOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    requires_rest_day_after: bool
    is_active: bool
    display_order: int

    model_config = {"from_attributes": True}
