"""
Teste do limite de preferências por grupo (cota_grupo × fator).
Garante que o perito não ultrapassa o teto de dias para uma modalidade.
"""
import uuid

from app.models.user import User
from app.models.profile import Profile, ProfileGroupLimit
from app.models.schedule_type import ScheduleType
from app.core.security import hash_password


def _setup_perito(db):
    t = ScheduleType(id=str(uuid.uuid4()), name="Plantão 12h", group_name="Plantão", group_weight=1)
    db.add(t)
    profile = Profile(id=str(uuid.uuid4()), name="Perfil Pref")
    db.add(profile)
    db.flush()
    db.add(ProfileGroupLimit(id=str(uuid.uuid4()), profile_id=profile.id, group_name="Plantão", max_quantity=1))
    u = User(id=str(uuid.uuid4()), name="Perito Pref", email="pref@teste.com",
             hashed_password=hash_password("senha123"), is_manager=False, profile_id=profile.id)
    db.add(u)
    db.commit()
    return t


def test_limite_preferencias_por_grupo(client, db):
    """Cota Plantão=1 e fator padrão 2 → no máximo 2 dias de 'desejo' de Plantão."""
    t = _setup_perito(db)
    token = client.post("/api/v1/auth/login", json={"email": "pref@teste.com", "password": "senha123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def marcar(dia):
        return client.post("/api/v1/preferences/", headers=headers, json={
            "year": 2026, "month": 6, "date": f"2026-06-{dia:02d}",
            "schedule_type_id": t.id, "type": "desired",
        })

    assert marcar(10).status_code == 201
    assert marcar(17).status_code == 201
    # 3º estoura o teto (1 × fator 2 = 2)
    resp = marcar(24)
    assert resp.status_code == 400, "o 3º dia de Plantão deveria ser bloqueado pelo limite"
    assert "Limite" in resp.json()["detail"]
