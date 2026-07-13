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
    settings = Settings(GROQ_API_KEY_1="dummy-key")
    
    client = get_llm_client(config, settings)
    assert isinstance(client, ChatGroq)
    assert client.model_name == "llama-3.3-70b-versatile"


def test_get_llm_client_groq_indexed():
    config = AgentLLMConfig(provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile")
    settings = Settings(GROQ_API_KEY_1="dummy-1", GROQ_API_KEY_2="dummy-2")
    
    client1 = get_llm_client(config, settings, api_key_index=1)
    assert isinstance(client1, ChatGroq)
    assert client1.groq_api_key.get_secret_value() == "dummy-1"

    client2 = get_llm_client(config, settings, api_key_index=2)
    assert isinstance(client2, ChatGroq)
    assert client2.groq_api_key.get_secret_value() == "dummy-2"


def test_get_llm_client_deepseek():
    config = AgentLLMConfig(provider=LLMProvider.DEEPSEEK, model_name="deepseek-chat")
    settings = Settings(DEEPSEEK_API_KEY="dummy-key")
    
    client = get_llm_client(config, settings)
    assert isinstance(client, ChatOpenAI)
    assert client.model_name == "deepseek-chat"
    assert client.openai_api_base == "https://api.deepseek.com/v1"


def test_get_llm_client_missing_api_key():
    config = AgentLLMConfig(provider=LLMProvider.GROQ, model_name="llama3")
    settings = Settings(GROQ_API_KEY_1=None)
    
    with pytest.raises(ValueError, match="GROQ_API_KEY_1 is not configured"):
        get_llm_client(config, settings, api_key_index=1)


def test_get_llm_client_unsupported_provider():
    # Force an unsupported provider enum for coverage
    config = AgentLLMConfig(provider=LLMProvider.OPENAI, model_name="gpt")
    object.__setattr__(config, "provider", "UNSUPPORTED_PROVIDER")
    settings = Settings()
    
    with pytest.raises(ValueError, match="Unsupported LLM provider: UNSUPPORTED_PROVIDER"):
        get_llm_client(config, settings)


def test_get_llm_client_explicit_model_name():
    config = AgentLLMConfig(
        provider=LLMProvider.GROQ,
        smart_model_name="smart-70b",
        fast_model_name="fast-8b"
    )
    settings = Settings(GROQ_API_KEY_1="dummy-key")
    
    # Passing no model_name should use smart_model_name
    client = get_llm_client(config, settings)
    assert client.model_name == "smart-70b"

    # Passing explicit model_name should use it
    client_fast = get_llm_client(config, settings, model_name="fast-8b")
    assert client_fast.model_name == "fast-8b"
