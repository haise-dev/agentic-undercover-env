import pytest

from src.engine.nodes import endgame_node, reaction_node


async def test_node_stubs():
    with pytest.raises(NotImplementedError):
        await reaction_node(None, None, None)

    with pytest.raises(NotImplementedError):
        await endgame_node(None, None)
