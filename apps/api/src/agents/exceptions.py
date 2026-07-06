from src.models.enums import Phase


class AgentError(Exception):
    """Base class for all agent-related exceptions."""

    pass


class AgentOutputError(AgentError):
    """Raised when an agent completely fails to produce valid output after all retries."""

    def __init__(self, agent_id: str, phase: Phase, original_error: Exception) -> None:
        self.agent_id = agent_id
        self.phase = phase
        self.original_error = original_error
        super().__init__(
            f"Agent {agent_id} failed to produce valid output in phase {phase.value}. "
            f"Reason: {original_error}"
        )
