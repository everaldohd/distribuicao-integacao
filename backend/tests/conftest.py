import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.ratelimit import limiter
from app.core.security import hash_password
from app.models.user import User

# Desativa o rate limit nos testes (vários logins do mesmo IP fariam 429)
limiter.enabled = False

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def manager_user(db):
    user = User(
        id="manager-001",
        name="Gestor Teste",
        email="gestor@teste.com",
        hashed_password=hash_password("senha123"),
        is_manager=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def manager_token(client, manager_user):
    resp = client.post("/api/v1/auth/login", json={"email": "gestor@teste.com", "password": "senha123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def regular_user(db):
    user = User(
        id="user-001",
        name="Usuário Teste",
        email="usuario@teste.com",
        hashed_password=hash_password("senha123"),
        is_manager=False,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def user_token(client, regular_user):
    resp = client.post("/api/v1/auth/login", json={"email": "usuario@teste.com", "password": "senha123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]
