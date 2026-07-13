from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.core.config import Settings
from src.models import AgentLLMConfig, LLMProvider


def get_llm_client(
    config: AgentLLMConfig, settings: Settings, model_name: str | None = None, api_key_index: int = 1
) -> BaseChatModel:
    """
    Factory function to instantiate the correct LangChain ChatModel based on provider.
    Requires the appropriate API key to be set in Settings.
    """
    resolved_model_name = model_name or config.smart_model_name

    if config.provider == LLMProvider.OPENAI:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY.get_secret_value(),
            model=resolved_model_name,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.GEMINI:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        return ChatGoogleGenerativeAI(
            api_key=settings.GEMINI_API_KEY.get_secret_value(),
            model=resolved_model_name,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.GROQ:
        from src.core.config import get_llm_key

        key = get_llm_key(settings, "groq", api_key_index)
        if not key:
            raise ValueError(f"GROQ_API_KEY_{api_key_index} is not configured")
        return ChatGroq(
            api_key=key,
            model_name=resolved_model_name,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.DEEPSEEK:
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        return ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY.get_secret_value(),
            model=resolved_model_name,
            temperature=config.temperature,
            base_url="https://api.deepseek.com/v1",
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
