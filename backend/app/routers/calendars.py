import calendar
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core import schedule_types as sched
from app.core.database import get_db
from app.models.audit import AuditAction
from app.models.operational_calendar import CalendarDay, CalendarStatus, DayCategory, DayCoverage, OperationalCalendar
from app.models.schedule_type import ScheduleType
from app.models.user import User
from app.routers.deps import get_current_manager, get_current_user
from app.schemas.calendar import (
    CalendarCreate,
    CalendarOut,
    CoverageTemplateSet,
    DayOverrideRequest,
    XlsxImportApply,
    XlsxParseResult,
)
from app.services import xlsx_import
from app.services.audit import log_action

router = APIRouter(prefix="/calendars", tags=["calendars"])


def _get_calendar_or_404(calendar_id: str, db: Session) -> OperationalCalendar:
    cal = db.get(OperationalCalendar, calendar_id)
    if not cal:
        raise HTTPException(status_code=404, detail="Calendário não encontrado")
    return cal


# Cobertura padrão por categoria de dia: {nome_tipo: quantidade}
COBERTURA_UTIL = {
    sched.PLANTAO_12H:   1,
    sched.RESERVA_MANHA: 1,
    sched.RESERVA_TARDE: 1,
    sched.RESERVA_12H:   0,
    sched.PATIO_MANHA:   1,
    sched.PATIO_TARDE:   1,
}
COBERTURA_FDS = {
    sched.PLANTAO_12H:   1,
    sched.RESERVA_MANHA: 0,
    sched.RESERVA_TARDE: 0,
    sched.RESERVA_12H:   1,
    sched.PATIO_MANHA:   0,
    sched.PATIO_TARDE:   0,
}


def _apply_default_coverage(cal: OperationalCalendar, db: Session) -> int:
    """Aplica a cobertura padrão (dia útil x fim de semana) a todos os dias do calendário.
    Retorna a quantidade de dias atualizados. Não faz commit."""
    tipos = {t.name: t for t in db.query(ScheduleType).filter(ScheduleType.is_active == True).all()}
    if not tipos:
        raise HTTPException(status_code=400, detail="Nenhum tipo de escala ativo cadastrado")

    dias_atualizados = 0
    for day in cal.days:
        template = COBERTURA_UTIL if day.category == DayCategory.WORKDAY else COBERTURA_FDS
        coberturas_existentes = {c.schedule_type_id: c for c in day.coverages}
        for nome, qtd in template.items():
            if nome not in tipos:
                continue
            tipo_id = tipos[nome].id
            if tipo_id in coberturas_existentes:
                coberturas_existentes[tipo_id].quantity = qtd
            else:
                day.coverages.append(DayCoverage(
                    id=str(uuid.uuid4()),
                    day_id=day.id,
                    schedule_type_id=tipo_id,
                    quantity=qtd,
                ))
        dias_atualizados += 1
    return dias_atualizados


@router.get("/", response_model=list[CalendarOut], dependencies=[Depends(get_current_user)])
def list_calendars(db: Session = Depends(get_db)):
    return db.query(OperationalCalendar).order_by(OperationalCalendar.year.desc(), OperationalCalendar.month.desc()).all()


