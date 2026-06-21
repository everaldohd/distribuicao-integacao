"""
Testes do fluxo de troca de escala (1:1, mesmo grupo, aprovação do gestor).
"""
import uuid
from datetime import date, timedelta

from app.core.security import hash_password
from app.models.eligibility import Eligibility
from app.models.exchange import Exchange, ExchangeStatus, ExchangeType
from app.models.schedule import Assignment, Schedule, ScheduleStatus
from app.models.schedule_type import ScheduleType
from app.models.user import User


def _user(db, email):
    u = User(id=str(uuid.uuid4()), name=email.split("@")[0], email=email,
             hashed_password=hash_password("senha123"), is_manager=False)
    db.add(u)
    db.flush()
    return u


def _type(db, name, group):
    t = ScheduleType(id=str(uuid.uuid4()), name=name, group_name=group, group_weight=1)
    db.add(t)
    db.flush()
    return t


def _assign(db, sched, user, stype, d):
    a = Assignment(id=str(uuid.uuid4()), schedule_id=sched.id, user_id=user.id,
                   schedule_type_id=stype.id, date=d, is_gap=False)
    db.add(a)
    db.flush()
    return a


def _token(client, email):
    return client.post("/api/v1/auth/login", json={"email": email, "password": "senha123"}).json()["access_token"]


def _setup(db, same_group=True, lead_days=10):
    sched = Schedule(id=str(uuid.uuid4()), calendar_id="cal", year=2026, month=7,
                     version=1, status=ScheduleStatus.PUBLISHED, created_by_id="mgr")
    db.add(sched)
    db.flush()
    plantao = _type(db, "Plantão 12h", "Plantão")
    other = plantao if same_group else _type(db, "Reserva Manhã", "Reserva")

    a = _user(db, "a@teste.com")
    b = _user(db, "b@teste.com")
    # Elegibilidades cruzadas (cada um elegível para o tipo do outro)
    for u in (a, b):
        for t in {plantao.id, other.id}:
            db.add(Eligibility(id=str(uuid.uuid4()), user_id=u.id, schedule_type_id=t, is_eligible=True))
    db.flush()

    d1 = date.today() + timedelta(days=lead_days)
    d2 = date.today() + timedelta(days=lead_days + 5)
    ass_a = _assign(db, sched, a, plantao, d1)
    ass_b = _assign(db, sched, b, other, d2)
    db.commit()
    return ass_a, ass_b


def test_troca_direta_fluxo_completo(client, db, manager_token):
    ass_a, ass_b = _setup(db, same_group=True)
    ta, tb = _token(client, "a@teste.com"), _token(client, "b@teste.com")

    # A solicita troca direta do seu turno pelo de B
    r = client.post("/api/v1/exchanges/direct",
                    headers={"Authorization": f"Bearer {ta}"},
                    json={"requester_assignment_id": ass_a.id, "target_assignment_id": ass_b.id})
    assert r.status_code == 201, r.text
    ex_id = r.json()["id"]
    assert r.json()["status"] == "awaiting_target"

    # B aceita → aguardando gestor
    r = client.post(f"/api/v1/exchanges/{ex_id}/accept", headers={"Authorization": f"Bearer {tb}"})
    assert r.status_code == 200 and r.json()["status"] == "awaiting_manager", r.text

    # Gestor aprova → executa o swap
    r = client.post(f"/api/v1/exchanges/{ex_id}/approve", headers={"Authorization": f"Bearer {manager_token}"})
    assert r.status_code == 200 and r.json()["status"] == "approved", r.text

    # As atribuições trocaram de dono
    db.expire_all()
    assert db.get(Assignment, ass_a.id).user_id == db.query(User).filter(User.email == "b@teste.com").first().id
    assert db.get(Assignment, ass_b.id).user_id == db.query(User).filter(User.email == "a@teste.com").first().id


def test_troca_grupos_diferentes_bloqueada(client, db):
    ass_a, ass_b = _setup(db, same_group=False)
    ta = _token(client, "a@teste.com")
    r = client.post("/api/v1/exchanges/direct",
                    headers={"Authorization": f"Bearer {ta}"},
                    json={"requester_assignment_id": ass_a.id, "target_assignment_id": ass_b.id})
    assert r.status_code == 422
    assert "mesmo grupo" in r.json()["detail"]


