class EngineError(Exception):
    """
    Top-level engine error. Raised when the game engine cannot proceed.
    Wraps lower-level errors with additional episode context.
    """
    def __init__(self, message: str, episode_id: str | None = None) -> None:
        super().__init__(message)
        self.episode_id = episode_id


class NodeError(EngineError):
    """
    Raised when a specific engine node fails after exhausting retries.
    """
    def __init__(
        self,
        message: str,
        node_name: str,
        episode_id: str | None = None,
    ) -> None:
        super().__init__(message, episode_id)
        self.node_name = node_name


class AgentOutputError(NodeError):
    """
    Raised when an agent produces invalid structured output after all retry attempts.
    """
    def __init__(
        self,
        message: str,
        agent_id: str,
        phase: str,
        episode_id: str | None = None,
    ) -> None:
        super().__init__(message, node_name=f"{phase}_node", episode_id=episode_id)
        self.agent_id = agent_id
        self.phase = phase
