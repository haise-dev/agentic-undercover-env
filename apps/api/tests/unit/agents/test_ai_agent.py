from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.ai_agent import AIAgent
from src.models import (
    AgentType,
    DeliberationOutput,
    Phase,
    PollingOutput,
    ReactionOutput,
    SpeakingOutput,
    VotingOutput,
    Role,
    RoundContext,
    AgentRoleAssignment,
)


@pytest.fixture
def mock_llm_client():
    mock = MagicMock()
    mock_chain = AsyncMock()
    mock.with_structured_output.return_value = mock_chain
    return mock


@pytest.fixture
def round_context():
    return RoundContext(
        role_assignment=AgentRoleAssignment(
            agent_id="agent_0", role=Role.VILLAGER, secret_word="Cat", topic="Animals"
        ),
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=0,
        public_history=[],
        announcements=[],
        alive_agents=[
            {"agent_id": "agent_0", "display_name": "Alice"},
            {"agent_id": "agent_1", "display_name": "Bob"},
            {"agent_id": "agent_2", "display_name": "Charlie"},
            {"agent_id": "agent_3", "display_name": "Dave"},
        ],
        all_agent_names="Alice, Bob, Charlie, Dave",
        game_language="English",
        is_final_round=False,
    )


@pytest.fixture
def ai_agent(make_agent_config, role_assignments, mock_llm_client):
    config = make_agent_config(0, AgentType.AI)
    role_assignment = role_assignments["agent_0"]
    
    with patch("src.agents.ai_agent.get_llm_client", return_value=mock_llm_client), \
         patch("src.agents.ai_agent.settings"):
        agent = AIAgent(config=config, role_assignment=role_assignment)
    return agent


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_speak(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = SpeakingOutput(inner_thought="I should say hi.", public_statement="Hi!")
    mock_invoke.return_value = expected_output

    with patch("src.core.quota.QuotaManager.add_usage") as mock_add_usage:
        output = await ai_agent.speak(context=round_context)
        
        assert output == expected_output
        assert len(ai_agent.action_logs) == 1
        log = ai_agent.action_logs[0]
        assert log.phase == Phase.SPEAKING
        assert log.agent_id == ai_agent.config.agent_id
        assert log.structured_output == expected_output.model_dump()
        assert log.prompt_tokens is not None
        assert log.completion_tokens is not None
        assert log.total_tokens is not None
        assert mock_invoke.call_count == 1
        mock_add_usage.assert_called_once_with(ai_agent.config.api_key_index, log.total_tokens)


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_deliberate(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = DeliberationOutput(inner_thought="Thinking...", public_statement="I agree.")
    mock_invoke.return_value = expected_output

    with patch("src.core.quota.QuotaManager.add_usage") as mock_add_usage:
        output = await ai_agent.deliberate(context=round_context)
        
        assert output == expected_output
        assert len(ai_agent.action_logs) == 1
        log = ai_agent.action_logs[0]
        assert log.phase == Phase.DELIBERATION
        assert log.prompt_tokens is not None
        assert log.completion_tokens is not None
        assert log.total_tokens is not None
        mock_add_usage.assert_called_once_with(ai_agent.config.api_key_index, log.total_tokens)


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_poll(mock_invoke, ai_agent, mock_llm_client, round_context):
    from src.models import PollVote
    expected_output = PollingOutput(inner_thought="Skip it", poll_vote=PollVote.SKIP)
    mock_invoke.return_value = expected_output

    with patch("src.core.quota.QuotaManager.add_usage") as mock_add_usage:
        output = await ai_agent.poll(context=round_context)
        
        assert output == expected_output
        assert len(ai_agent.action_logs) == 1
        log = ai_agent.action_logs[0]
        assert log.phase == Phase.POLLING
        assert log.prompt_tokens is not None
        assert log.completion_tokens is not None
        assert log.total_tokens is not None
        mock_add_usage.assert_called_once_with(ai_agent.config.api_key_index, log.total_tokens)


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_vote(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = VotingOutput(inner_thought="Voting agent_1", vote_target="agent_1")
    mock_invoke.return_value = expected_output

    with patch("src.core.quota.QuotaManager.add_usage") as mock_add_usage:
        output = await ai_agent.vote(context=round_context)
        
        assert output == expected_output
        assert len(ai_agent.action_logs) == 1
        log = ai_agent.action_logs[0]
        assert log.phase == Phase.VOTING
        assert log.prompt_tokens is not None
        assert log.completion_tokens is not None
        assert log.total_tokens is not None
        mock_add_usage.assert_called_once_with(ai_agent.config.api_key_index, log.total_tokens)


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_react(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = ReactionOutput(inner_thought="Surprised", public_statement="Wow!")
    mock_invoke.return_value = expected_output

    with patch("src.core.quota.QuotaManager.add_usage") as mock_add_usage:
        output = await ai_agent.react(context=round_context, is_eliminated_agent=True)
        
        assert output == expected_output
        assert len(ai_agent.action_logs) == 1
        log = ai_agent.action_logs[0]
        assert log.phase == Phase.REACTION
        assert log.prompt_tokens is not None
        assert log.completion_tokens is not None
        assert log.total_tokens is not None
        mock_add_usage.assert_called_once_with(ai_agent.config.api_key_index, log.total_tokens)


def test_ai_agent_model_tiering_selection(make_agent_config, role_assignments, round_context):
    from src.models import AgentLLMConfig, LLMProvider
    
    # Custom config with distinct model names
    llm_config = AgentLLMConfig(
        provider=LLMProvider.GROQ,
        smart_model_name="smart-model-70b",
        fast_model_name="fast-model-8b"
    )
    
    config = make_agent_config(0, AgentType.AI)
    object.__setattr__(config, "llm_config", llm_config)
    
    role_assignment = role_assignments["agent_0"]
    
    mock_smart_llm = MagicMock()
    mock_fast_llm = MagicMock()
    
    mock_smart_llm.with_structured_output.return_value = AsyncMock()
    mock_fast_llm.with_structured_output.return_value = AsyncMock()

    def get_llm_client_side_effect(cfg, settings, model_name=None, api_key_index=1):
        if model_name == "smart-model-70b":
            return mock_smart_llm
        elif model_name == "fast-model-8b":
            return mock_fast_llm
        return MagicMock()

    with patch("src.agents.ai_agent.get_llm_client", side_effect=get_llm_client_side_effect), \
         patch("src.agents.ai_agent.settings"):
        agent = AIAgent(config=config, role_assignment=role_assignment)
        
    assert agent._smart_llm == mock_smart_llm
    assert agent._fast_llm == mock_fast_llm


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_routing_to_tiers(mock_invoke, make_agent_config, role_assignments, round_context):
    from src.models import AgentLLMConfig, LLMProvider
    
    llm_config = AgentLLMConfig(
        provider=LLMProvider.GROQ,
        smart_model_name="smart-model-70b",
        fast_model_name="fast-model-8b"
    )
    
    config = make_agent_config(0, AgentType.AI)
    object.__setattr__(config, "llm_config", llm_config)
    role_assignment = role_assignments["agent_0"]
    
    mock_smart_llm = MagicMock()
    mock_fast_llm = MagicMock()
    
    mock_smart_chain = AsyncMock()
    mock_fast_chain = AsyncMock()
    
    mock_smart_llm.with_structured_output.return_value = mock_smart_chain
    mock_fast_llm.with_structured_output.return_value = mock_fast_chain
    
    def get_llm_client_side_effect(cfg, settings, model_name=None, api_key_index=1):
        if model_name == "smart-model-70b":
            return mock_smart_llm
        elif model_name == "fast-model-8b":
            return mock_fast_llm
        return MagicMock()
        
    with patch("src.agents.ai_agent.get_llm_client", side_effect=get_llm_client_side_effect), \
         patch("src.agents.ai_agent.settings"):
        agent = AIAgent(config=config, role_assignment=role_assignment)

    # Test Speaking (should route to smart model)
    mock_invoke.return_value = SpeakingOutput(inner_thought="thought", public_statement="statement")
    await agent.speak(context=round_context)
    mock_smart_llm.with_structured_output.assert_called_once_with(SpeakingOutput, include_raw=True)
    mock_fast_llm.with_structured_output.assert_not_called()

    # Reset mocks
    mock_smart_llm.reset_mock()
    mock_fast_llm.reset_mock()
    
    # Test Reacting (should route to fast model)
    mock_invoke.return_value = ReactionOutput(inner_thought="thought", public_statement="statement")
    await agent.react(context=round_context)
    mock_fast_llm.with_structured_output.assert_called_once_with(ReactionOutput, include_raw=True)
    mock_smart_llm.with_structured_output.assert_not_called()


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_token_extraction(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = SpeakingOutput(inner_thought="I should say hi.", public_statement="Hi!")
    
    mock_raw_message = MagicMock()
    mock_raw_message.usage_metadata = {
        "input_tokens": 150,
        "output_tokens": 50,
        "total_tokens": 200,
    }
    mock_invoke.return_value = {
        "parsed": expected_output,
        "raw": mock_raw_message,
    }

    with patch("src.core.quota.QuotaManager.add_usage") as mock_add_usage:
        output = await ai_agent.speak(context=round_context)
        
        assert output == expected_output
        assert len(ai_agent.action_logs) == 1
        log = ai_agent.action_logs[0]
        assert log.prompt_tokens == 150
        assert log.completion_tokens == 50
        assert log.total_tokens == 200
        mock_add_usage.assert_called_once_with(ai_agent.config.api_key_index, 200)

