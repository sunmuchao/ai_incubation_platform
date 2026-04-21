import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from db.models import UserDB
from auth.jwt import create_access_token
from api.chat import _safe_auto_update_profile_from_chat, router as chat_router


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)
app_for_api_tests = FastAPI()
app_for_api_tests.include_router(chat_router)


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app_for_api_tests.dependency_overrides[get_db] = override_get_db
    with TestClient(app_for_api_tests) as c:
        yield c
    app_for_api_tests.dependency_overrides.clear()


def make_user(**kwargs):
    defaults = {
        "id": str(uuid.uuid4()),
        "email": f"chat_api_{uuid.uuid4()}@example.com",
        "password_hash": "hashed_pw",
        "name": "Chat API User",
        "age": 28,
        "gender": "male",
        "location": "北京",
        "interests": "[]",
        "values": "{}",
        "bio": "",
        "occupation": "产品经理",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


def test_rollback_endpoint_success(client, db_session):
    user = make_user(location="北京")
    db_session.add(user)
    db_session.commit()

    # 先制造可回滚的自动更新
    _safe_auto_update_profile_from_chat(db_session, user.id, "我现在在无锡这边工作")
    _safe_auto_update_profile_from_chat(db_session, user.id, "我目前常住在无锡生活")

    token = create_access_token(user_id=user.id)
    response = client.post(
        "/api/chat/profile/auto-update/rollback",
        headers={"Authorization": f"Bearer {token}"},
        json={"field": "location"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rolled_back"] is True
    assert payload["field"] == "location"
    assert payload["restored_value"] == "北京"


def test_rollback_endpoint_no_applied_update(client, db_session):
    user = make_user(location="北京")
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user_id=user.id)
    response = client.post(
        "/api/chat/profile/auto-update/rollback",
        headers={"Authorization": f"Bearer {token}"},
        json={"field": "location"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rolled_back"] is False
    assert payload["reason"] == "no_applied_update"


def test_rollback_endpoint_invalid_field_returns_422(client, db_session):
    user = make_user()
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user_id=user.id)
    response = client.post(
        "/api/chat/profile/auto-update/rollback",
        headers={"Authorization": f"Bearer {token}"},
        json={"field": "gender"},
    )
    assert response.status_code == 422