def test_troca_dentro_do_prazo_bloqueada(client, db):
    # Turnos a apenas 1 dia → abaixo da antecedência mínima (default 3)
    ass_a, ass_b = _setup(db, same_group=True, lead_days=1)
    ta = _token(client, "a@teste.com")
    r = client.post("/api/v1/exchanges/direct",
                    headers={"Authorization": f"Bearer {ta}"},
                    json={"requester_assignment_id": ass_a.id, "target_assignment_id": ass_b.id})
    assert r.status_code == 422
    assert "antecedência" in r.json()["detail"]


def test_aprovacao_troca_desatualizada_rejeitada(client, db, manager_token):
    """#2: se o turno mudou de dono após a solicitação, a aprovação não pode
    swapar o perito errado — deve recusar com 409 e não executar a troca."""
    ass_a, ass_b = _setup(db, same_group=True)
    a = db.query(User).filter(User.email == "a@teste.com").first()
    b = db.query(User).filter(User.email == "b@teste.com").first()
    # requester_id registrado (b) ≠ dono atual de ass_a (a) → troca desatualizada
    ex = Exchange(id=str(uuid.uuid4()), type=ExchangeType.DIRECT.value,
                  status=ExchangeStatus.AWAITING_MANAGER.value,
                  requester_id=b.id, requester_assignment_id=ass_a.id,
                  target_id=a.id, target_assignment_id=ass_b.id, validation_passed=True)
    db.add(ex)
    db.commit()
    r = client.post(f"/api/v1/exchanges/{ex.id}/approve",
                    headers={"Authorization": f"Bearer {manager_token}"})
    assert r.status_code == 409, r.text
    db.expire_all()
    # Nenhum swap aconteceu
    assert db.get(Assignment, ass_a.id).user_id == a.id
    assert db.get(Assignment, ass_b.id).user_id == b.id


def test_expira_ofertas_vencidas(db):
    """#3: ofertas pendentes cujo turno entrou no prazo de antecedência expiram."""
    from app.services.exchange_validator import expire_pending_exchanges
    ass_a, ass_b = _setup(db, same_group=True, lead_days=1)  # dentro do prazo (default 3)
    a = db.query(User).filter(User.email == "a@teste.com").first()
    ex = Exchange(id=str(uuid.uuid4()), type=ExchangeType.OPEN.value,
                  status=ExchangeStatus.OPEN.value,
                  requester_id=a.id, requester_assignment_id=ass_a.id)
    db.add(ex)
    db.commit()
    n = expire_pending_exchanges(db)
    assert n == 1
    db.expire_all()
    assert db.get(Exchange, ex.id).status == ExchangeStatus.EXPIRED.value


def test_interesticio_vira_o_mes_na_troca(db):
    """#4: o descanso pós-Plantão 12h precisa valer na virada de mês.

    Ao trocar, B assume o Plantão 12h de A no último dia de julho; B já tem um
    turno no 1º de agosto (outra escala). Antes da correção isso passava, porque
    a checagem filtrava por schedule_id (mesmo mês)."""
    from datetime import date

    from app.services.exchange_validator import validate_exchange

    ass_a, ass_b = _setup(db, same_group=True, lead_days=30)
    b = db.query(User).filter(User.email == "b@teste.com").first()
    plantao = db.query(ScheduleType).filter(ScheduleType.name == "Plantão 12h").first()
    plantao.requires_rest_day_after = True  # Plantão 12h exige descanso no dia seguinte

    # Plantão de A no último dia de julho; B com turno no 1º de agosto (escala distinta)
    sched_ago = Schedule(id=str(uuid.uuid4()), calendar_id="cal", year=2026, month=8,
                         version=1, status=ScheduleStatus.PUBLISHED, created_by_id="mgr")
    db.add(sched_ago)
    db.flush()
    ass_a.date = date(2026, 7, 31)
    _assign(db, sched_ago, b, plantao, date(2026, 8, 1))
    db.commit()

    result = validate_exchange(db, ass_a.id, ass_b.id)
    assert not result.passed
    assert "dia seguinte" in result.errors_str()
