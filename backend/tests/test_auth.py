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


def test_login_sets_cookies(client, manager_user):
    resp = client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    assert resp.status_code == 200
    # Sessão HttpOnly + cookie CSRF legível
    assert "access_token" in resp.cookies
    assert "csrf_token" in resp.cookies
    assert resp.json()["csrf_token"]


def test_cookie_auth_works_for_get(client, manager_user):
    # Login grava cookies no client; GET (método seguro) dispensa CSRF
    client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    resp = client.get("/api/v1/users/me")  # sem header Authorization → usa cookie
    assert resp.status_code == 200
    assert resp.json()["email"] == "gestor@teste.com"


def test_cookie_mutation_requires_csrf(client, manager_user):
    login = client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    csrf = login.json()["csrf_token"]
    # Sem o header X-CSRF-Token → bloqueado (autenticação via cookie)
    blocked = client.post(
        "/api/v1/users/",
        json={"name": "Xavier", "email": "x@teste.com", "password": "Senha@123", "is_manager": False},
    )
    assert blocked.status_code == 403
    # Com o header correto → passa
    ok = client.post(
        "/api/v1/users/",
        json={"name": "Xavier", "email": "x@teste.com", "password": "Senha@123", "is_manager": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert ok.status_code == 201


def test_logout_clears_session(client, manager_user):
    client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    csrf = client.cookies.get("csrf_token")
    resp = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    client.cookies.clear()
    # Sem cookies → não autenticado
    assert client.get("/api/v1/users/me").status_code == 401


def test_logout_revokes_token(client, manager_user):
    """Após o logout, o MESMO token não pode mais ser usado (denylist por jti).

    Sem revogação, um token vazado continuaria válido até o exp mesmo com logout.
    """
    login = client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    token = login.json()["access_token"]
    # Token funciona antes do logout
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    csrf = client.cookies.get("csrf_token")
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.cookies.clear()
    # O mesmo token, apresentado como Bearer, deve ser recusado
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_first_login_requires_password_change(client, manager_token):
    """Usuário recém-criado vem com must_change_password=True (troca no 1º login)."""
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {manager_token}"})
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True


def test_change_password_clears_flag_and_new_password_works(client, manager_token):
    headers = {"Authorization": f"Bearer {manager_token}"}
    resp = client.put(
        "/api/v1/users/me/password",
        json={"current_password": "senha123", "new_password": "minha.nova1"},
        headers=headers,
    )
    assert resp.status_code == 200
    # Flag limpa após a troca
    assert client.get("/api/v1/users/me", headers=headers).json()["must_change_password"] is False
    # A senha nova vale; a antiga não
    assert client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "minha.nova1"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"}).status_code == 401


def test_password_policy_8_chars_and_special(client, manager_token):
    """Política: mínimo 8 caracteres + 1 especial (sem exigir maiúscula/dígito)."""
    headers = {"Authorization": f"Bearer {manager_token}"}

    def attempt(pwd):
        return client.put(
            "/api/v1/users/me/password",
            json={"current_password": "senha123", "new_password": pwd},
            headers=headers,
        ).status_code

    assert attempt("curta!") == 422          # menos de 8
    assert attempt("semespecial8") == 422    # sem caractere especial
    assert attempt("senhaboa!") == 200       # 8+ com especial: aceita


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
