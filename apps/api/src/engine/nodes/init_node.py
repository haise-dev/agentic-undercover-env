import random
from datetime import UTC, datetime

from src.engine.event_emitter import EVT_GAME_START, EventEmitter
from src.models import (
    AgentRoleAssignment,
    EpisodeConfig,
    GameState,
    Phase,
    Role,
)


async def init_node(config: EpisodeConfig, emitter: EventEmitter) -> GameState:
    """
    Initializes a new game episode.

    Steps:
    1. Randomly selects 1 agent as Imposter (the rest are Villagers).
    2. Creates AgentRoleAssignment for each agent:
       - Imposter: role=IMPOSTER, secret_word=None, topic=config.topic
       - Villager: role=VILLAGER, secret_word=config.secret_word, topic=config.topic
    3. Generates a random turn order (shuffled permutation of all agent IDs).
    4. Constructs and returns the initial GameState.
    5. Emits EVT_GAME_START event via emitter.

    Args:
        config: Episode configuration. Must have exactly 4 agents
                (validated by EpisodeConfig).
        emitter: EventEmitter connected to this episode's Redis channel.

    Returns:
        GameState at Phase.INIT with all agents alive and turn_order set.
        Caller (EpisodeRunner) transitions to Phase.SPEAKING before
        speaking_node().
    """
    agent_ids = [agent.agent_id for agent in config.agents]

    # Step 1: Randomly select imposter
    imposter_id = random.sample(agent_ids, 1)[0]

    # Step 2: Create role assignments
    role_assignments: dict[str, AgentRoleAssignment] = {}
    for agent in config.agents:
        if agent.agent_id == imposter_id:
            role_assignments[agent.agent_id] = AgentRoleAssignment(
                agent_id=agent.agent_id,
                role=Role.IMPOSTER,
                secret_word=None,
                topic=config.topic,
            )
        else:
            role_assignments[agent.agent_id] = AgentRoleAssignment(
                agent_id=agent.agent_id,
                role=Role.VILLAGER,
                secret_word=config.secret_word,
                topic=config.topic,
            )

    # Step 3: Random turn order
    turn_order = random.sample(agent_ids, len(agent_ids))

    # Step 4: Construct GameState
    state = GameState(
        episode_id=config.episode_id,
        config=config,
        role_assignments=role_assignments,
        current_turn_order=turn_order,
        current_phase=Phase.INIT,
        current_round=1,
        current_deliberation_round=1,
        agent_alive=dict.fromkeys(agent_ids, True),
        started_at=datetime.now(UTC).isoformat(),
    )

    # Step 5: Emit GAME_START event
    await emitter.emit(
        EVT_GAME_START,
        _build_game_start_payload(config, turn_order),
    )

    return state


def _build_game_start_payload(
    config: EpisodeConfig, turn_order: list[str]
) -> dict:
    """
    Builds the GAME_START event payload.
    Deliberately excludes roles and secret_word to avoid spoilers for observers.

    Fields:
      - episode_id: str
      - topic: str          # Category label ("Fruit"), NOT the secret word
      - agents: list[dict]  # display info only — no role/secret
      - turn_order: list[str]  # initial speaking order for Round 1
    """
    return {
        "episode_id": config.episode_id,
        "topic": config.topic,
        "agents": [
            {
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "display_color": agent.display_color,
                "agent_type": agent.agent_type,
            }
            for agent in config.agents
        ],
        "turn_order": turn_order,
    }
