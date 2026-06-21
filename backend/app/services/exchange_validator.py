"""Validação de trocas de escala contra regras operacionais rígidas."""
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.timeutil import today_local
from app.models.eligibility import Eligibility
from app.models.historical_balance import BalanceConfig
from app.models.schedule import Assignment
from app.models.schedule_type import ScheduleType
from app.models.unavailability import Unavailability


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)

    def errors_str(self) -> str:
        return "; ".join(self.errors)


def get_min_lead_days(db: Session) -> int:
    cfg = db.query(BalanceConfig).first()
    return cfg.exchange_min_lead_days if cfg and cfg.exchange_min_lead_days is not None else 3


def expire_pending_exchanges(db: Session) -> int:
    """Marca como EXPIRED as trocas pendentes cujo turno entrou na janela de
    antecedência (ou já passou). Lógica isolada da task Celery p/ ser testável."""
    from datetime import UTC, datetime

    from app.core.timeutil import today_local
    from app.models.exchange import Exchange, ExchangeStatus
    from app.models.schedule import Assignment

    pending = (ExchangeStatus.OPEN.value, ExchangeStatus.AWAITING_TARGET.value,
               ExchangeStatus.AWAITING_MANAGER.value)
    limite = today_local() + timedelta(days=get_min_lead_days(db))
    expired = 0
    for ex in db.query(Exchange).filter(Exchange.status.in_(pending)).all():
        dates = []
        for aid in (ex.requester_assignment_id, ex.target_assignment_id):
            if aid:
                a = db.get(Assignment, aid)
                if a:
                    dates.append(a.date)
        if dates and min(dates) < limite:
            ex.status = ExchangeStatus.EXPIRED.value
            ex.resolved_at = datetime.now(UTC)
            expired += 1
    if expired:
        db.commit()
    return expired


def validate_exchange(
    db: Session,
    requester_assignment_id: str,
    target_assignment_id: str,
) -> ValidationResult:
    """Valida se uma troca 1:1 entre duas atribuições viola regras rígidas:
    mesmo grupo, antecedência mínima, elegibilidade, indisponibilidade,
    interstício pós-Plantão 12h e não-duplicação de turno no mesmo dia."""
    errors = []

    req = db.get(Assignment, requester_assignment_id)
    tgt = db.get(Assignment, target_assignment_id)

    if not req or not tgt:
        return ValidationResult(False, ["Atribuição não encontrada"])

    if req.id == tgt.id or req.user_id == tgt.user_id:
        return ValidationResult(False, ["Não é possível trocar com a própria atribuição/usuário"])

    req_user_id, tgt_user_id = req.user_id, tgt.user_id

    # 0a. Mesmo grupo (Plantão↔Plantão, Reserva↔Reserva, Pátio↔Pátio)
    req_type = db.get(ScheduleType, req.schedule_type_id)
    tgt_type = db.get(ScheduleType, tgt.schedule_type_id)
    req_group = (req_type.group_name or req_type.name) if req_type else None
    tgt_group = (tgt_type.group_name or tgt_type.name) if tgt_type else None
    if req_group != tgt_group:
        errors.append(f"Troca só é permitida dentro do mesmo grupo ({req_group} ≠ {tgt_group})")

    # 0b. Antecedência mínima — os dois turnos precisam estar suficientemente no futuro
    min_lead = get_min_lead_days(db)
    limite = today_local() + timedelta(days=min_lead)
    for d in (req.date, tgt.date):
        if d < limite:
            errors.append(f"Troca exige antecedência mínima de {min_lead} dia(s); {d} está dentro do prazo")
            break

    # Após a troca: req_user ficará no turno do tgt e vice-versa
    # Validar cada usuário no novo turno
    for (user_id, new_assignment) in [(req_user_id, tgt), (tgt_user_id, req)]:
        new_date = new_assignment.date
        new_type_id = new_assignment.schedule_type_id

        schedule_type = db.get(ScheduleType, new_type_id)

        # 1. Indisponibilidade
        unavails = db.query(Unavailability).filter(
            Unavailability.user_id == user_id,
            Unavailability.start_date <= new_date,
            Unavailability.end_date >= new_date,
        ).first()
        if unavails:
            errors.append(f"Usuário {user_id} está indisponível em {new_date}")

        # 2. Elegibilidade
        elig = db.query(Eligibility).filter(
            Eligibility.user_id == user_id,
            Eligibility.schedule_type_id == new_type_id,
            Eligibility.is_eligible == True,
        ).first()
        if not elig:
            errors.append(f"Usuário {user_id} não é elegível para {schedule_type.name if schedule_type else new_type_id}")

        # 3. Interstício pós-Plantão 12h
        # NB: sem filtro por schedule_id — o descanso precisa valer também na
        # virada do mês (dia seguinte/anterior pode estar em outra escala).
        if schedule_type and schedule_type.requires_rest_day_after:
            # Não pode ter escala no dia seguinte
            next_day = new_date + timedelta(days=1)
            next_assignment = db.query(Assignment).filter(
                Assignment.user_id == user_id,
                Assignment.date == next_day,
                Assignment.is_gap == False,
                Assignment.id.notin_([req.id, tgt.id]),
            ).first()
            if next_assignment:
                errors.append(f"Usuário {user_id} tem escala no dia seguinte ao Plantão 12h ({next_day})")

        # Também verificar se não há Plantão 12h no dia anterior que exija descanso neste dia
        prev_day = new_date - timedelta(days=1)
        prev_rest_assignment = db.query(Assignment).join(ScheduleType).filter(
            Assignment.user_id == user_id,
            Assignment.date == prev_day,
            Assignment.is_gap == False,
            Assignment.id.notin_([req.id, tgt.id]),
            ScheduleType.requires_rest_day_after == True,
        ).first()
        if prev_rest_assignment:
            errors.append(f"Usuário {user_id} fez Plantão 12h em {prev_day} e precisa de descanso em {new_date}")

        # 4. Não pode ficar com dois turnos no mesmo dia (ignora as duas vagas da própria troca)
        outro_no_dia = db.query(Assignment).filter(
            Assignment.user_id == user_id,
            Assignment.date == new_date,
            Assignment.is_gap == False,
            Assignment.schedule_id == new_assignment.schedule_id,
            Assignment.id.notin_([req.id, tgt.id]),
        ).first()
        if outro_no_dia:
            errors.append(f"Usuário {user_id} já tem outro turno em {new_date}")

    return ValidationResult(passed=len(errors) == 0, errors=errors)
