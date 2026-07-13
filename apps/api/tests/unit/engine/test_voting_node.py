import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.event_emitter import (
    EVT_ELIMINATION_RESULT,
    EVT_VOTE_CAST,
    EVT_VOTING_STARTED,
    EventEmitter,
)
from src.engine.exceptions import NodeError
from src.engine.nodes.voting_node import (
    _resolve_agent_id,
    voting_node,
)
from src.models import GameState, Phase, VotingOutput
from tests.unit.engine.conftest import MockAgent


# --- Mock EventEmitter fixture ---
@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


# --- Helper to create game state in voting phase ---
@pytest.fixture
def voting_state(game_state):
    game_state.current_phase = Phase.VOTING
    return game_state


# --- Helper to make VotingOutput concisely ---
def ok_vote(target: str, thought: str = "think") -> VotingOutput:
    return VotingOutput(inner_thought=thought, vote_target=target)


@pytest.mark.asyncio
async def test_voting_node_phase_guard(game_state, mock_emitter):
    # game_state starts at INIT phase by default
    agents = {}
    with pytest.raises(ValueError, match="voting_node requires Phase.VOTING"):
        await voting_node(game_state, agents, mock_emitter)

    game_state.current_phase = Phase.SPEAKING
    with pytest.raises(ValueError, match="voting_node requires Phase.VOTING"):
        await voting_node(game_state, agents, mock_emitter)


@pytest.mark.asyncio
async def test_voting_node_valid_vote_path(voting_state, mock_emitter):
    agents = {
        "agent_0": MockAgent(vote_outputs=[ok_vote("agent_1", "t0")]),
        "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2", "t1")]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_0", "t2")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0", "t3")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    # Alice voted agent_1, Bob voted agent_2, Charlie voted agent_0, Diana voted agent_0
    assert len(state.vote_records) == 4
    records_dict = {r.voter_agent_id: r for r in state.vote_records}

    assert records_dict["agent_0"].target_agent_id == "agent_1"
    assert records_dict["agent_0"].inner_thought == "t0"

    assert records_dict["agent_1"].target_agent_id == "agent_2"
    assert records_dict["agent_1"].inner_thought == "t1"

    assert records_dict["agent_2"].target_agent_id == "agent_0"
    assert records_dict["agent_2"].inner_thought == "t2"

    assert records_dict["agent_3"].target_agent_id == "agent_0"
    assert records_dict["agent_3"].inner_thought == "t3"


@pytest.mark.asyncio
async def test_voting_node_self_vote_rejection(voting_state, mock_emitter):
    agents = {
        "agent_0": MockAgent(vote_outputs=[
            ok_vote("agent_0", "self"),  # invalid
            ok_vote("agent_1", "valid"),
        ]),
        "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2")]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_3")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    # agent_0 should have 2 calls
    assert len(agents["agent_0"].vote_calls) == 2

    # accepted vote should be agent_1
    records_dict = {r.voter_agent_id: r for r in state.vote_records}
    assert records_dict["agent_0"].target_agent_id == "agent_1"
    assert records_dict["agent_0"].inner_thought == "valid"


@pytest.mark.asyncio
async def test_voting_node_self_vote_fallback(voting_state, mock_emitter):
    agents = {
        # Both attempts are self-votes
        "agent_0": MockAgent(vote_outputs=[
            ok_vote("agent_0", "self1"),
            ok_vote("agent_0", "self2"),
        ]),
        "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2")]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_3")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    assert len(agents["agent_0"].vote_calls) == 2

    records_dict = {r.voter_agent_id: r for r in state.vote_records}
    # Target must be one of the other agents
    assert records_dict["agent_0"].target_agent_id in ["agent_1", "agent_2", "agent_3"]
    assert records_dict["agent_0"].inner_thought == ""


