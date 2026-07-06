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

    output = await ai_agent.speak(context=round_context)
    
    assert output == expected_output
    assert len(ai_agent.action_logs) == 1
    log = ai_agent.action_logs[0]
    assert log.phase == Phase.SPEAKING
    assert log.agent_id == ai_agent.config.agent_id
    assert log.structured_output == expected_output.model_dump()
    assert mock_invoke.call_count == 1


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_deliberate(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = DeliberationOutput(inner_thought="Thinking...", public_statement="I agree.")
    mock_invoke.return_value = expected_output

    output = await ai_agent.deliberate(context=round_context)
    
    assert output == expected_output
    assert len(ai_agent.action_logs) == 1
    assert ai_agent.action_logs[0].phase == Phase.DELIBERATION


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_poll(mock_invoke, ai_agent, mock_llm_client, round_context):
    from src.models import PollVote
    expected_output = PollingOutput(inner_thought="Skip it", poll_vote=PollVote.SKIP)
    mock_invoke.return_value = expected_output

    output = await ai_agent.poll(context=round_context)
    
    assert output == expected_output
    assert len(ai_agent.action_logs) == 1
    assert ai_agent.action_logs[0].phase == Phase.POLLING


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_vote(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = VotingOutput(inner_thought="Voting agent_1", vote_target="agent_1")
    mock_invoke.return_value = expected_output

    output = await ai_agent.vote(context=round_context)
    
    assert output == expected_output
    assert len(ai_agent.action_logs) == 1
    assert ai_agent.action_logs[0].phase == Phase.VOTING


@pytest.mark.asyncio
@patch("src.agents.ai_agent.invoke_with_retry")
async def test_ai_agent_react(mock_invoke, ai_agent, mock_llm_client, round_context):
    expected_output = ReactionOutput(inner_thought="Surprised", public_statement="Wow!")
    mock_invoke.return_value = expected_output

    output = await ai_agent.react(context=round_context, is_eliminated_agent=True)
    
    assert output == expected_output
    assert len(ai_agent.action_logs) == 1
    assert ai_agent.action_logs[0].phase == Phase.REACTION
