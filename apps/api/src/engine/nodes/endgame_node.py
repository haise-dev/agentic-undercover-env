from src.engine.event_emitter import EventEmitter
from src.models import EpisodeExport, GameState


async def endgame_node(state: GameState, emitter: EventEmitter) -> EpisodeExport:
    """
    Finalizes the game status, builds the EpisodeExport, and records log data.
    """
    raise NotImplementedError("endgame_node is not yet implemented — see E3-T6")
