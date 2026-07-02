import pytest
from pydantic import ValidationError

from src.core.config import Settings, get_llm_key


def test_settings_loads_db_url_from_env():
    # DATABASE_URL is set in conftest.py
    settings = Settings()
    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
    )


def test_settings_raises_validation_error_when_db_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_openai_api_key_defaults_to_none(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings()
    assert settings.OPENAI_API_KEY is None


def test_settings_sql_echo_defaults_to_false():
    settings = Settings()
    assert settings.SQL_ECHO is False


def test_settings_api_keys_are_masked(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456")
    settings = Settings()
    assert str(settings.OPENAI_API_KEY) == "**********"
    assert settings.OPENAI_API_KEY.get_secret_value() == "sk-test123456"


def test_get_llm_key_retrieves_raw_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-groq")
    settings = Settings()
    assert get_llm_key(settings, "openai") == "sk-openai"
    assert get_llm_key(settings, "groq") == "gsk-groq"
    assert get_llm_key(settings, "gemini") is None
    assert get_llm_key(settings, "unknown") is None
