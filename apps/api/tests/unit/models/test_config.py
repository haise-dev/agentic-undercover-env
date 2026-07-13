import pytest
from pydantic import ValidationError

from src.models.config import AgentConfig, AgentLLMConfig, EpisodeConfig
from src.models.enums import AgentType, LLMProvider


def test_agent_llm_config_defaults():
    config = AgentLLMConfig(
        provider=LLMProvider.GROQ,
        smart_model_name="smart-70b",
        fast_model_name="fast-8b"
    )
    assert config.temperature == 0.8
    assert config.max_tokens is None
    assert config.smart_model_name == "smart-70b"
    assert config.fast_model_name == "fast-8b"


def test_agent_llm_config_fallback():
    # Test backward compatibility where only model_name is provided
    config = AgentLLMConfig(
        provider=LLMProvider.GROQ,
        model_name="fallback-model"
    )
    assert config.smart_model_name == "fallback-model"
    assert config.fast_model_name == "fallback-model"


def test_agent_llm_config_frozen():
    config = AgentLLMConfig(
        provider=LLMProvider.GROQ,
        smart_model_name="smart-70b",
        fast_model_name="fast-8b"
    )
    with pytest.raises(ValidationError):
        config.temperature = 0.5


def test_agent_config_ai_type():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agent = AgentConfig(
        agent_id="agent_0",
        display_name="Alice",
        display_color="cyan",
        agent_type=AgentType.AI,
        llm_config=llm,
    )
    assert agent.agent_type == AgentType.AI
    assert agent.llm_config == llm


def test_agent_config_human_type():
    agent = AgentConfig(
        agent_id="agent_0",
        display_name="Alice",
        display_color="cyan",
        agent_type=AgentType.HUMAN,
        llm_config=None,
    )
    assert agent.agent_type == AgentType.HUMAN
    assert agent.llm_config is None
    assert agent.api_key_index == 1


def test_agent_config_api_key_index_validation():
    # Valid index
    for idx in range(1, 5):
        agent = AgentConfig(
            agent_id="agent_0",
            display_name="Alice",
            display_color="cyan",
            agent_type=AgentType.HUMAN,
            llm_config=None,
            api_key_index=idx,
        )
        assert agent.api_key_index == idx

    # Invalid index < 1
    with pytest.raises(ValidationError):
        AgentConfig(
            agent_id="agent_0",
            display_name="Alice",
            display_color="cyan",
            agent_type=AgentType.HUMAN,
            llm_config=None,
            api_key_index=0,
        )

    # Invalid index > 4
    with pytest.raises(ValidationError):
        AgentConfig(
            agent_id="agent_0",
            display_name="Alice",
            display_color="cyan",
            agent_type=AgentType.HUMAN,
            llm_config=None,
            api_key_index=5,
        )


def test_episode_config_exactly_four_agents():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agents = [
        AgentConfig(
            agent_id=f"agent_{i}",
            display_name=name,
            display_color=color,
            agent_type=AgentType.AI,
            llm_config=llm,
        )
        for i, (name, color) in enumerate(
            zip(
                ["Alice", "Bob", "Charlie", "Diana"],
                ["cyan", "magenta", "yellow", "green"],
                strict=False,
            )
        )
    ]
    episode = EpisodeConfig(
        episode_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        topic="Fruit",
        secret_word="Durian",
        agents=agents,
        max_rounds=3,
    )
    assert len(episode.agents) == 4


def test_episode_config_three_agents_raises():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agents = [
        AgentConfig(
            agent_id=f"agent_{i}",
            display_name=name,
            display_color=color,
            agent_type=AgentType.AI,
            llm_config=llm,
        )
        for i, (name, color) in enumerate(
            zip(
                ["Alice", "Bob", "Charlie"], ["cyan", "magenta", "yellow"], strict=False
            )
        )
    ]
    with pytest.raises(ValidationError) as exc_info:
        EpisodeConfig(
            episode_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
            topic="Fruit",
            secret_word="Durian",
            agents=agents,
            max_rounds=3,
        )
    assert "agents" in str(exc_info.value)
    assert "exactly 4 agents" in str(exc_info.value).lower()


def test_episode_config_five_agents_raises():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agents = [
        AgentConfig(
            agent_id=f"agent_{i}",
            display_name=name,
            display_color=color,
            agent_type=AgentType.AI,
            llm_config=llm,
        )
        for i, (name, color) in enumerate(
            zip(
                ["Alice", "Bob", "Charlie", "Diana", "Eve"],
                ["cyan", "magenta", "yellow", "green", "green"],
                strict=False,
            )
        )
    ]
    with pytest.raises(ValidationError) as exc_info:
        EpisodeConfig(
            episode_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
            topic="Fruit",
            secret_word="Durian",
            agents=agents,
            max_rounds=3,
        )
    assert "agents" in str(exc_info.value)
    assert "exactly 4 agents" in str(exc_info.value).lower()


def test_episode_config_max_rounds_default():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agents = [
        AgentConfig(
            agent_id=f"agent_{i}",
            display_name=name,
            display_color=color,
            agent_type=AgentType.AI,
            llm_config=llm,
        )
        for i, (name, color) in enumerate(
            zip(
                ["Alice", "Bob", "Charlie", "Diana"],
                ["cyan", "magenta", "yellow", "green"],
                strict=False,
            )
        )
    ]
    episode = EpisodeConfig(
        episode_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        topic="Fruit",
        secret_word="Durian",
        agents=agents,
    )
    assert episode.max_rounds == 3


def test_episode_config_frozen():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agents = [
        AgentConfig(
            agent_id=f"agent_{i}",
            display_name=name,
            display_color=color,
            agent_type=AgentType.AI,
            llm_config=llm,
        )
        for i, (name, color) in enumerate(
            zip(
                ["Alice", "Bob", "Charlie", "Diana"],
                ["cyan", "magenta", "yellow", "green"],
                strict=False,
            )
        )
    ]
    episode = EpisodeConfig(
        episode_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        topic="Fruit",
        secret_word="Durian",
        agents=agents,
    )
    with pytest.raises(ValidationError):
        episode.topic = "Animals"


def test_episode_config_serializable():
    llm = AgentLLMConfig(
        provider=LLMProvider.GROQ, model_name="llama-3.3-70b-versatile"
    )
    agents = [
        AgentConfig(
            agent_id=f"agent_{i}",
            display_name=name,
            display_color=color,
            agent_type=AgentType.AI,
            llm_config=llm,
        )
        for i, (name, color) in enumerate(
            zip(
                ["Alice", "Bob", "Charlie", "Diana"],
                ["cyan", "magenta", "yellow", "green"],
                strict=False,
            )
        )
    ]
    episode = EpisodeConfig(
        episode_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        topic="Fruit",
        secret_word="Durian",
        agents=agents,
    )
    dumped = episode.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["topic"] == "Fruit"
    assert len(dumped["agents"]) == 4
