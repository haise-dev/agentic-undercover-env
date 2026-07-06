from src.engine.graph.state import GraphState
from src.engine.graph.routers import poll_router


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
