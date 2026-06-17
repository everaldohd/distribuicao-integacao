def test_login_success(client, manager_user):
    resp = client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, manager_user):
    resp = client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "errada"})
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/api/v1/auth/login", json={"email": "naoexiste@teste.com", "password": "qualquer"})
    assert resp.status_code == 401


def test_get_me(client, manager_token):
    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {manager_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "gestor@teste.com"


def test_get_me_unauthenticated(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
