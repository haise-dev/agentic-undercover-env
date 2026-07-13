from src.engine.graph.state import GraphState, to_graph_state
from src.engine.graph.routers import poll_router, route_dynamic_deliberation
from src.models import DeliberationIntent, Phase, PublicMessage


def test_poll_router_proceed_true():
    # If proceed_to_vote is True, route to voting_node
    state: GraphState = {
        "game_state": None,  # Router doesn't access game_state directly
        "proceed_to_vote": True,
    }
    assert poll_router(state) == "voting_node"


def test_poll_router_proceed_false():
    # If proceed_to_vote is False, route to speaking_node
    state: GraphState = {
        "game_state": None,
        "proceed_to_vote": False,
    }
    assert poll_router(state) == "speaking_node"


def test_poll_router_missing_key():
    # If proceed_to_vote key is missing, defaults to speaking_node
    state: GraphState = {
        "game_state": None,
    }
    assert poll_router(state) == "speaking_node"


def test_route_dynamic_deliberation_budget_exhausted(game_state):
    game_state.deliberation_message_count = 16  # alive_count (4) * 4
    state = to_graph_state(game_state)
    assert route_dynamic_deliberation(state) == "polling"


def test_route_dynamic_deliberation_priority_1_rebuttal(game_state):
    game_state.deliberation_message_count = 2
    # Add an ACCUSE message targeting Bob (agent_1)
    msg = PublicMessage(
        agent_id="agent_0",
        display_name="Alice",
        phase=Phase.DELIBERATION,
        round_number=1,
        content="I accuse Bob",
        timestamp="2026-07-02T10:00:00Z",
        intent=DeliberationIntent.ACCUSE,
        target_name="Bob",
    )
    game_state.all_messages.append(msg)
    state = to_graph_state(game_state)
    
    assert route_dynamic_deliberation(state) == "deliberation"
    assert game_state.next_speaker_id == "agent_1"


def test_route_dynamic_deliberation_priority_1_ignored_if_must_speak(game_state):
    # Total budget = 16. remaining = 2.
    # agents alive: 4. turns_count: agent_0: 2, agent_1: 2, agent_2: 0, agent_3: 0.
    # turns needed = (2 - 0) + (2 - 0) = 4.
    # Since remaining (2) < turns needed (4), we are in must-speak mode.
    # So we should ignore rebuttal and pick one of the 0-turn agents.
    game_state.deliberation_message_count = 14
    game_state.turns_count = {
        "agent_0": 2,
        "agent_1": 2,
        "agent_2": 0,
        "agent_3": 0,
    }
    msg = PublicMessage(
        agent_id="agent_0",
        display_name="Alice",
        phase=Phase.DELIBERATION,
        round_number=1,
        content="I accuse Bob",
        timestamp="2026-07-02T10:00:00Z",
        intent=DeliberationIntent.ACCUSE,
        target_name="Bob",  # Bob is agent_1
    )
    game_state.all_messages.append(msg)
    state = to_graph_state(game_state)
    
    assert route_dynamic_deliberation(state) == "deliberation"
    # next speaker must be agent_2 or agent_3 (0 turns), not agent_1 (the target)
    assert game_state.next_speaker_id in ("agent_2", "agent_3")


def test_route_dynamic_deliberation_priority_2_zero_turn(game_state):
    game_state.deliberation_message_count = 1
    game_state.turns_count = {"agent_0": 1}
    state = to_graph_state(game_state)
    
    assert route_dynamic_deliberation(state) == "deliberation"
    # next speaker must be agent_1, agent_2, or agent_3 (0 turns)
    assert game_state.next_speaker_id in ("agent_1", "agent_2", "agent_3")


def test_route_dynamic_deliberation_priority_3_one_turn(game_state):
    game_state.deliberation_message_count = 4
    game_state.turns_count = {
        "agent_0": 2,
        "agent_1": 2,
        "agent_2": 1,
        "agent_3": 1,
    }
    state = to_graph_state(game_state)
    
    assert route_dynamic_deliberation(state) == "deliberation"
    # next speaker must be agent_2 or agent_3 (1 turn)
    assert game_state.next_speaker_id in ("agent_2", "agent_3")


def test_route_dynamic_deliberation_priority_4_free_for_all(game_state):
    game_state.deliberation_message_count = 8
    game_state.turns_count = {
        "agent_0": 2,
        "agent_1": 2,
        "agent_2": 2,
        "agent_3": 2,
    }
    state = to_graph_state(game_state)
    
    assert route_dynamic_deliberation(state) == "deliberation"
    # next speaker can be any alive agent
    assert game_state.next_speaker_id in ("agent_0", "agent_1", "agent_2", "agent_3")

