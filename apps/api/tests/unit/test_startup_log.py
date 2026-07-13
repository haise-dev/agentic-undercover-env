import logging

from src.core.config import Settings
from src.core.logging import configure_logging, get_logger, log_startup_status


def test_configure_logging():
    # Make sure calling it doesn't fail
    configure_logging("INFO")
    # Check that root logger level is INFO (or has been set)
    assert logging.getLogger().level == logging.INFO


def test_get_logger():
    logger = get_logger("aue.test")
    assert logger.name == "aue.test"


def test_log_startup_status_no_keys(caplog):
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5432/test_db",
        REDIS_URL="redis://localhost:6379/0",
        OPENAI_API_KEY=None,
        GEMINI_API_KEY=None,
        GROQ_API_KEY_1=None,
        GROQ_API_KEY_2=None,
        GROQ_API_KEY_3=None,
        GROQ_API_KEY_4=None,
        DEEPSEEK_API_KEY=None,
    )
    with caplog.at_level(logging.INFO):
        log_startup_status(settings)

    log_text = caplog.text
    assert "AUE API starting — environment=test" in log_text
    assert (
        "LLM providers configured: openai=False gemini=False groq=False deepseek=False"
        in log_text
    )
    # Assert password is not in log text
    assert "test_password" not in log_text


def test_log_startup_status_with_keys(caplog):
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5432/test_db",
        REDIS_URL="redis://localhost:6379/0",
        OPENAI_API_KEY="sk-openai-val",
        GEMINI_API_KEY=None,
        GROQ_API_KEY_1="gsk-groq-val",
        DEEPSEEK_API_KEY=None,
    )
    with caplog.at_level(logging.INFO):
        log_startup_status(settings)

    log_text = caplog.text
    assert "openai=True" in log_text
    assert "groq=True" in log_text
    assert "gemini=False" in log_text
    # Assert actual keys are NOT present in the log output in plaintext
    assert "sk-openai-val" not in log_text
    assert "gsk-groq-val" not in log_text
