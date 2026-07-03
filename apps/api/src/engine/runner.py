from src.core.redis import RedisClient
from src.engine.event_emitter import EventEmitter
from src.models import EpisodeConfig, EpisodeExport


class EpisodeRunner:
    """
    Orchestrates a full game episode through the linear pipeline:
    INIT → SPEAKING → VOTING → REACTION → ENDGAME.

    Usage:
        runner = EpisodeRunner(agents={...}, redis_client=client)
        export = await runner.run(config)
    """

    def __init__(self, agents: dict, redis_client: RedisClient) -> None:
        """
        Args:
            agents: Mapping of agent_id → agent instance. Must contain exactly 4 agents.
            redis_client: A live, connected RedisClient for event publishing.

        Raises:
            ValueError: if `agents` does not contain exactly 4 entries.
        """
        if len(agents) != 4:
            raise ValueError(
                f"EpisodeRunner requires exactly 4 agents, got {len(agents)}"
            )
        self._agents = agents
        self._redis_client = redis_client
        self._emitter: EventEmitter | None = None

    async def run(self, config: EpisodeConfig) -> EpisodeExport:
        """
        Runs a complete game episode. Calls each node in sequence.

        Emits events to Redis throughout the episode via self._emitter.
        Persists the completed EpisodeExport to PostgreSQL.

        Args:
            config: Full episode configuration including agent configs.

        Returns:
            Completed EpisodeExport with all action logs.

        Raises:
            EngineError: if the episode cannot complete for any reason.
        """
        # Set emitter when run starts
        self._emitter = EventEmitter(self._redis_client, config.episode_id)
        raise NotImplementedError(
            "EpisodeRunner.run() is not yet implemented — see E3-T7"
        )

    @property
    def emitter(self) -> EventEmitter | None:
        """
        Returns the EventEmitter for this episode runner,
        or None if run() has not started.
        """
        return self._emitter
