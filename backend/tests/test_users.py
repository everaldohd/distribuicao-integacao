def test_create_user_as_manager(client, manager_token):
    resp = client.post(
        "/api/v1/users/",
        json={"name": "Novo Usuário", "email": "novo@teste.com", "password": "Senha@123", "is_manager": False},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "novo@teste.com"
    assert data["is_manager"] is False


def test_create_user_duplicate_email(client, manager_token, regular_user):
    resp = client.post(
        "/api/v1/users/",
        json={"name": "Duplicado", "email": "usuario@teste.com", "password": "Senha@123", "is_manager": False},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400


def test_create_user_requires_manager(client, user_token):
    resp = client.post(
        "/api/v1/users/",
        json={"name": "Bloqueado", "email": "bloqueado@teste.com", "password": "Senha@123", "is_manager": False},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_list_users_as_manager(client, manager_token, regular_user):
    resp = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {manager_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_users_requires_manager(client, user_token):
    resp = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


def test_create_user_weak_password_rejected(client, manager_token):
    # Sem maiúscula/dígito/símbolo → deve falhar a validação (422)
    resp = client.post(
        "/api/v1/users/",
        json={"name": "Fraco", "email": "fraco@teste.com", "password": "senhafraca", "is_manager": False},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 422


def test_change_password(client, user_token):
    resp = client.put(
        "/api/v1/users/me/password",
        json={"current_password": "senha123", "new_password": "NovaSenha@456"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200


def test_change_password_wrong_current(client, user_token):
    resp = client.put(
        "/api/v1/users/me/password",
        json={"current_password": "errada", "new_password": "NovaSenha@456"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 400
