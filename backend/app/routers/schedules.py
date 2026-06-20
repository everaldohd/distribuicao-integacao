import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.audit import AuditAction
from app.models.schedule import Assignment, Schedule, ScheduleStatus
from app.models.user import User
from app.routers.deps import get_current_manager, get_current_user
from app.schemas.schedule import ManualFillRequest, ScheduleOut, ScheduleSummary, SimulationResult
from app.services.audit import log_action
from app.workers.tasks import run_solver_task

logger = get_logger(__name__)
router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[ScheduleSummary], dependencies=[Depends(get_current_user)])
def list_schedules(db: Session = Depends(get_db)):
    return db.query(Schedule).order_by(Schedule.year.desc(), Schedule.month.desc(), Schedule.version.desc()).all()


@router.get("/published", response_model=ScheduleOut, dependencies=[Depends(get_current_user)])
def get_published(year: int, month: int, db: Session = Depends(get_db)):
    """Escala publicada do mês (pública a qualquer perito logado) — calendário geral.
    Retorna a versão publicada mais recente do período."""
    s = db.query(Schedule).filter(
        Schedule.year == year, Schedule.month == month,
        Schedule.status == ScheduleStatus.PUBLISHED,
    ).order_by(Schedule.version.desc()).first()
    if not s:
        raise HTTPException(status_code=404, detail="Nenhuma escala publicada para este mês")
    return s


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    # Perito comum só enxerga escala publicada; rascunho/gerada é restrito ao gestor
    if s.status != ScheduleStatus.PUBLISHED and not current_user.is_manager:
        raise HTTPException(status_code=403, detail="Escala ainda não publicada")
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
    logger.info("Geração enfileirada: escala %s (%d/%d v%d) por %s",
                schedule.id, cal.year, cal.month, schedule.version, manager.email)
    log_action(db, manager.id, AuditAction.GENERATE, "Schedule", schedule.id, description="Geração iniciada")
    return {"schedule_id": schedule.id, "message": "Geração enfileirada"}


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Apaga uma escala em preparação (não publicada)."""
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    if s.status == ScheduleStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Escala publicada não pode ser apagada.")

    from app.models.audit import SolverAudit
    db.query(SolverAudit).filter(SolverAudit.schedule_id == schedule_id).delete(synchronize_session=False)
    db.query(Assignment).filter(Assignment.schedule_id == schedule_id).delete(synchronize_session=False)
    db.delete(s)
    db.commit()
    logger.info("Escala apagada: %s (%d/%d v%d) por %s", schedule_id, s.year, s.month, s.version, manager.email)
    log_action(db, manager.id, AuditAction.DELETE, "Schedule", schedule_id, description="Escala em preparação apagada")


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
    s.published_at = datetime.now(UTC)
    s.published_by_id = manager.id

    # Finaliza o calendário do mês (Aberto → Finalizado)
    from app.models.operational_calendar import CalendarStatus, OperationalCalendar
    cal = db.get(OperationalCalendar, s.calendar_id)
    if cal:
        cal.status = CalendarStatus.LOCKED

    db.commit()
    logger.info("Escala publicada: %s (%d/%d v%d) por %s; calendário finalizado",
                schedule_id, s.year, s.month, s.version, manager.email)

    # Disparar e-mails e calcular saldo em background
    from app.workers.tasks import post_publish_tasks
    post_publish_tasks.delay(schedule_id)

    log_action(db, manager.id, AuditAction.PUBLISH, "Schedule", schedule_id)
    return {"message": "Escala publicada com sucesso"}


class AssignmentEdit(BaseModel):
    user_id: str | None = None  # None => transforma a vaga em buraco
    reason: str | None = None   # justificativa (obrigatória após publicação)


@router.patch("/{schedule_id}/assignments/{assignment_id}")
def edit_assignment(
    schedule_id: str,
    assignment_id: str,
    data: AssignmentEdit,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    """Admin reatribui (ou esvazia) uma vaga. Após a publicação, exige justificativa."""
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    if s.status == ScheduleStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Escala arquivada não pode ser editada.")

    is_published = s.status == ScheduleStatus.PUBLISHED
    reason = (data.reason or "").strip()
    if is_published and not reason:
        raise HTTPException(status_code=400, detail="Justificativa é obrigatória para alterar uma escala publicada.")

    a = db.get(Assignment, assignment_id)
    if not a or a.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="Atribuição não encontrada")

    anterior = a.user_id
    if data.user_id:
        novo = db.get(User, data.user_id)
        if not novo:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        # Impede a mesma pessoa em dois turnos no mesmo dia
        conflito = db.query(Assignment).filter(
            Assignment.schedule_id == schedule_id,
            Assignment.date == a.date,
            Assignment.user_id == data.user_id,
            Assignment.id != a.id,
        ).first()
        if conflito:
            raise HTTPException(status_code=400, detail=f"{novo.name} já está escalado neste dia")
        a.user_id = data.user_id
        a.is_gap = False
        a.is_manual = True
        a.explanation_flags = {"manual": True, "reason": reason} if reason else {"manual": True}
    else:
        a.user_id = None
        a.is_gap = True
        a.is_manual = True
        a.explanation_flags = {"manual": True, "gap": True, "reason": reason} if reason else {"manual": True, "gap": True}

    db.commit()
    desc = f"Reatribuição em {a.date}" + (f" (escala publicada) — {reason}" if is_published else "")
    log_action(db, manager.id, AuditAction.MANUAL_FILL, "Assignment", assignment_id,
               previous_value={"user_id": anterior}, description=desc)
    return {"message": "Atribuição atualizada"}


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
