from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.schedule import Schedule, Assignment, ScheduleStatus
from app.models.user import User
from app.schemas.schedule import ScheduleOut, ScheduleSummary, ManualFillRequest, SimulationResult
from app.routers.deps import get_current_manager, get_current_user
from app.services.audit import log_action
from app.models.audit import AuditAction
from app.workers.tasks import run_solver_task
import uuid

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=List[ScheduleSummary], dependencies=[Depends(get_current_user)])
def list_schedules(db: Session = Depends(get_db)):
    return db.query(Schedule).order_by(Schedule.year.desc(), Schedule.month.desc(), Schedule.version.desc()).all()


@router.get("/{schedule_id}", response_model=ScheduleOut, dependencies=[Depends(get_current_user)])
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    return s


@router.post("/simulate/{calendar_id}", response_model=SimulationResult)
def simulate(
    calendar_id: str,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Executa simulação síncrona rápida (sem gerar atribuições)."""
    from app.services.optimizer.solver import ScheduleSolver
    solver = ScheduleSolver(db, calendar_id, manager.id, simulate_only=True)
    return solver.simulate()


@router.post("/generate/{calendar_id}", status_code=status.HTTP_202_ACCEPTED)
def generate(
    calendar_id: str,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Enfileira geração assíncrona da escala via Celery."""
    # Cria Schedule em rascunho para rastrear o job
    from app.models.operational_calendar import OperationalCalendar
    cal = db.get(OperationalCalendar, calendar_id)
    if not cal:
        raise HTTPException(status_code=404, detail="Calendário não encontrado")

    schedule = Schedule(
        id=str(uuid.uuid4()),
        calendar_id=calendar_id,
        year=cal.year,
        month=cal.month,
        version=_next_version(db, cal.year, cal.month),
        status=ScheduleStatus.DRAFT,
        created_by_id=manager.id,
    )
    db.add(schedule)
    db.commit()

    run_solver_task.delay(schedule.id, manager.id)
    log_action(db, manager.id, AuditAction.GENERATE, "Schedule", schedule.id, description="Geração iniciada")
    return {"schedule_id": schedule.id, "message": "Geração enfileirada"}


@router.post("/{schedule_id}/publish")
def publish(
    schedule_id: str,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    from datetime import datetime
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    if s.status != ScheduleStatus.GENERATED:
        raise HTTPException(status_code=400, detail="Apenas escalas geradas podem ser publicadas")

    s.status = ScheduleStatus.PUBLISHED
    s.published_at = datetime.utcnow()
    s.published_by_id = manager.id
    db.commit()

    # Disparar e-mails e calcular saldo em background
    from app.workers.tasks import post_publish_tasks
    post_publish_tasks.delay(schedule_id)

    log_action(db, manager.id, AuditAction.PUBLISH, "Schedule", schedule_id)
    return {"message": "Escala publicada com sucesso"}


@router.post("/{schedule_id}/manual-fill")
def manual_fill(
    schedule_id: str,
    data: ManualFillRequest,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Preenche manualmente um buraco na escala."""
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    if s.status == ScheduleStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Escala arquivada não pode ser alterada")

    # Verificar se existe gap nessa data/tipo
    gap = db.query(Assignment).filter(
        Assignment.schedule_id == schedule_id,
        Assignment.date == data.date,
        Assignment.schedule_type_id == data.schedule_type_id,
        Assignment.is_gap == True,
    ).first()

    if gap:
        gap.user_id = data.user_id
        gap.is_gap = False
        gap.is_manual = True
        gap.explanation_flags = {"manual": True}
    else:
        # Adicionar nova atribuição manual
        a = Assignment(
            id=str(uuid.uuid4()),
            schedule_id=schedule_id,
            user_id=data.user_id,
            schedule_type_id=data.schedule_type_id,
            date=data.date,
            is_gap=False,
            is_manual=True,
            explanation_flags={"manual": True},
        )
        db.add(a)

    db.commit()
    log_action(db, manager.id, AuditAction.MANUAL_FILL, "Assignment", schedule_id,
               description=f"Preenchimento manual: {data.user_id} em {data.date}")
    return {"message": "Turno preenchido manualmente"}


def _next_version(db: Session, year: int, month: int) -> int:
    last = db.query(Schedule).filter(
        Schedule.year == year, Schedule.month == month
    ).order_by(Schedule.version.desc()).first()
    return (last.version + 1) if last else 1
