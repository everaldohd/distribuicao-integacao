from datetime import date

from pydantic import BaseModel, Field

from app.models.operational_calendar import CalendarStatus, DayCategory


class CalendarCreate(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)


class DayCoverageOut(BaseModel):
    schedule_type_id: str
    schedule_type_name: str
    quantity: int
    is_overridden: bool
    override_reason: str | None
    original_quantity: int | None

    model_config = {"from_attributes": True}


class CalendarDayOut(BaseModel):
    id: str
    date: date
    category: DayCategory
    category_override_reason: str | None
    coverages: list[DayCoverageOut]

    model_config = {"from_attributes": True}


class CalendarOut(BaseModel):
    id: str
    year: int
    month: int
    status: CalendarStatus
    days: list[CalendarDayOut]

    model_config = {"from_attributes": True}


class DayOverrideRequest(BaseModel):
    category: DayCategory | None = None
    category_reason: str | None = None
    # cobertura: dict {schedule_type_id: quantity}
    coverage_overrides: dict[str, int] | None = None
    coverage_reason: str | None = None


class CoverageTemplateSet(BaseModel):
    """Define o modelo de cobertura padrão para uma categoria de dia."""
    category: DayCategory
    coverages: dict[str, int]  # {schedule_type_id: quantity}


# --- Importação da planilha macro ------------------------------------------

class XlsxDayCell(BaseModel):
    """Uma célula por dia já digerida a partir da planilha macro."""
    day: int
    weekend: bool
    plantao: list[str] = []
    rm: str = ""
    rt: str = ""
    pim: str = ""
    pit: str = ""


class XlsxParseResult(BaseModel):
    sheet_name: str
    available_sheets: list[str]
    sections_found: list[str]
    default_selected: list[str]
    types: list[str]
    grid: list[XlsxDayCell]


class XlsxImportApply(BaseModel):
    """Aplica a cobertura derivada da planilha ao calendário, para as seções escolhidas."""
    selected_sections: list[str]
    grid: list[XlsxDayCell]