@router.post("/", response_model=CalendarOut, status_code=status.HTTP_201_CREATED)
def create_calendar(
    data: CalendarCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    existing = db.query(OperationalCalendar).filter(
        OperationalCalendar.year == data.year, OperationalCalendar.month == data.month
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Calendário já existe para este mês")

    cal = OperationalCalendar(
        id=str(uuid.uuid4()),
        year=data.year,
        month=data.month,
        created_by_id=manager.id,
    )
    db.add(cal)
    db.flush()

    # Gerar dias automaticamente com classificação padrão
    _, num_days = calendar.monthrange(data.year, data.month)
    for day_num in range(1, num_days + 1):
        d = date(data.year, data.month, day_num)
        weekday = d.weekday()  # 0=Mon, 6=Sun
        if weekday < 5:
            category = DayCategory.WORKDAY
        else:
            category = DayCategory.WEEKEND
        cal_day = CalendarDay(id=str(uuid.uuid4()), calendar_id=cal.id, date=d, category=category)
        db.add(cal_day)

    db.flush()
    db.refresh(cal)

    # Aplica cobertura padrão automaticamente e abre o calendário
    _apply_default_coverage(cal, db)
    cal.status = CalendarStatus.OPEN

    db.commit()
    db.refresh(cal)
    log_action(db, manager.id, AuditAction.CREATE, "OperationalCalendar", cal.id, description=f"Calendário {data.year}/{data.month:02d} criado com cobertura padrão")
    return cal


@router.get("/{calendar_id}", response_model=CalendarOut, dependencies=[Depends(get_current_user)])
def get_calendar(calendar_id: str, db: Session = Depends(get_db)):
    return _get_calendar_or_404(calendar_id, db)


@router.post("/{calendar_id}/coverage-template", dependencies=[Depends(get_current_manager)])
def set_coverage_template(
    calendar_id: str,
    data: CoverageTemplateSet,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Aplica modelo de cobertura padrão a todos os dias de uma categoria."""
    cal = _get_calendar_or_404(calendar_id, db)
    days = [d for d in cal.days if d.category == data.category]
    for day in days:
        # Remove coberturas existentes não-overridden
        existing = {c.schedule_type_id: c for c in day.coverages if not c.is_overridden}
        for type_id, qty in data.coverages.items():
            if type_id in existing:
                existing[type_id].quantity = qty
            else:
                day.coverages.append(DayCoverage(
                    id=str(uuid.uuid4()), day_id=day.id, schedule_type_id=type_id, quantity=qty
                ))
    db.commit()
    return {"message": f"Modelo aplicado a {len(days)} dias do tipo {data.category}"}


@router.post("/{calendar_id}/apply-default-template", dependencies=[Depends(get_current_manager)])
def apply_default_template(
    calendar_id: str,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Aplica template padrão por categoria de dia:
    - Dia útil:      1× Plantão 12h, 1× Reserva Manhã, 1× Reserva Tarde, 1× Pátio Manhã, 1× Pátio Tarde
    - Fim de semana: 1× Plantão 12h, 1× Reserva 12h
    - Feriado:       mesmo que fim de semana
    """
    cal = _get_calendar_or_404(calendar_id, db)
    dias_atualizados = _apply_default_coverage(cal, db)
    cal.status = CalendarStatus.OPEN
    db.commit()
    log_action(db, manager.id, AuditAction.UPDATE, "OperationalCalendar", cal.id,
               description=f"Template padrão aplicado a {dias_atualizados} dias")
    return {"message": f"Template aplicado a {dias_atualizados} dias. Status: OPEN"}


@router.post("/parse-xlsx", response_model=XlsxParseResult, dependencies=[Depends(get_current_manager)])
async def parse_xlsx(
    year: int = Form(...),
    month: int = Form(...),
    file: UploadFile = File(...),
    sheet_name: str | None = Form(None),
):
    """Lê a planilha macro e devolve a grade digerida + seções encontradas.
    Não altera nada — apenas alimenta a tela de importação."""
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")
    content = await file.read()
    try:
        return xlsx_import.parse_workbook(content, year, month, sheet_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # openpyxl pode falhar em arquivos corrompidos
        raise HTTPException(status_code=400, detail=f"Não foi possível ler a planilha: {e}") from e


@router.post("/preview-xlsx-coverage", dependencies=[Depends(get_current_manager)])
def preview_xlsx_coverage(data: XlsxImportApply):
    """Prévia da cobertura (totais por tipo) para uma seleção de seções, sem gravar.
    Usa a MESMA regra do import (fonte única no backend) — o front não replica a regra."""
    grid = [c.model_dump() for c in data.grid]
    coverage = xlsx_import.coverage_from_grid(grid, data.selected_sections)
    totals = {t: 0 for t in xlsx_import.ALL_TYPES}
    for tipo_qtd in coverage.values():
        for tname, qtd in tipo_qtd.items():
            totals[tname] += qtd
    return {"totals": totals, "total_vagas": sum(totals.values())}


@router.post("/{calendar_id}/import-xlsx", dependencies=[Depends(get_current_manager)])
def import_xlsx(
    calendar_id: str,
    data: XlsxImportApply,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Aplica ao calendário a cobertura derivada da planilha, para as seções escolhidas.
    Sobrescreve a cobertura de todos os dias com os 6 tipos (inclusive zeros)."""
    cal = _get_calendar_or_404(calendar_id, db)
    tipos = {t.name: t for t in db.query(ScheduleType).filter(ScheduleType.is_active == True).all()}
    faltando = [t for t in xlsx_import.ALL_TYPES if t not in tipos]
    if faltando:
        raise HTTPException(status_code=400, detail=f"Tipos de escala ausentes no sistema: {', '.join(faltando)}")

    grid = [c.model_dump() for c in data.grid]
    coverage = xlsx_import.coverage_from_grid(grid, data.selected_sections)

    days_by_num = {d.date.day: d for d in cal.days}
    dias_atualizados = 0
    total_vagas = 0
    for daynum, tipo_qtd in coverage.items():
        day = days_by_num.get(daynum)
        if not day:
            continue
        existentes = {c.schedule_type_id: c for c in day.coverages}
        for tname, qtd in tipo_qtd.items():
            tipo = tipos.get(tname)
            if not tipo:
                continue
            total_vagas += qtd
            if tipo.id in existentes:
                cov = existentes[tipo.id]
                cov.quantity = qtd
                cov.is_overridden = False
                cov.original_quantity = None
                cov.override_reason = None
            else:
                day.coverages.append(DayCoverage(
                    id=str(uuid.uuid4()), day_id=day.id, schedule_type_id=tipo.id, quantity=qtd,
                ))
        dias_atualizados += 1

    cal.status = CalendarStatus.OPEN
    db.commit()
    log_action(db, manager.id, AuditAction.UPDATE, "OperationalCalendar", cal.id,
               description=f"Cobertura importada da planilha ({len(data.selected_sections)} seções) → {dias_atualizados} dias")
    return {
        "message": f"Cobertura importada para {dias_atualizados} dias.",
        "dias_atualizados": dias_atualizados,
        "total_vagas": total_vagas,
        "secoes": data.selected_sections,
    }


@router.patch("/{calendar_id}/days/{day_id}")
def override_day(
    calendar_id: str,
    day_id: str,
    data: DayOverrideRequest,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    cal = _get_calendar_or_404(calendar_id, db)
    day = next((d for d in cal.days if d.id == day_id), None)
    if not day:
        raise HTTPException(status_code=404, detail="Dia não encontrado")

    previous = {"category": day.category, "coverages": {c.schedule_type_id: c.quantity for c in day.coverages}}

    if data.category:
        day.category = data.category
        day.category_override_reason = data.category_reason

    if data.coverage_overrides:
        existing = {c.schedule_type_id: c for c in day.coverages}
        for type_id, qty in data.coverage_overrides.items():
            if type_id in existing:
                cov = existing[type_id]
                if not cov.is_overridden:
                    cov.original_quantity = cov.quantity
                cov.quantity = qty
                cov.is_overridden = True
                cov.override_reason = data.coverage_reason
            else:
                day.coverages.append(DayCoverage(
                    id=str(uuid.uuid4()),
                    day_id=day.id,
                    schedule_type_id=type_id,
                    quantity=qty,
                    is_overridden=True,
                    override_reason=data.coverage_reason,
                ))

    db.commit()
    log_action(db, manager.id, AuditAction.UPDATE, "CalendarDay", day_id, previous_value=previous, description=data.coverage_reason or data.category_reason)
    return {"message": "Dia atualizado"}
