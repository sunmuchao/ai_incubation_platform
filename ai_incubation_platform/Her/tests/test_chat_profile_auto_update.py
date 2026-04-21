import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import Base, UserDB, UserProfileUpdateDB
import api.chat as chat_api
from api.chat import (
    _get_auto_profile_runtime_config,
    _extract_profile_signals_from_text,
    _safe_auto_update_profile_from_chat,
    _parse_profile_signals_from_llm_text,
    _safe_parse_json_object,
    _rollback_latest_auto_profile_update,
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _make_user(**kwargs) -> UserDB:
    defaults = {
        "id": str(uuid.uuid4()),
        "email": f"u_{uuid.uuid4()}@example.com",
        "password_hash": "hashed",
        "name": "Test User",
        "age": 28,
        "gender": "male",
        "location": "",
        "occupation": "",
        "interests": "[]",
        "values": "{}",
        "bio": "",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_extract_profile_signals_basic():
    text = "我叫孙木超，在无锡从事软件开发，平时爱看动漫和听音乐"
    signals = _extract_profile_signals_from_text(text)
    assert signals["location"] == "无锡"
    assert signals["occupation"] == "软件开发"
    assert "动漫" in signals["interests"]
    assert "音乐" in signals["interests"]


def test_auto_update_conflict_requires_second_confirmation():
    db = TestingSessionLocal()
    user = _make_user(location="北京", occupation="产品经理")
    db.add(user)
    db.commit()

    first = _safe_auto_update_profile_from_chat(db, user.id, "我现在在无锡做软件开发")
    db.refresh(user)
    assert first["applied"] == 0
    assert first["pending"] >= 1
    assert user.location == "北京"
    assert user.occupation == "产品经理"

    second = _safe_auto_update_profile_from_chat(db, user.id, "我在无锡，从事软件开发")
    db.refresh(user)
    assert second["applied"] >= 1
    assert user.location == "无锡"
    assert user.occupation == "软件开发"

    applied_updates = db.query(UserProfileUpdateDB).filter(
        UserProfileUpdateDB.user_id == user.id,
        UserProfileUpdateDB.applied.is_(True),
    ).count()
    assert applied_updates >= 1
    db.close()


def test_auto_update_merges_interests():
    db = TestingSessionLocal()
    user = _make_user(interests='["音乐"]')
    db.add(user)
    db.commit()

    result = _safe_auto_update_profile_from_chat(db, user.id, "我平时喜欢看动漫，也喜欢听音乐")
    db.refresh(user)
    assert result["applied"] >= 1
    assert "音乐" in user.interests
    assert "动漫" in user.interests
    db.close()


def test_parse_profile_signals_from_llm_text():
    llm_text = '{"location":"无锡","occupation":"软件开发","interests":["动漫","音乐","动漫"]}'
    signals = _parse_profile_signals_from_llm_text(llm_text)
    assert signals["location"] == "无锡"
    assert signals["occupation"] == "软件开发"
    assert signals["interests"] == ["动漫", "音乐"]


def test_rollback_latest_auto_profile_update():
    db = TestingSessionLocal()
    user = _make_user(location="北京")
    db.add(user)
    db.commit()

    _safe_auto_update_profile_from_chat(db, user.id, "我在无锡做软件开发")
    _safe_auto_update_profile_from_chat(db, user.id, "我在无锡做软件开发")
    db.refresh(user)
    assert user.location == "无锡"

    result = _rollback_latest_auto_profile_update(db, user.id, "location")
    db.refresh(user)
    assert result["rolled_back"] is True
    assert user.location == "北京"
    db.close()


def test_pending_evidence_expires_and_needs_new_accumulation():
    db = TestingSessionLocal()
    user = _make_user(location="北京")
    db.add(user)
    db.commit()

    first = _safe_auto_update_profile_from_chat(db, user.id, "我现在在无锡做软件开发")
    assert first["pending"] >= 1

    pending_row = db.query(UserProfileUpdateDB).filter(
        UserProfileUpdateDB.user_id == user.id,
        UserProfileUpdateDB.update_type == "chat_auto_location",
        UserProfileUpdateDB.applied.is_(False),
    ).order_by(UserProfileUpdateDB.created_at.desc()).first()
    pending_row.created_at = datetime.utcnow() - timedelta(days=45)
    db.commit()

    second = _safe_auto_update_profile_from_chat(db, user.id, "我现在在无锡生活和工作")
    db.refresh(user)
    assert second["applied"] == 0
    assert second["pending"] >= 1
    assert user.location == "北京"
    db.close()


def test_runtime_settings_threshold_takes_effect(monkeypatch):
    db = TestingSessionLocal()
    user = _make_user(location="北京", occupation="产品经理")
    db.add(user)
    db.commit()

    monkeypatch.setattr(chat_api.settings, "chat_auto_update_location_threshold", 2.0, raising=False)

    _safe_auto_update_profile_from_chat(db, user.id, "我目前人在无锡这边生活")
    second = _safe_auto_update_profile_from_chat(db, user.id, "我现在常住在无锡附近")
    db.refresh(user)

    # 两次 location 规则证据共 1.44，低于 2.0，不应自动覆盖
    assert second["pending"] >= 1
    assert user.location == "北京"
    db.close()


def test_runtime_config_clamps_invalid_values(monkeypatch):
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_cooldown_hours", 0, raising=False)
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_confirm_window_days", -1, raising=False)
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_min_text_len_for_llm", 2, raising=False)
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_llm_max_tokens", 10, raising=False)
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_pending_ttl_days", 0, raising=False)
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_location_threshold", 0.1, raising=False)
    monkeypatch.setattr(chat_api.settings, "chat_auto_update_occupation_threshold", 0.2, raising=False)

    cfg = _get_auto_profile_runtime_config()
    assert cfg["cooldown_hours"] == 1
    assert cfg["confirm_window_days"] == 1
    assert cfg["min_text_len_for_llm"] == 8
    assert cfg["llm_max_tokens"] == 60
    assert cfg["pending_ttl_days"] == 1
    assert cfg["threshold"]["location"] == 0.8
    assert cfg["threshold"]["occupation"] == 0.8


def test_auto_update_uses_small_llm_fallback(monkeypatch):
    db = TestingSessionLocal()
    user = _make_user(location="北京")
    db.add(user)
    db.commit()

    monkeypatch.setattr(chat_api.settings, "chat_auto_update_location_threshold", 1.2, raising=False)
    monkeypatch.setattr(chat_api, "_extract_profile_signals_from_text", lambda _text: {})
    monkeypatch.setattr(chat_api, "_extract_profile_signals_with_small_llm", lambda _text: {"location": "无锡"})

    first = _safe_auto_update_profile_from_chat(db, user.id, "我想聊聊近况")
    second = _safe_auto_update_profile_from_chat(db, user.id, "我想聊聊近况")
    db.refresh(user)

    assert first["pending"] >= 1
    assert second["applied"] >= 1
    assert user.location == "无锡"
    db.close()


def test_auto_update_syncs_vector_dimensions_on_apply():
    db = TestingSessionLocal()
    user = _make_user(
        location="",
        occupation="",
        self_profile_json="{}",
        desire_profile_json="{}",
    )
    db.add(user)
    db.commit()

    result = _safe_auto_update_profile_from_chat(db, user.id, "我在无锡做软件开发，喜欢动漫和音乐")
    db.refresh(user)
    self_json = _safe_parse_json_object(user.self_profile_json)
    desire_json = _safe_parse_json_object(user.desire_profile_json)

    assert result["applied"] >= 1
    assert self_json.get("vector_dimensions", {}).get("demographics", {}).get("location") == "无锡"
    assert self_json.get("vector_dimensions", {}).get("demographics", {}).get("occupation") == "软件开发"
    declared = desire_json.get("vector_dimensions", {}).get("interests", {}).get("declared_interests", [])
    assert "动漫" in declared

    db.close()


def test_rollback_when_no_applied_update_returns_false():
    db = TestingSessionLocal()
    user = _make_user(location="北京")
    db.add(user)
    db.commit()

    result = _rollback_latest_auto_profile_update(db, user.id, "location")
    assert result["rolled_back"] is False
    assert result["reason"] == "no_applied_update"
    db.close()
