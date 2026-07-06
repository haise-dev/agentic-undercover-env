from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.core.config import Settings
from src.models import AgentLLMConfig, LLMProvider


def get_llm_client(config: AgentLLMConfig, settings: Settings) -> BaseChatModel:
    """
    Factory function to instantiate the correct LangChain ChatModel based on provider.
    Requires the appropriate API key to be set in Settings.
    """
    if config.provider == LLMProvider.OPENAI:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY.get_secret_value(),
            model=config.model_name,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.GEMINI:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        return ChatGoogleGenerativeAI(
            api_key=settings.GEMINI_API_KEY.get_secret_value(),
            model=config.model_name,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.GROQ:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured")
        return ChatGroq(
            api_key=settings.GROQ_API_KEY.get_secret_value(),
            model_name=config.model_name,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.DEEPSEEK:
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        return ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY.get_secret_value(),
            model=config.model_name,
            temperature=config.temperature,
            base_url="https://api.deepseek.com/v1",
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
