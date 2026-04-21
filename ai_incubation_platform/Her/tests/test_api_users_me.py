from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from auth.jwt import get_current_user
from main import app
from api.users import get_user_service


def _build_mock_user(user_id: str):
    user = MagicMock()
    user.id = user_id
    user.username = "tester"
    user.name = "Test User"
    user.email = "test@example.com"
    user.age = 28
    user.gender = "male"
    user.location = "Shanghai"
    user.avatar_url = None
    user.bio = "bio"
    user.preferred_age_min = 22
    user.preferred_age_max = 35
    user.preferred_gender = None
    user.interests = "[]"
    user.values = "{}"
    user.sexual_orientation = "heterosexual"
    return user


def test_get_me_returns_current_user_profile():
    client = TestClient(app)
    current_user_id = "u-test-me-1"

    repo = MagicMock()
    repo.get_by_id.return_value = _build_mock_user(current_user_id)

    app.dependency_overrides[get_current_user] = lambda: current_user_id
    app.dependency_overrides[get_user_service] = lambda: repo
    try:
        response = client.get("/api/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == current_user_id
    assert data["name"] == "Test User"


def test_get_me_returns_404_when_current_user_missing():
    client = TestClient(app)
    current_user_id = "u-not-found"

    repo = MagicMock()
    repo.get_by_id.return_value = None

    app.dependency_overrides[get_current_user] = lambda: current_user_id
    app.dependency_overrides[get_user_service] = lambda: repo
    try:
        response = client.get("/api/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_service, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
