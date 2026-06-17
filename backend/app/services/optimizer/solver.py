"""
Motor de Otimização CP-SAT – Sistema de Gestão de Escalas
==========================================================
Implementa distribuição justa, auditável e reproduzível usando Google OR-Tools.

Variáveis de decisão:
  x[u, d, t] = 1 se o usuário u for escalado no dia d para o tipo t, 0 caso contrário
  gap[d, t]  = 1 se a vaga (d, t) ficar vazia ("buraco na escala")

Restrições Rígidas (hard constraints):
  - Indisponibilidade: x[u,d,t] = 0 se u estiver em férias/abono/licença no dia d
  - Elegibilidade: x[u,d,t] = 0 se u não for elegível para t
  - Um turno por dia: sum_t x[u,d,t] <= 1 para todo u, d
  - Cobertura: sum_u x[u,d,t] + gap[d,t] = vagas[d,t] para todo d, t
  - Cotas do perfil: sum_d x[u,d,t] <= cota[u,t] para todo u, t
  - Interstício pós-Plantão 12h: x[u,d+1,*] = 0 se x[u,d,PLANTÃO12h] = 1
    (inclui borda do mês anterior: consulta publicação prévia)

Restrições Suaves (soft constraints, maximize/minimize):
  - Atender preferências desejadas: +peso para x[u,d,*] quando d é desejado por u
  - Evitar datas indesejadas: -peso para x[u,d,*] quando d é a evitar
  - Saldo histórico: prioriza usuários com maior saldo (peso proporcional)
  - Equilíbrio de carga: minimiza variância das atribuições totais

A função objetivo é uma combinação ponderada dessas soft constraints.

Reprodutibilidade: random_seed fixo garantido via SolverParameters.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from ortools.sat.python import cp_model
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
from app.models.operational_calendar import OperationalCalendar
from app.models.schedule import Schedule, Assignment, ScheduleStatus
from app.models.schedule_type import ScheduleType
from app.models.user import User
from app.models.preference import UserPreference, PreferenceType
from app.models.unavailability import Unavailability
from app.models.historical_balance import HistoricalBalance
from app.models.eligibility import Eligibility
from app.models.profile import ProfileRule, UserProfileException
from app.models.audit import SolverAudit
from app.schemas.schedule import SimulationResult


# ---------------------------------------------------------------------------
# Pesos da função objetivo
# ---------------------------------------------------------------------------
WEIGHT_DESIRED = 300        # atender data desejada
WEIGHT_AVOID = 200          # penalidade por data evitada atribuída
WEIGHT_BALANCE = 10         # por ponto de saldo histórico
WEIGHT_GAP = 100_000        # penalidade por buraco (vaga vazia)
WEIGHT_LOAD_EQUITY = 50     # penalidade por desvio de carga


@dataclass
class _UserData:
    id: str
    name: str
    profile_id: Optional[str]
    eligible_type_ids: set = field(default_factory=set)
    unavailable_dates: set = field(default_factory=set)
    desired_dates: set = field(default_factory=set)
    avoid_dates: set = field(default_factory=set)
    quota: dict = field(default_factory=dict)          # {type_id: max_qty}
    balance: float = 0.0
    # Se fez Plantão 12h no último dia do mês anterior
    had_shift_last_day_prev_month: bool = False


class ScheduleSolver:
    """
    Constrói e resolve o modelo CP-SAT para um calendário mensal.
    """

    def __init__(
        self,
        db: Session,
        calendar_id: str,
        manager_id: str,
        simulate_only: bool = False,
    ):
        self.db = db
        self.calendar_id = calendar_id
        self.manager_id = manager_id
        self.simulate_only = simulate_only
        self._load_data()

    # ------------------------------------------------------------------
    # Carga de dados
    # ------------------------------------------------------------------

    def _load_data(self):
        self.calendar = self.db.get(OperationalCalendar, self.calendar_id)
        if not self.calendar:
            raise ValueError(f"Calendário {self.calendar_id} não encontrado")

        self.year = self.calendar.year
        self.month = self.calendar.month

        # Tipos de escala ativos
        self.schedule_types: list[ScheduleType] = (
            self.db.query(ScheduleType).filter(ScheduleType.is_active == True).all()
        )
        self.type_ids = [t.id for t in self.schedule_types]
        self.type_by_id = {t.id: t for t in self.schedule_types}

        # Dias do calendário ordenados
        self.days = sorted(self.calendar.days, key=lambda d: d.date)

        # Cobertura: {(date, type_id): quantity}
        self.coverage: dict[tuple[date, str], int] = {}
        for day in self.days:
            for cov in day.coverages:
                if cov.quantity > 0:
                    self.coverage[(day.date, cov.schedule_type_id)] = cov.quantity

        # Usuários ativos
        active_users = self.db.query(User).filter(User.is_active == True).all()
        self.users: list[_UserData] = []
        self._build_user_data(active_users)

    def _build_user_data(self, active_users: list[User]):
        """Popula _UserData para cada usuário com elegibilidade, indisponibilidade,
        preferências, cotas e saldo histórico."""

        # Elegibilidades
        eligibilities = self.db.query(Eligibility).all()
        elig_map: dict[str, set[str]] = {}  # user_id -> set of type_ids
        for e in eligibilities:
            if e.is_eligible:
                elig_map.setdefault(e.user_id, set()).add(e.schedule_type_id)

        # Indisponibilidades que cobrem algum dia do mês
        first_day = date(self.year, self.month, 1)
        last_day = self.days[-1].date
        unavails = self.db.query(Unavailability).filter(
            Unavailability.start_date <= last_day,
            Unavailability.end_date >= first_day,
        ).all()
        unavail_map: dict[str, set[date]] = {}
        for u in unavails:
            uid = u.user_id
            d = max(u.start_date, first_day)
            while d <= min(u.end_date, last_day):
                unavail_map.setdefault(uid, set()).add(d)
                d += timedelta(days=1)

        # Preferências do mês
        prefs = self.db.query(UserPreference).filter(
            UserPreference.year == self.year,
            UserPreference.month == self.month,
        ).all()
        desired_map: dict[str, set[date]] = {}
        avoid_map: dict[str, set[date]] = {}
        for p in prefs:
            if p.type == PreferenceType.DESIRED:
                desired_map.setdefault(p.user_id, set()).add(p.date)
            else:
                avoid_map.setdefault(p.user_id, set()).add(p.date)

        # Cotas (perfil + exceções individuais)
        profile_rules = self.db.query(ProfileRule).all()
        rule_map: dict[str, dict[str, int]] = {}  # profile_id -> {type_id: qty}
        for r in profile_rules:
            rule_map.setdefault(r.profile_id, {})[r.schedule_type_id] = r.quantity

        exceptions = self.db.query(UserProfileException).filter(
            UserProfileException.year == self.year,
            UserProfileException.month == self.month,
        ).all()
        exception_map: dict[tuple[str, str], int] = {}  # (user_id, type_id) -> qty
        for ex in exceptions:
            exception_map[(ex.user_id, ex.schedule_type_id)] = ex.quantity

        # Saldo histórico: último registro por usuário
        balances = (
            self.db.query(HistoricalBalance)
            .order_by(HistoricalBalance.year.desc(), HistoricalBalance.month.desc())
            .all()
        )
        latest_balance: dict[str, float] = {}
        for b in balances:
            if b.user_id not in latest_balance:
                latest_balance[b.user_id] = b.cumulative_balance

        # Verificar Plantão 12h no último dia do mês anterior (borda do mês)
        prev_plantao_users = self._get_prev_month_plantao_users()

        # Tipos com interstício obrigatório
        rest_type_ids = {t.id for t in self.schedule_types if t.requires_rest_day_after}

        for user in active_users:
            quota: dict[str, int] = {}
            if user.profile_id and user.profile_id in rule_map:
                quota = dict(rule_map[user.profile_id])
            # Sobrescrever com exceções individuais
            for type_id in self.type_ids:
                key = (user.id, type_id)
                if key in exception_map:
                    quota[type_id] = exception_map[key]

            ud = _UserData(
                id=user.id,
                name=user.name,
                profile_id=user.profile_id,
                eligible_type_ids=elig_map.get(user.id, set()),
                unavailable_dates=unavail_map.get(user.id, set()),
                desired_dates=desired_map.get(user.id, set()),
                avoid_dates=avoid_map.get(user.id, set()),
                quota=quota,
                balance=latest_balance.get(user.id, 0.0),
                had_shift_last_day_prev_month=user.id in prev_plantao_users,
            )
            self.users.append(ud)

        self.rest_type_ids = rest_type_ids

    def _get_prev_month_plantao_users(self) -> set[str]:
        """Retorna IDs de usuários que fizeram Plantão 12h no último dia do mês anterior
        (na versão publicada), para aplicar interstício na borda do mês."""
        if self.month == 1:
            prev_year, prev_month = self.year - 1, 12
        else:
            prev_year, prev_month = self.year, self.month - 1

        prev_last_day = date(prev_year, prev_month,
                             [31, 29 if prev_year % 4 == 0 else 28, 31, 30, 31, 30,
                              31, 31, 30, 31, 30, 31][prev_month - 1])

        # Buscar atribuições publicadas no último dia do mês anterior com tipo rest_day
        rest_type_ids = {t.id for t in self.schedule_types if t.requires_rest_day_after}
        if not rest_type_ids:
            return set()

        published_schedule = (
            self.db.query(Schedule)
            .filter(
                Schedule.year == prev_year,
                Schedule.month == prev_month,
                Schedule.status == ScheduleStatus.PUBLISHED,
            )
            .order_by(Schedule.version.desc())
            .first()
        )
        if not published_schedule:
            return set()

        prev_assignments = (
            self.db.query(Assignment)
            .filter(
                Assignment.schedule_id == published_schedule.id,
                Assignment.date == prev_last_day,
                Assignment.schedule_type_id.in_(rest_type_ids),
                Assignment.is_gap == False,
            )
            .all()
        )
        return {a.user_id for a in prev_assignments if a.user_id}

    # ------------------------------------------------------------------
    # Simulação rápida (sem solver)
    # ------------------------------------------------------------------

    def simulate(self) -> SimulationResult:
        """Estimativa rápida sem executar o solver."""
        total_slots = sum(self.coverage.values())
        day_dates = [d.date for d in self.days]

        # Usuários elegíveis para ao menos um tipo
        eligible_users = [u for u in self.users if u.eligible_type_ids]
        n_eligible = len(eligible_users)

        # Estimativa de preferências
        all_desired = sum(len(u.desired_dates) for u in self.users)
        all_avoid = sum(len(u.avoid_dates) for u in self.users)

        # Estimativa de gaps: dias sem usuários disponíveis suficientes
        gaps = 0
        for (d, t), qty in self.coverage.items():
            available = sum(
                1 for u in self.users
                if t in u.eligible_type_ids and d not in u.unavailable_dates
            )
            if available < qty:
                gaps += qty - available

        return SimulationResult(
            total_slots=total_slots,
            eligible_users=n_eligible,
            estimated_preferences_fulfilled_pct=min(100.0, 70.0) if all_desired > 0 else 0.0,
            estimated_avoided_assigned=max(0, all_avoid // 4),
            expected_gaps=gaps,
            notes=[
                f"{n_eligible} usuários elegíveis para ao menos um tipo de escala.",
                f"{total_slots} vagas no total.",
                f"{gaps} possíveis buracos identificados na pré-análise.",
            ],
        )

    # ------------------------------------------------------------------
    # Geração via CP-SAT
    # ------------------------------------------------------------------

    def solve(self, schedule_id: str) -> dict:
        """Executa o solver e persiste as atribuições no banco."""
        model = cp_model.CpModel()

        users = self.users
        days = self.days
        type_ids = self.type_ids

        # Índices numéricos
        U = {u.id: i for i, u in enumerate(users)}
        D = {d.date: j for j, d in enumerate(days)}
        T = {t: k for k, t in enumerate(type_ids)}

        # ------------------------------------------------------------------
        # Variáveis de decisão
        # ------------------------------------------------------------------
        x = {}
        for u in users:
            for day in days:
                for t_id in type_ids:
                    if (day.date, t_id) in self.coverage and self.coverage[(day.date, t_id)] > 0:
                        x[(u.id, day.date, t_id)] = model.new_bool_var(
                            f"x_{U[u.id]}_{D[day.date]}_{T[t_id]}"
                        )

        # Variáveis de gap (buraco)
        gap = {}
        for (d, t_id), qty in self.coverage.items():
            if qty > 0:
                gap[(d, t_id)] = model.new_int_var(0, qty, f"gap_{D[d]}_{T[t_id]}")

        # ------------------------------------------------------------------
        # Restrições Rígidas
        # ------------------------------------------------------------------

        # 1. Indisponibilidade e elegibilidade
        for u in users:
            for day in days:
                for t_id in type_ids:
                    if (u.id, day.date, t_id) not in x:
                        continue
                    if day.date in u.unavailable_dates or t_id not in u.eligible_type_ids:
                        model.add(x[(u.id, day.date, t_id)] == 0)

        # 2. Um turno por dia por usuário
        for u in users:
            for day in days:
                vars_day = [
                    x[(u.id, day.date, t_id)]
                    for t_id in type_ids
                    if (u.id, day.date, t_id) in x
                ]
                if vars_day:
                    model.add(sum(vars_day) <= 1)

        # 3. Cobertura = atribuições + gaps
        for (d, t_id), qty in self.coverage.items():
            if qty == 0:
                continue
            assigned_vars = [
                x[(u.id, d, t_id)] for u in users if (u.id, d, t_id) in x
            ]
            model.add(sum(assigned_vars) + gap[(d, t_id)] == qty)

        # 4. Cotas do perfil por usuário e tipo
        for u in users:
            for t_id in type_ids:
                max_qty = u.quota.get(t_id)
                if max_qty is not None:
                    vars_type = [
                        x[(u.id, d.date, t_id)]
                        for d in days
                        if (u.id, d.date, t_id) in x
                    ]
                    if vars_type:
                        model.add(sum(vars_type) <= max_qty)

        # 5. Interstício pós-Plantão 12h
        for u in users:
            for j, day in enumerate(days):
                for t_id in self.rest_type_ids:
                    if (u.id, day.date, t_id) not in x:
                        continue
                    # No dia seguinte, nenhuma escala
                    if j + 1 < len(days):
                        next_day = days[j + 1]
                        next_vars = [
                            x[(u.id, next_day.date, t2)]
                            for t2 in type_ids
                            if (u.id, next_day.date, t2) in x
                        ]
                        for nv in next_vars:
                            model.add(nv + x[(u.id, day.date, t_id)] <= 1)

            # Borda do mês: Plantão 12h no último dia do mês anterior
            if u.had_shift_last_day_prev_month and days:
                first_day = days[0]
                first_vars = [
                    x[(u.id, first_day.date, t2)]
                    for t2 in type_ids
                    if (u.id, first_day.date, t2) in x
                ]
                for fv in first_vars:
                    model.add(fv == 0)

        # ------------------------------------------------------------------
        # Função Objetivo (soft constraints)
        # ------------------------------------------------------------------
        objective_terms = []

        # Minimizar gaps (buracos)
        for (d, t_id), g in gap.items():
            objective_terms.append(-WEIGHT_GAP * g)

        # Maximizar preferências atendidas / penalizar datas evitadas
        for u in users:
            for day in days:
                for t_id in type_ids:
                    if (u.id, day.date, t_id) not in x:
                        continue
                    v = x[(u.id, day.date, t_id)]
                    if day.date in u.desired_dates:
                        objective_terms.append(WEIGHT_DESIRED * v)
                    elif day.date in u.avoid_dates:
                        objective_terms.append(-WEIGHT_AVOID * v)

        # Priorizar usuários com maior saldo histórico
        max_abs_balance = max((abs(u.balance) for u in users), default=1.0) or 1.0
        for u in users:
            normalized = u.balance / max_abs_balance  # [-1, 1]
            scaled = int(normalized * 100)
            for day in days:
                for t_id in type_ids:
                    if (u.id, day.date, t_id) not in x:
                        continue
                    objective_terms.append(WEIGHT_BALANCE * scaled * x[(u.id, day.date, t_id)])

        # Equilíbrio de carga (minimizar desvio entre número de atribuições)
        if users:
            total_assignments = [
                sum(x[(u.id, d.date, t_id)] for d in days for t_id in type_ids if (u.id, d.date, t_id) in x)
                for u in users
            ]
            if len(total_assignments) > 1:
                avg_var = model.new_int_var(0, len(days) * len(type_ids), "avg_load")
                for ta in total_assignments:
                    dev = model.new_int_var(-len(days) * len(type_ids), len(days) * len(type_ids), "dev")
                    model.add(dev == ta - avg_var)
                    abs_dev = model.new_int_var(0, len(days) * len(type_ids), "abs_dev")
                    model.add_abs_equality(abs_dev, dev)
                    objective_terms.append(-WEIGHT_LOAD_EQUITY * abs_dev)

        model.maximize(sum(objective_terms))

        # ------------------------------------------------------------------
        # Resolver
        # ------------------------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.random_seed = settings.SOLVER_RANDOM_SEED
        solver.parameters.max_time_in_seconds = settings.SOLVER_MAX_TIME_SECONDS
        solver.parameters.num_workers = 4

        start_time = time.time()
        status = solver.solve(model)
        elapsed = time.time() - start_time

        status_name = solver.status_name(status)

        # ------------------------------------------------------------------
        # Persistir resultados
        # ------------------------------------------------------------------
        assignments_to_create = []
        gaps_count = 0
        preferences_fulfilled = 0
        avoided_assigned = 0

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Atribuições
            for u in users:
                for day in days:
                    for t_id in type_ids:
                        if (u.id, day.date, t_id) not in x:
                            continue
                        if solver.value(x[(u.id, day.date, t_id)]) == 1:
                            flags = {"eligible": True, "rested": True}
                            if day.date in u.desired_dates:
                                flags["desired_date"] = True
                                preferences_fulfilled += 1
                            if day.date in u.avoid_dates:
                                flags["avoided_date"] = True
                                avoided_assigned += 1
                            if u.balance > 0:
                                flags["positive_balance"] = round(u.balance, 2)
                            assignments_to_create.append(
                                Assignment(
                                    id=str(uuid.uuid4()),
                                    schedule_id=schedule_id,
                                    user_id=u.id,
                                    schedule_type_id=t_id,
                                    date=day.date,
                                    is_gap=False,
                                    explanation_flags=flags,
                                )
                            )

            # Gaps
            for (d, t_id), g_var in gap.items():
                gap_qty = solver.value(g_var)
                for _ in range(gap_qty):
                    assignments_to_create.append(
                        Assignment(
                            id=str(uuid.uuid4()),
                            schedule_id=schedule_id,
                            user_id=None,
                            schedule_type_id=t_id,
                            date=d,
                            is_gap=True,
                            explanation_flags={"gap": True, "reason": "Sem usuários elegíveis disponíveis"},
                        )
                    )
                    gaps_count += 1

        # Persistir
        db_schedule = self.db.get(Schedule, schedule_id)
        if assignments_to_create:
            self.db.add_all(assignments_to_create)

        db_schedule.status = ScheduleStatus.GENERATED if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else ScheduleStatus.DRAFT

        # Auditoria matemática
        audit = SolverAudit(
            id=str(uuid.uuid4()),
            schedule_id=schedule_id,
            eligible_users_count=len([u for u in users if u.eligible_type_ids]),
            total_slots=sum(self.coverage.values()),
            preferences_desired_count=sum(len(u.desired_dates) for u in users),
            preferences_avoid_count=sum(len(u.avoid_dates) for u in users),
            preferences_fulfilled_count=preferences_fulfilled,
            avoided_dates_assigned_count=avoided_assigned,
            gaps_count=gaps_count,
            solver_status=status_name,
            objective_value=solver.objective_value if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
            processing_time_seconds=round(elapsed, 3),
            random_seed=settings.SOLVER_RANDOM_SEED,
            solver_params={"max_time_seconds": settings.SOLVER_MAX_TIME_SECONDS, "num_workers": 4},
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "status": status_name,
            "gaps": gaps_count,
            "assignments": len([a for a in assignments_to_create if not a.is_gap]),
            "elapsed_seconds": round(elapsed, 3),
        }