@pytest.mark.asyncio
async def test_voting_node_dead_agent_vote_rejection(voting_state, mock_emitter):
    # Simulate agent_1 is dead
    voting_state.agent_alive["agent_1"] = False
    voting_state.current_turn_order = ["agent_0", "agent_2", "agent_3"]

    agents = {
        "agent_0": MockAgent(vote_outputs=[
            ok_vote("agent_1", "dead"),  # invalid
            ok_vote("agent_2", "valid"),
        ]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_3")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    assert len(agents["agent_0"].vote_calls) == 2

    records_dict = {r.voter_agent_id: r for r in state.vote_records}
    assert records_dict["agent_0"].target_agent_id == "agent_2"
    assert records_dict["agent_0"].inner_thought == "valid"


@pytest.mark.asyncio
async def test_voting_node_dead_agent_vote_fallback(voting_state, mock_emitter):
    # agent_1 is dead
    voting_state.agent_alive["agent_1"] = False
    voting_state.current_turn_order = ["agent_0", "agent_2", "agent_3"]

    agents = {
        "agent_0": MockAgent(vote_outputs=[
            ok_vote("agent_1", "dead1"),
            ok_vote("agent_1", "dead2"),
        ]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_3")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    assert len(agents["agent_0"].vote_calls) == 2

    records_dict = {r.voter_agent_id: r for r in state.vote_records}
    assert records_dict["agent_0"].target_agent_id in ["agent_2", "agent_3"]
    assert records_dict["agent_0"].inner_thought == ""


@pytest.mark.asyncio
async def test_voting_node_exception_fallback(voting_state, mock_emitter):
    agents = {
        "agent_0": MockAgent(vote_outputs=[
            ValueError("LLM Timeout 1"),
            ValueError("LLM Timeout 2"),
        ]),
        "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2")]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_3")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    assert len(agents["agent_0"].vote_calls) == 2

    records_dict = {r.voter_agent_id: r for r in state.vote_records}
    assert records_dict["agent_0"].target_agent_id in ["agent_1", "agent_2", "agent_3"]
    assert records_dict["agent_0"].inner_thought == ""


def test_resolve_agent_id_helper(voting_state):
    # Valid direct agent_id
    assert _resolve_agent_id("agent_1", voting_state) == "agent_1"

    # Valid display name (case-insensitive and whitespace)
    assert _resolve_agent_id("Bob", voting_state) == "agent_1"
    assert _resolve_agent_id("  bob  ", voting_state) == "agent_1"

    # Dead agent (Charlie is agent_2)
    voting_state.agent_alive["agent_2"] = False
    assert _resolve_agent_id("agent_2", voting_state) is None
    assert _resolve_agent_id("Charlie", voting_state) is None

    # Non-existent target
    assert _resolve_agent_id("agent_99", voting_state) is None
    assert _resolve_agent_id("Nonexistent", voting_state) is None

    # Invalid input types
    assert _resolve_agent_id(None, voting_state) is None
    assert _resolve_agent_id(123, voting_state) is None


@pytest.mark.asyncio
async def test_voting_node_tally_and_elimination(voting_state, mock_emitter):
    # Alice (0) -> Bob (1)
    # Bob (1) -> Charlie (2)
    # Charlie (2) -> Alice (0)
    # Diana (3) -> Alice (0)
    # Tally: agent_0: 2 votes, agent_1: 1 vote, agent_2: 1 vote, agent_3: 0 votes
    # Highest: agent_0 (Alice)
    agents = {
        "agent_0": MockAgent(vote_outputs=[ok_vote("agent_1")]),
        "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2")]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_0")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
    }

    state = await voting_node(voting_state, agents, mock_emitter)

    assert state.agent_alive["agent_0"] is False
    assert state.agent_alive["agent_1"] is True
    assert state.agent_alive["agent_2"] is True
    assert state.agent_alive["agent_3"] is True

    res = state.elimination_result
    assert res is not None
    assert res.eliminated_agent_id == "agent_0"
    assert res.vote_tally == {"agent_1": 1, "agent_2": 1, "agent_0": 2}
    assert res.was_tiebreak is False
    assert res.tiebreak_candidates is None


@pytest.mark.asyncio
async def test_voting_node_no_valid_targets_raises_node_error(
    voting_state, mock_emitter
):
    # If all agents except agent_0 are dead, and we are evaluating agent_0:
    # wait, if all other agents are dead, can agent_0 vote?
    # Let's set agent_1, agent_2, agent_3 to dead.
    voting_state.agent_alive = {
        "agent_0": True,
        "agent_1": False,
        "agent_2": False,
        "agent_3": False,
    }
    voting_state.current_turn_order = ["agent_0"]

    agents = {
        "agent_0": MockAgent(vote_outputs=[ok_vote("agent_1")]),
    }

    with pytest.raises(NodeError, match="No valid voting targets for agent"):
        await voting_node(voting_state, agents, mock_emitter)


# --- Event emission integration tests (S2) ---

@pytest.mark.asyncio
async def test_voting_node_event_emission_integration(
    voting_state, fake_redis, fake_redis_client
):
    emitter = EventEmitter(fake_redis_client, voting_state.episode_id)

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(emitter.channel)
    await asyncio.sleep(0.01)

    agents = {
        "agent_0": MockAgent(vote_outputs=[ok_vote("agent_1", "t0")]),
        "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2", "t1")]),
        "agent_2": MockAgent(vote_outputs=[ok_vote("agent_0", "t2")]),
        "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0", "t3")]),
    }

    state = await voting_node(voting_state, agents, emitter)

    # Retrieve all 6 events
    events = []
    async for m in pubsub.listen():
        if m["type"] == "message":
            events.append(json.loads(m["data"].decode("utf-8")))
            if len(events) == 6:
                break

    assert len(events) == 6

    # Verify first event is VOTING_STARTED
    assert events[0]["event_type"] == EVT_VOTING_STARTED

    # Verify next 4 events are VOTE_CAST
    vote_cast_voters = []
    for i in range(1, 5):
        evt = events[i]
        assert evt["event_type"] == EVT_VOTE_CAST
        assert evt["episode_id"] == voting_state.episode_id
        
        payload = evt["payload"]
        assert payload["round_number"] == voting_state.current_round
        assert "voter_agent_id" in payload
        assert "target_agent_id" in payload
        assert "inner_thought" in payload  # Now included for UI experience

        vote_cast_voters.append(payload["voter_agent_id"])

    # Ordering is based on turn_order iteration (stable order)
    assert vote_cast_voters == ["agent_0", "agent_1", "agent_2", "agent_3"]

    # Verify 6th event is ELIMINATION_RESULT
    evt_elim = events[5]
    assert evt_elim["event_type"] == EVT_ELIMINATION_RESULT
    assert evt_elim["episode_id"] == voting_state.episode_id
    
    payload = evt_elim["payload"]
    expected_elim = state.elimination_result.eliminated_agent_id
    assert payload["eliminated_agent_id"] == expected_elim
    assert payload["was_tiebreak"] == state.elimination_result.was_tiebreak
    assert payload["vote_tally"] == state.elimination_result.vote_tally
    assert payload["round_number"] == voting_state.current_round


