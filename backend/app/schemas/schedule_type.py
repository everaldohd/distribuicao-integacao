
from pydantic import BaseModel, Field


class ScheduleTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    requires_rest_day_after: bool = False
    display_order: int = 0


class ScheduleTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    requires_rest_day_after: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None


class ScheduleTypeOut(BaseModel):
    id: str
    name: str
    description: str | None
    requires_rest_day_after: bool
    is_active: bool
    display_order: int

    model_config = {"from_attributes": True}
