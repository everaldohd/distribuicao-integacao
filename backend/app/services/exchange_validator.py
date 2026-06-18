"""Validação de trocas de escala contra regras operacionais rígidas."""
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.eligibility import Eligibility
from app.models.schedule import Assignment
from app.models.schedule_type import ScheduleType
from app.models.unavailability import Unavailability


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)

    def errors_str(self) -> str:
        return "; ".join(self.errors)


def validate_exchange(
    db: Session,
    requester_assignment_id: str,
    target_assignment_id: str,
) -> ValidationResult:
    """Valida se uma troca entre duas atribuições viola regras rígidas."""
    errors = []

    req = db.get(Assignment, requester_assignment_id)
    tgt = db.get(Assignment, target_assignment_id)

    if not req or not tgt:
        return ValidationResult(False, ["Atribuição não encontrada"])

    req_user_id, tgt_user_id = req.user_id, tgt.user_id

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
        if schedule_type and schedule_type.requires_rest_day_after:
            # Não pode ter escala no dia seguinte
            next_day = new_date + timedelta(days=1)
            next_assignment = db.query(Assignment).filter(
                Assignment.user_id == user_id,
                Assignment.date == next_day,
                Assignment.is_gap == False,
                Assignment.schedule_id == new_assignment.schedule_id,
            ).first()
            if next_assignment:
                errors.append(f"Usuário {user_id} tem escala no dia seguinte ao Plantão 12h ({next_day})")

        # Também verificar se não há Plantão 12h no dia anterior que exija descanso neste dia
        prev_day = new_date - timedelta(days=1)
        prev_rest_assignment = db.query(Assignment).join(ScheduleType).filter(
            Assignment.user_id == user_id,
            Assignment.date == prev_day,
            Assignment.is_gap == False,
            Assignment.schedule_id == new_assignment.schedule_id,
            ScheduleType.requires_rest_day_after == True,
        ).first()
        if prev_rest_assignment:
            errors.append(f"Usuário {user_id} fez Plantão 12h em {prev_day} e precisa de descanso em {new_date}")

    return ValidationResult(passed=len(errors) == 0, errors=errors)
