def test_create_schedule_type(client, manager_token):
    resp = client.post(
        "/api/v1/schedule-types/",
        json={"name": "Plantão 12h", "requires_rest_day_after": True},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Plantão 12h"
    assert data["requires_rest_day_after"] is True


def test_list_schedule_types(client, manager_token):
    client.post(
        "/api/v1/schedule-types/",
        json={"name": "Sobreaviso", "requires_rest_day_after": False},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    resp = client.get("/api/v1/schedule-types/", headers={"Authorization": f"Bearer {manager_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_create_schedule_type_requires_auth(client):
    resp = client.post("/api/v1/schedule-types/", json={"name": "X", "requires_rest_day_after": False})
    assert resp.status_code == 401
