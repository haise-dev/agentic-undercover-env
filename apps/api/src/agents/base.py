from abc import ABC, abstractmethod

from src.models import (
    ActionLog,
    AgentConfig,
    AgentRoleAssignment,
    DeliberationOutput,
    Phase,
    PollingOutput,
    ReactionOutput,
    RoundContext,
    SpeakingOutput,
    VotingOutput,
)


class BaseAgent(ABC):
    """
    Abstract base class defining the strict contract for all agent types.
    Whether Human or AI, the game engine will invoke these methods for each phase.
    """

    def __init__(self, config: AgentConfig, role_assignment: AgentRoleAssignment) -> None:
        self.config = config
        self.role_assignment = role_assignment
        self.action_logs: list[ActionLog] = []

    @abstractmethod
    async def speak(self, context: RoundContext) -> SpeakingOutput:
        """Called during the SPEAKING phase."""
        pass

    @abstractmethod
    async def deliberate(self, context: RoundContext) -> DeliberationOutput:
        """Called during the DELIBERATION phase."""
        pass

    @abstractmethod
    async def poll(self, context: RoundContext) -> PollingOutput:
        """Called during the POLLING phase."""
        pass

    @abstractmethod
    async def vote(self, context: RoundContext) -> VotingOutput:
        """Called during the VOTING phase."""
        pass

    @abstractmethod
    async def react(self, context: RoundContext) -> ReactionOutput:
        """Called during the REACTION phase."""
        pass
