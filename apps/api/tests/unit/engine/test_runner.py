import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.runner import EpisodeRunner
from src.engine import RateLimitError
from src.engine.event_emitter import (
    EventEmitter,
    EVT_GAME_START,
    EVT_GAME_OVER,
    EVT_GAME_ERROR,
    EVT_ROUND_STARTED,
    EVT_AGENT_SPOKE,
    EVT_AGENT_DELIBERATED,
    EVT_POLL_RESULT,
    EVT_VOTE_CAST,
    EVT_ELIMINATION_RESULT,
    EVT_LAST_WORDS,
    EVT_ROLE_REVEAL,
    EVT_SURVIVOR_REACTED,
)
from src.models import (
    EpisodeExport,
    Phase,
    ActionLog,
    SpeakingOutput,
    DeliberationOutput,
    PollingOutput,
    PollVote,
    VotingOutput,
    ReactionOutput,
)
from tests.unit.engine.conftest import MockAgent


def test_runner_init_validation():
    mock_redis = MagicMock()

    valid_agents = {"a1": 1, "a2": 2, "a3": 3, "a4": 4}
    runner = EpisodeRunner(valid_agents, mock_redis)
    assert runner is not None
    assert runner.emitter is None

    invalid_3 = {"a1": 1, "a2": 2, "a3": 3}
    with pytest.raises(ValueError) as exc_info:
        EpisodeRunner(invalid_3, mock_redis)
    assert "EpisodeRunner requires exactly 4 agents" in str(exc_info.value)

    invalid_5 = {"a1": 1, "a2": 2, "a3": 3, "a4": 4, "a5": 5}
    with pytest.raises(ValueError) as exc_info:
        EpisodeRunner(invalid_5, mock_redis)
    assert "EpisodeRunner requires exactly 4 agents" in str(exc_info.value)


@pytest.mark.asyncio
@patch("src.engine.nodes.endgame_node.EpisodeRepository.create", new_callable=AsyncMock)
async def test_runner_full_linear_pipeline(
    mock_repo_create, episode_config, fake_redis, fake_redis_client
):
    mock_db_session = MagicMock(spec=AsyncSession)

    # Prepare Mock Agents with simple valid outputs
    def ok_speak(msg):
        return SpeakingOutput(inner_thought="think", public_statement=msg)

    def ok_deliberate(msg):
        return DeliberationOutput(inner_thought="think", public_statement=msg)

    def ok_poll(vote):
        return PollingOutput(inner_thought="think", poll_vote=vote)

    def ok_vote(target):
        return VotingOutput(inner_thought="think", vote_target=target)

    def ok_react(msg):
        return ReactionOutput(inner_thought="think", public_statement=msg)

    # Let's say agents vote for agent_1
    agents = {
        "agent_0": MockAgent(
            speak_outputs=[ok_speak("S0")],
            deliberate_outputs=[ok_deliberate("D0_1"), ok_deliberate("D0_2")],
            poll_outputs=[ok_poll(PollVote.VOTE_NOW)],
            vote_outputs=[ok_vote("agent_1")],
            react_outputs=[ok_react("R0")],
        ),
        "agent_1": MockAgent(
            speak_outputs=[ok_speak("S1")],
            deliberate_outputs=[ok_deliberate("D1_1"), ok_deliberate("D1_2")],
            poll_outputs=[ok_poll(PollVote.VOTE_NOW)],
            vote_outputs=[ok_vote("agent_2")],
            react_outputs=[ok_react("Last Words")],  # agent_1 gets eliminated
        ),
        "agent_2": MockAgent(
            speak_outputs=[ok_speak("S2")],
            deliberate_outputs=[ok_deliberate("D2_1"), ok_deliberate("D2_2")],
            poll_outputs=[ok_poll(PollVote.VOTE_NOW)],
            vote_outputs=[ok_vote("agent_1")],
            react_outputs=[ok_react("R2")],
        ),
        "agent_3": MockAgent(
            speak_outputs=[ok_speak("S3")],
            deliberate_outputs=[ok_deliberate("D3_1"), ok_deliberate("D3_2")],
            poll_outputs=[ok_poll(PollVote.VOTE_NOW)],
            vote_outputs=[ok_vote("agent_1")],
            react_outputs=[ok_react("R3")],
        ),
    }

    # Assign some dummy action logs to one agent
    dummy_log = ActionLog(
        episode_id=episode_config.episode_id,
        agent_id="agent_0",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={},
        raw_llm_response="raw",
        structured_output={},
        total_tokens=100,
        timestamp="2026-07-06T00:00:00Z",
    )
    agents["agent_0"].action_logs = [dummy_log]

    runner = EpisodeRunner(agents, fake_redis_client)

    # Subscribe to pubsub to catch all events
    pubsub = fake_redis.pubsub()
    # Emitter channel is `episode:{episode_id}`
    channel = f"episode:{episode_config.episode_id}"
    await pubsub.subscribe(channel)
    await asyncio.sleep(0.01)

    export = await runner.run(episode_config, mock_db_session)

    # Verify the run completed and returned Export
    assert isinstance(export, EpisodeExport)
    assert export.episode_id == episode_config.episode_id
    assert export.elimination_result.eliminated_agent_id == "agent_1"

    # Verify action logs were extracted
    assert len(export.action_logs) == 1
    assert export.action_logs[0] == dummy_log

    # Verify DB save was called
    mock_repo_create.assert_awaited_once()

    # Collect and verify events
    events = []
    async for m in pubsub.listen():
        if m["type"] == "message":
            events.append(json.loads(m["data"].decode("utf-8")))
            # Total events = 26:
            # 1 GAME_START + 1 ROUND_STARTED + 4 AGENT_SPOKE + 8 AGENT_DELIBERATED + 1 POLL_RESULT + 4 VOTE_CAST + 1 ELIMINATION_RESULT + 1 LAST_WORDS + 1 ROLE_REVEAL + 3 SURVIVOR_REACTED + 1 GAME_OVER
            if len(events) >= 26:
                break

    assert len(events) == 26
    event_types = [e["event_type"] for e in events]
    
    assert event_types[0] == EVT_GAME_START
    assert event_types[1] == EVT_ROUND_STARTED
    assert event_types[2:6] == [EVT_AGENT_SPOKE] * 4
    # Deliberation events can come in shuffled turn order, but should be 8 of them
    assert event_types[6:14] == [EVT_AGENT_DELIBERATED] * 8
    assert event_types[14] == EVT_POLL_RESULT
    # Votes can come in any order because they are concurrent
    assert set(event_types[15:19]) == {EVT_VOTE_CAST}
    assert event_types[19] == EVT_ELIMINATION_RESULT
    assert event_types[20] == EVT_LAST_WORDS
    assert event_types[21] == EVT_ROLE_REVEAL
    # Reactions can come in any order
    assert set(event_types[22:25]) == {EVT_SURVIVOR_REACTED}
    assert event_types[25] == EVT_GAME_OVER


