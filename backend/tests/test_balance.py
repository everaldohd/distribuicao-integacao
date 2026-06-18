"""
Teste do cálculo de saldo de compensação (justiça).
Verifica a convenção de pontos, a normalização pela média e a regra de
saldo IMUTÁVEL para peritos sem elegibilidade.
"""
import uuid
from datetime import date

from app.models.user import User
from app.models.eligibility import Eligibility
from app.models.schedule_type import ScheduleType
from app.models.schedule import Schedule, Assignment, ScheduleStatus
from app.models.historical_balance import HistoricalBalance
from app.core.security import hash_password
from app.services.balance import compute_and_persist_monthly_balances


def _user(db, email, eligible_type=None):
    u = User(id=str(uuid.uuid4()), name=email, email=email, hashed_password=hash_password("x"), is_manager=False)
    db.add(u)
    db.flush()
    if eligible_type is not None:
        db.add(Eligibility(id=str(uuid.uuid4()), user_id=u.id, schedule_type_id=eligible_type.id, is_eligible=True))
        db.flush()
    return u


def test_saldo_normalizado_e_imutavel(db):
    t = ScheduleType(id=str(uuid.uuid4()), name="Plantão 12h", group_name="Plantão", group_weight=1)
    db.add(t)
    db.flush()

    a = _user(db, "a@teste.com", eligible_type=t)   # será escalado (turno comum)
    b = _user(db, "b@teste.com", eligible_type=t)   # elegível, mas sem escala → penalidade
    c = _user(db, "c@teste.com", eligible_type=None)  # SEM elegibilidade → imutável

    sched = Schedule(id=str(uuid.uuid4()), calendar_id="cal", year=2026, month=6,
                     version=1, status=ScheduleStatus.PUBLISHED, created_by_id="mgr")
    db.add(sched)
    db.flush()
    db.add(Assignment(id=str(uuid.uuid4()), schedule_id=sched.id, user_id=a.id,
                      schedule_type_id=t.id, date=date(2026, 6, 10), is_gap=False))
    db.commit()

    compute_and_persist_monthly_balances(db, sched.id)

    saldos = {h.user_id: h.cumulative_balance for h in db.query(HistoricalBalance).all()}

    # Defaults: comum=0 (A), sem_escala=-10 (B). Média = -5; normaliza somando +5.
    assert saldos.get(a.id) == 5.0, "quem trabalhou (comum) deve ficar acima da média"
    assert saldos.get(b.id) == -5.0, "quem não foi escalado deve ficar abaixo da média"
    # C não tem elegibilidade → não pode ser escalado → saldo imutável (sem registro)
    assert c.id not in saldos, "perito sem elegibilidade não deve ter saldo computado"