# --- Statistical and concurrency tests (S3) ---

@pytest.mark.asyncio
async def test_voting_node_concurrency_statistical(voting_state, mock_emitter):
    # Setup mock agents where each agent sleeps for 50ms inside vote()
    class SlowMockAgent:
        async def vote(self, context):
            await asyncio.sleep(0.05)
            return ok_vote("agent_1")

    agents = {
        "agent_0": SlowMockAgent(),
        "agent_1": SlowMockAgent(),
        "agent_2": SlowMockAgent(),
        "agent_3": SlowMockAgent(),
    }

    start_time = time.perf_counter()
    await voting_node(voting_state, agents, mock_emitter)
    duration = time.perf_counter() - start_time

    # If executed concurrently, total time should be close to 50ms (<150ms).
    # If sequential, total time would be >= 200ms.
    assert duration < 0.15


@pytest.mark.asyncio
async def test_voting_node_tie_breaking_uniformity(voting_state, mock_emitter):
    # Alice (0) -> Bob (1)
    # Bob (1) -> Alice (0)
    # Charlie (2) -> Bob (1)
    # Diana (3) -> Alice (0)
    # Tally: agent_0 (Alice): 2, agent_1 (Bob): 2
    # This is a 2-way tie. Both should have a chance to be eliminated.
    eliminations = set()

    for _ in range(100):
        # We need fresh state for each run so agent_alive is reset
        state = GameState(
            episode_id=voting_state.episode_id,
            config=voting_state.config,
            role_assignments=voting_state.role_assignments,
            current_turn_order=["agent_0", "agent_1", "agent_2", "agent_3"],
            current_phase=Phase.VOTING,
            agent_alive={
                "agent_0": True,
                "agent_1": True,
                "agent_2": True,
                "agent_3": True,
            },
            started_at=voting_state.started_at,
        )

        agents = {
            "agent_0": MockAgent(vote_outputs=[ok_vote("agent_1")]),
            "agent_1": MockAgent(vote_outputs=[ok_vote("agent_0")]),
            "agent_2": MockAgent(vote_outputs=[ok_vote("agent_1")]),
            "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
        }

        ret_state = await voting_node(state, agents, mock_emitter)
        eliminations.add(ret_state.elimination_result.eliminated_agent_id)

    # Both agent_0 and agent_1 must have been eliminated at least once
    assert eliminations == {"agent_0", "agent_1"}


@pytest.mark.asyncio
async def test_voting_node_fallback_uniformity(voting_state, mock_emitter):
    # agent_0 fails both attempts -> falls back to random target
    # Validate that fallback targets are distributed and not always same
    fallback_targets = set()

    for _ in range(100):
        state = GameState(
            episode_id=voting_state.episode_id,
            config=voting_state.config,
            role_assignments=voting_state.role_assignments,
            current_turn_order=["agent_0", "agent_1", "agent_2", "agent_3"],
            current_phase=Phase.VOTING,
            agent_alive={
                "agent_0": True,
                "agent_1": True,
                "agent_2": True,
                "agent_3": True,
            },
            started_at=voting_state.started_at,
        )

        agents = {
            "agent_0": MockAgent(vote_outputs=[
                ValueError("Timeout 1"),
                ValueError("Timeout 2"),
            ]),
            "agent_1": MockAgent(vote_outputs=[ok_vote("agent_2")]),
            "agent_2": MockAgent(vote_outputs=[ok_vote("agent_3")]),
            "agent_3": MockAgent(vote_outputs=[ok_vote("agent_0")]),
        }

        ret_state = await voting_node(state, agents, mock_emitter)
        
        # Extract Alice's VoteRecord
        alice_record = next(
            r for r in ret_state.vote_records if r.voter_agent_id == "agent_0"
        )
        fallback_targets.add(alice_record.target_agent_id)

    # With 100 runs, Alice should have randomly voted for agent_1, agent_2, and agent_3
    assert fallback_targets == {"agent_1", "agent_2", "agent_3"}
