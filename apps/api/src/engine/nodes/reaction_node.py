from src.engine.event_emitter import EventEmitter
from src.models import GameState


async def reaction_node(
    state: GameState,
    agents: dict,
    emitter: EventEmitter,
) -> GameState:
    """
    Runs the reaction sequence after elimination.
    """
    raise NotImplementedError("reaction_node is not yet implemented — see E3-T5")
