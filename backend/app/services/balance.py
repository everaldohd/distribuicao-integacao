"""
Serviço de compensação histórica.
Calcula e persiste o saldo pós-publicação de escala.
"""
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.historical_balance import BalanceConfig, HistoricalBalance
from app.models.preference import PreferenceType, UserPreference
from app.models.schedule import Assignment, Schedule
from app.models.user import User


def _get_config(db: Session) -> BalanceConfig:
    cfg = db.query(BalanceConfig).first()
    if cfg:
        return cfg
    # Retorna config padrão em memória sem persistir
    return BalanceConfig(
        month_no_schedule=settings.BALANCE_MONTH_NO_SCHEDULE,
        desired_date_fulfilled=settings.BALANCE_DESIRED_DATE_FULFILLED,
        common_schedule=settings.BALANCE_COMMON_SCHEDULE,
        avoided_date_assigned=settings.BALANCE_AVOIDED_DATE_ASSIGNED,
    )


def compute_new_user_initial_balance(db: Session) -> float | None:
    """Retorna a média dos saldos atuais dos usuários ativos para nivelar novo usuário."""
    active_ids = [u.id for u in db.query(User.id).filter(User.is_active == True).all()]
    if not active_ids:
        return 0.0

    # Último saldo de cada usuário ativo
    balances = []
    for uid in active_ids:
        last = (
            db.query(HistoricalBalance)
            .filter(HistoricalBalance.user_id == uid)
            .order_by(HistoricalBalance.year.desc(), HistoricalBalance.month.desc())
            .first()
        )
        if last:
            balances.append(last.cumulative_balance)

    if not balances:
        return 0.0
    return sum(balances) / len(balances)


def compute_and_persist_monthly_balances(db: Session, schedule_id: str):
    """
    Calcula o delta de saldo para cada usuário baseado na escala publicada
    e persiste em HistoricalBalance. Aplica normalização ao final.
    """
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return

    cfg = _get_config(db)
    year, month = schedule.year, schedule.month

    # Atribuições publicadas (excluindo gaps)
    assignments = (
        db.query(Assignment)
        .filter(Assignment.schedule_id == schedule_id, Assignment.is_gap == False, Assignment.user_id != None)
        .all()
    )

    # Preferências do mês (casadas por modalidade quando há schedule_type_id)
    prefs = db.query(UserPreference).filter(
        UserPreference.year == year, UserPreference.month == month
    ).all()
    desired_by_user: dict[str, set] = {}   # (date, type_id) ou date (genérica)
    avoid_by_user: dict[str, set] = {}
    for p in prefs:
        key = (p.date, p.schedule_type_id) if p.schedule_type_id else p.date
        if p.type == PreferenceType.DESIRED:
            desired_by_user.setdefault(p.user_id, set()).add(key)
        else:
            avoid_by_user.setdefault(p.user_id, set()).add(key)

    def _matches(prefset: set, a) -> bool:
        return (a.date, a.schedule_type_id) in prefset or a.date in prefset

    # Calcular eventos por usuário
    events: dict[str, dict] = {}
    for a in assignments:
        uid = a.user_id
        ev = events.setdefault(uid, {
            "no_schedule": 0, "desired": 0, "avoided": 0, "common": 0
        })
        if _matches(desired_by_user.get(uid, set()), a):
            ev["desired"] += 1
        elif _matches(avoid_by_user.get(uid, set()), a):
            ev["avoided"] += 1
        else:
            ev["common"] += 1

    # Usuários "escaláveis": têm ao menos uma elegibilidade ativa.
    # Quem não pode ser escalado (sem nenhuma elegibilidade) fica com saldo IMUTÁVEL —
    # não recebe a penalidade de mês sem escala nem entra na normalização.
    from app.models.eligibility import Eligibility
    eligible_user_ids = {
        e.user_id for e in db.query(Eligibility.user_id)
        .filter(Eligibility.is_eligible == True).all()
    }

    # Usuários ativos sem escala no mês, mas que PODERIAM ser escalados → penalidade de ausência
    active_users = db.query(User).filter(User.is_active == True).all()
    assigned_user_ids = {a.user_id for a in assignments}
    for user in active_users:
        if user.id not in assigned_user_ids and user.id in eligible_user_ids:
            events[user.id] = {"no_schedule": 1, "desired": 0, "avoided": 0, "common": 0}

    # Calcular deltas e saldo acumulado
    deltas: dict[str, float] = {}
    for uid, ev in events.items():
        delta = (
            ev["no_schedule"] * cfg.month_no_schedule
            + ev["desired"] * cfg.desired_date_fulfilled
            + ev["avoided"] * cfg.avoided_date_assigned
            + ev["common"] * cfg.common_schedule
        )
        deltas[uid] = delta

    # Buscar saldo anterior de cada usuário
    cumulative: dict[str, float] = {}
    for uid in deltas:
        last = (
            db.query(HistoricalBalance)
            .filter(HistoricalBalance.user_id == uid)
            .order_by(HistoricalBalance.year.desc(), HistoricalBalance.month.desc())
            .first()
        )
        cumulative[uid] = (last.cumulative_balance if last else 0.0) + deltas[uid]

    # Normalização: subtrai a média de todos os saldos acumulados
    if cumulative:
        mean_balance = sum(cumulative.values()) / len(cumulative)
        normalization_delta = -mean_balance
    else:
        normalization_delta = 0.0

    # Persistir
    for uid, delta in deltas.items():
        ev = events[uid]
        final_balance = cumulative[uid] + normalization_delta
        record = HistoricalBalance(
            id=str(uuid.uuid4()),
            user_id=uid,
            year=year,
            month=month,
            delta=delta,
            cumulative_balance=final_balance,
            events_count_no_schedule=ev["no_schedule"],
            events_count_desired_fulfilled=ev["desired"],
            events_count_avoided_assigned=ev["avoided"],
            events_count_common=ev["common"],
            normalization_delta=normalization_delta,
        )
        db.add(record)

    db.commit()
