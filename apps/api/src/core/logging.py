import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """
    Configures the root logger with a consistent format.
    Call once at application startup.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Factory function — all modules use this instead of
    logging.getLogger() directly.
    """
    return logging.getLogger(name)


def log_startup_status(settings) -> None:
    """
    Logs a startup status block.
    NEVER logs actual API key values — only boolean presence.
    """
    logger = get_logger("aue.startup")
    logger.info("AUE API starting — environment=%s", settings.APP_ENV)
    logger.info(
        "LLM providers configured: openai=%s gemini=%s groq=%s deepseek=%s",
        settings.OPENAI_API_KEY is not None,
        settings.GEMINI_API_KEY is not None,
        settings.GROQ_API_KEY_1 is not None,
        settings.DEEPSEEK_API_KEY is not None,
    )
