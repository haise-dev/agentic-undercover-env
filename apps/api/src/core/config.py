import sys

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    OPENAI_API_KEY: SecretStr | None = None
    GEMINI_API_KEY: SecretStr | None = None
    GROQ_API_KEY: SecretStr | None = None
    DEEPSEEK_API_KEY: SecretStr | None = None
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    APP_ENV: str = "development"
    SQL_ECHO: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


def get_llm_key(settings: Settings, provider: str) -> str | None:
    """
    Retrieves the actual API key string for a given LLM provider.
    Returns None if the key is not configured.

    Args:
        provider: One of "openai", "gemini", "groq", "deepseek"
    """
    key_map = {
        "openai": settings.OPENAI_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "deepseek": settings.DEEPSEEK_API_KEY,
    }
    secret = key_map.get(provider.lower())
    return secret.get_secret_value() if secret is not None else None


def load_settings() -> Settings:
    """
    Loads application settings with a human-readable startup error on failure.
    On ValidationError, prints a FATAL block and exits with code 1.
    """
    try:
        return Settings()
    except ValidationError as e:
        print("FATAL: Missing required configuration.")
        for error in e.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            print(f"  → {field}: {msg}")
        print("Hint: Copy .env.example to .env and fill in the required values.")
        sys.exit(1)


settings = load_settings()
