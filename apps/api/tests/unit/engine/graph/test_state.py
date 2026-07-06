import pytest
from src.models import GameState
from src.engine.graph.state import to_graph_state, to_game_state

@pytest.fixture
def mock_game_state(episode_config):
    # Construct a simple GameState with minimal fields using conftest setup
    from src.models import Phase
    from datetime import datetime, UTC
    agent_ids = [agent.agent_id for agent in episode_config.agents]
    return GameState(
        episode_id=episode_config.episode_id,
        config=episode_config,
        role_assignments={},
        current_turn_order=agent_ids,
        current_phase=Phase.INIT,
        current_round=1,
        current_deliberation_round=1,
        agent_alive={aid: True for aid in agent_ids},
        started_at=datetime.now(UTC).isoformat(),
    )

def test_bidirectional_conversion(mock_game_state):
    # GameState -> GraphState
    graph_state = to_graph_state(mock_game_state)
    assert isinstance(graph_state, dict)
    assert "game_state" in graph_state
    
    # GraphState -> GameState
    restored_game_state = to_game_state(graph_state)
    
    # Assert identity is preserved (pass-by-reference)
    assert restored_game_state is mock_game_state
    assert restored_game_state.episode_id == mock_game_state.episode_id
