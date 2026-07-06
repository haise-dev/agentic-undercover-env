import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.agents.llm_factory import get_llm_client
from src.core.config import Settings
from src.models import AgentLLMConfig, LLMProvider


def test_get_llm_client_openai():
    config = AgentLLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-4o")
    # Provide a dummy key so it doesn't try to load from environment
    settings = Settings(OPENAI_API_KEY="dummy-key")
    
    client = get_llm_client(config, settings)
    assert isinstance(client, ChatOpenAI)
    assert client.model_name == "gpt-4o"
    assert client.openai_api_base != "https://api.deepseek.com/v1"


def test_get_llm_client_gemini():
    config = AgentLLMConfig(provider=LLMProvider.GEMINI, model_name="gemini-1.5-pro")
    settings = Settings(GEMINI_API_KEY="dummy-key")
    
    client = get_llm_client(config, settings)
    assert isinstance(client, ChatGoogleGenerativeAI)
    assert client.model == "gemini-1.5-pro"


def test_get_llm_client_groq():
    config = AgentLLMConfig(provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile")
    settings = Settings(GROQ_API_KEY="dummy-key")
    
    client = get_llm_client(config, settings)
    assert isinstance(client, ChatGroq)
    assert client.model_name == "llama-3.3-70b-versatile"


def test_get_llm_client_deepseek():
    config = AgentLLMConfig(provider=LLMProvider.DEEPSEEK, model_name="deepseek-chat")
    settings = Settings(DEEPSEEK_API_KEY="dummy-key")
    
    client = get_llm_client(config, settings)
    assert isinstance(client, ChatOpenAI)
    assert client.model_name == "deepseek-chat"
    assert client.openai_api_base == "https://api.deepseek.com/v1"


def test_get_llm_client_missing_api_key():
    config = AgentLLMConfig(provider=LLMProvider.GROQ, model_name="llama3")
    settings = Settings(GROQ_API_KEY=None)
    
    with pytest.raises(ValueError, match="GROQ_API_KEY is not configured"):
        get_llm_client(config, settings)


def test_get_llm_client_unsupported_provider():
    # Force an unsupported provider enum for coverage
    config = AgentLLMConfig(provider=LLMProvider.OPENAI, model_name="gpt")
    object.__setattr__(config, "provider", "UNSUPPORTED_PROVIDER")
    settings = Settings()
    
    with pytest.raises(ValueError, match="Unsupported LLM provider: UNSUPPORTED_PROVIDER"):
        get_llm_client(config, settings)