@pytest.mark.asyncio
async def test_runner_rate_limit_error(episode_config, fake_redis, fake_redis_client):
    mock_db_session = MagicMock(spec=AsyncSession)

    def ok_speak(msg):
        return SpeakingOutput(inner_thought="think", public_statement=msg)

    # Let agent_0 raise RateLimitError during speak phase.
    # Note: MockAgent speak() is called up to _MAX_SPEAK_ATTEMPTS = 2.
    # We must provide two instances of RateLimitError so it raises on both attempts.
    agents = {
        "agent_0": MockAgent(speak_outputs=[
            RateLimitError("Rate limit hit", provider="openai"),
            RateLimitError("Rate limit hit", provider="openai"),
        ]),
        "agent_1": MockAgent(speak_outputs=[ok_speak("S1")]),
        "agent_2": MockAgent(speak_outputs=[ok_speak("S2")]),
        "agent_3": MockAgent(speak_outputs=[ok_speak("S3")]),
    }

    runner = EpisodeRunner(agents, fake_redis_client)

    # Execution should raise RateLimitError
    with pytest.raises(RateLimitError) as exc_info:
        await runner.run(episode_config, mock_db_session)
    
    assert exc_info.value.provider == "openai"
    assert "Rate limit hit" in str(exc_info.value)

    # Collect and verify emitted events
    raw_events = await fake_redis_client.lrange(f"episode_events:{episode_config.episode_id}", 0, -1)
    events = [json.loads(e) for e in raw_events]

    assert len(events) >= 3
    event_types = [e["event_type"] for e in events]
    assert event_types[0] == EVT_GAME_START
    assert event_types[1] == EVT_ROUND_STARTED
    assert event_types[-1] == EVT_GAME_ERROR
    
    error_event = next(e for e in events if e["event_type"] == EVT_GAME_ERROR)
    error_payload = error_event["payload"]
    assert error_payload["error_type"] == "rate_limit"
    assert error_payload["provider"] == "openai"
    assert "Rate limit hit" in error_payload["details"]


@pytest.mark.asyncio
async def test_runner_generic_error(episode_config, fake_redis, fake_redis_client):
    mock_db_session = MagicMock(spec=AsyncSession)
    from src.engine import AgentOutputError

    def ok_speak(msg):
        return SpeakingOutput(inner_thought="think", public_statement=msg)

    # Let agent_0 raise a generic ValueError during speak phase.
    # We provide two instances because _MAX_SPEAK_ATTEMPTS = 2.
    agents = {
        "agent_0": MockAgent(speak_outputs=[
            ValueError("Unexpected connection crash"),
            ValueError("Unexpected connection crash"),
        ]),
        "agent_1": MockAgent(speak_outputs=[ok_speak("S1")]),
        "agent_2": MockAgent(speak_outputs=[ok_speak("S2")]),
        "agent_3": MockAgent(speak_outputs=[ok_speak("S3")]),
    }

    runner = EpisodeRunner(agents, fake_redis_client)

    # Execution should raise AgentOutputError (wrapping ValueError)
    with pytest.raises(AgentOutputError) as exc_info:
        await runner.run(episode_config, mock_db_session)
    
    assert "Unexpected connection crash" in str(exc_info.value)

    # Collect and verify emitted events
    raw_events = await fake_redis_client.lrange(f"episode_events:{episode_config.episode_id}", 0, -1)
    events = [json.loads(e) for e in raw_events]

    assert len(events) >= 3
    event_types = [e["event_type"] for e in events]
    assert event_types[0] == EVT_GAME_START
    assert event_types[1] == EVT_ROUND_STARTED
    assert event_types[-1] == EVT_GAME_ERROR
    
    error_event = next(e for e in events if e["event_type"] == EVT_GAME_ERROR)
    error_payload = error_event["payload"]
    assert error_payload["error_type"] == "unknown"
    assert error_payload["provider"] == "unknown"
    assert "Unexpected connection crash" in error_payload["details"]

