"""
Testes do núcleo de otimização (ScheduleSolver).
Montam cenários mínimos e verificam as regras rígidas mais importantes:
cota por grupo e interstício pós-Plantão 12h.
"""
import uuid
from datetime import date

from app.models.schedule_type import ScheduleType
from app.models.profile import Profile, ProfileGroupLimit
from app.models.eligibility import Eligibility
from app.models.operational_calendar import OperationalCalendar, CalendarDay, DayCoverage, DayCategory
from app.models.schedule import Schedule, Assignment, ScheduleStatus
from app.models.user import User
from app.core.security import hash_password
from app.services.optimizer.solver import ScheduleSolver


def _plantao_type(db) -> ScheduleType:
    t = ScheduleType(id=str(uuid.uuid4()), name="Plantão 12h", requires_rest_day_after=True,
                     group_name="Plantão", group_weight=1, display_order=1)
    db.add(t)
    db.flush()
    return t


def _user_with(db, plantao_limit: int, plantao_type: ScheduleType) -> User:
    profile = Profile(id=str(uuid.uuid4()), name="Perfil Teste")
    db.add(profile)
    db.flush()
    db.add(ProfileGroupLimit(id=str(uuid.uuid4()), profile_id=profile.id, group_name="Plantão", max_quantity=plantao_limit))
    u = User(id=str(uuid.uuid4()), name="Perito Teste", email="perito@teste.com",
             hashed_password=hash_password("x"), is_manager=False, profile_id=profile.id)
    db.add(u)
    db.flush()
    db.add(Eligibility(id=str(uuid.uuid4()), user_id=u.id, schedule_type_id=plantao_type.id, is_eligible=True))
    db.flush()
    return u


def _calendar(db, n_days: int, plantao_type: ScheduleType, start: date = date(2026, 6, 1)) -> OperationalCalendar:
    cal = OperationalCalendar(id=str(uuid.uuid4()), year=start.year, month=start.month, created_by_id="mgr")
    db.add(cal)
    db.flush()
    for i in range(n_days):
        d = date(start.year, start.month, start.day + i)
        day = CalendarDay(id=str(uuid.uuid4()), calendar_id=cal.id, date=d, category=DayCategory.WORKDAY)
        db.add(day)
        db.flush()
        db.add(DayCoverage(id=str(uuid.uuid4()), day_id=day.id, schedule_type_id=plantao_type.id, quantity=1))
    db.flush()
    return cal


def _run(db, cal, manager_id="mgr"):
    sched = Schedule(id=str(uuid.uuid4()), calendar_id=cal.id, year=cal.year, month=cal.month,
                     version=1, status=ScheduleStatus.DRAFT, created_by_id=manager_id)
    db.add(sched)
    db.flush()
    ScheduleSolver(db, cal.id, manager_id).solve(sched.id)
    return db.query(Assignment).filter(Assignment.schedule_id == sched.id).all()


def test_cota_por_grupo_respeitada(db):
    """Com cota Plantão=1 e 4 vagas, o perito recebe no máximo 1 plantão (resto vira buraco)."""
    t = _plantao_type(db)
    u = _user_with(db, plantao_limit=1, plantao_type=t)
    cal = _calendar(db, n_days=4, plantao_type=t)

    assignments = _run(db, cal)
    do_perito = [a for a in assignments if a.user_id == u.id and not a.is_gap]
    buracos = [a for a in assignments if a.is_gap]

    assert len(do_perito) == 1, "perito não deveria ultrapassar a cota de 1 plantão"
    assert len(buracos) == 3, "as 3 vagas restantes deveriam virar buracos"


def test_intersticio_pos_plantao(db):
    """Cota generosa, mas o interstício impede plantões em dias consecutivos (1,3,5)."""
    t = _plantao_type(db)
    u = _user_with(db, plantao_limit=5, plantao_type=t)
    cal = _calendar(db, n_days=5, plantao_type=t)

    assignments = _run(db, cal)
    dias = sorted(a.date.day for a in assignments if a.user_id == u.id and not a.is_gap)

    assert len(dias) == 3, f"esperado 3 plantões não-consecutivos, veio {dias}"
    for anterior, proximo in zip(dias, dias[1:]):
        assert proximo - anterior >= 2, f"plantões em dias consecutivos violam o interstício: {dias}"
