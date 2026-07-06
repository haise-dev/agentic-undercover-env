from unittest.mock import AsyncMock, MagicMock
import pytest

from src.engine.graph import build_graph, to_graph_state
from src.engine.event_emitter import EventEmitter
from src.models import (
    Phase,
    SpeakingOutput,
    DeliberationOutput,
    PollingOutput,
    PollVote,
    VotingOutput,
    ReactionOutput,
)
from tests.unit.engine.conftest import MockAgent


@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


def test_build_graph_returns_compiled_graph(mock_emitter):
    agents = {}
    graph = build_graph(agents, mock_emitter)
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")
    # Verify expected nodes are present
    assert "speaking" in graph.nodes
    assert "deliberation" in graph.nodes
    assert "polling" in graph.nodes
    assert "voting" in graph.nodes
    assert "reaction" in graph.nodes


@pytest.mark.asyncio
async def test_compiled_graph_execution_path_to_voting(game_state, mock_emitter):
    # Set up mock outputs so that the graph completes
    # For polling, we return PollingOutput with vote_now=True to route to voting node immediately
    agents = {
        "agent_0": MockAgent(
            speak_outputs=[SpeakingOutput(inner_thought="t0", public_statement="s0")],
            deliberate_outputs=[
                DeliberationOutput(inner_thought="d0_1", public_statement="ds0_1"),
                DeliberationOutput(inner_thought="d0_2", public_statement="ds0_2"),
            ],
            poll_outputs=[PollingOutput(inner_thought="p0", poll_vote=PollVote.VOTE_NOW)],
            vote_outputs=[VotingOutput(inner_thought="v0", vote_target="agent_1")],
            react_outputs=[ReactionOutput(inner_thought="r0", public_statement="rs0")],
        ),
        "agent_1": MockAgent(
            speak_outputs=[SpeakingOutput(inner_thought="t1", public_statement="s1")],
            deliberate_outputs=[
                DeliberationOutput(inner_thought="d1_1", public_statement="ds1_1"),
                DeliberationOutput(inner_thought="d1_2", public_statement="ds1_2"),
            ],
            poll_outputs=[PollingOutput(inner_thought="p1", poll_vote=PollVote.VOTE_NOW)],
            vote_outputs=[VotingOutput(inner_thought="v1", vote_target="agent_0")],
            react_outputs=[ReactionOutput(inner_thought="r1", public_statement="rs1")],
        ),
        "agent_2": MockAgent(
            speak_outputs=[SpeakingOutput(inner_thought="t2", public_statement="s2")],
            deliberate_outputs=[
                DeliberationOutput(inner_thought="d2_1", public_statement="ds2_1"),
                DeliberationOutput(inner_thought="d2_2", public_statement="ds2_2"),
            ],
            poll_outputs=[PollingOutput(inner_thought="p2", poll_vote=PollVote.SKIP)],
            vote_outputs=[VotingOutput(inner_thought="v2", vote_target="agent_0")],
            react_outputs=[ReactionOutput(inner_thought="r2", public_statement="rs2")],
        ),
        "agent_3": MockAgent(
            speak_outputs=[SpeakingOutput(inner_thought="t3", public_statement="s3")],
            deliberate_outputs=[
                DeliberationOutput(inner_thought="d3_1", public_statement="ds3_1"),
                DeliberationOutput(inner_thought="d3_2", public_statement="ds3_2"),
            ],
            poll_outputs=[PollingOutput(inner_thought="p3", poll_vote=PollVote.SKIP)],
            vote_outputs=[VotingOutput(inner_thought="v3", vote_target="agent_0")],
            react_outputs=[ReactionOutput(inner_thought="r3", public_statement="rs3")],
        ),
    }

    graph = build_graph(agents, mock_emitter)
    
    # Wrap game_state (starts at Phase.INIT)
    graph_state = to_graph_state(game_state)
    
    # Run the graph
    final_state = await graph.ainvoke(graph_state)
    
    inner_state = final_state["game_state"]
    # Verify graph transitioned all the way to REACTION phase
    assert inner_state.current_phase == Phase.REACTION
    assert inner_state.current_round == 1

