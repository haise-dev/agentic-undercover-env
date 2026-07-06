from typing import TypedDict

from src.models import GameState


class GraphState(TypedDict):
    """
    LangGraph-specific state wrapper for GameState.
    Allows passing mutable GameState by reference while maintaining compatibility
    with LangGraph's TypedDict state requirements.
    """

    game_state: GameState
    proceed_to_vote: bool


def to_graph_state(game_state: GameState) -> GraphState:
    """Wraps Pydantic GameState into LangGraph GraphState."""
    return {
        "game_state": game_state,
        "proceed_to_vote": False,
    }


def to_game_state(graph_state: GraphState) -> GameState:
    """Extracts Pydantic GameState from LangGraph GraphState."""
    return graph_state["game_state"]
