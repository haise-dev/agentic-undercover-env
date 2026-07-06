from src.agents.base import BaseAgent
from src.models import (
    DeliberationOutput,
    PollingOutput,
    ReactionOutput,
    RoundContext,
    SpeakingOutput,
    VotingOutput,
)


class HumanAgent(BaseAgent):
    """
    Stub for a Human Player agent.
    Out of scope for Sprint 1, so all methods raise NotImplementedError.
    """

    async def speak(self, context: RoundContext) -> SpeakingOutput:
        raise NotImplementedError("Human agents are out of scope for Sprint 1")

    async def deliberate(self, context: RoundContext) -> DeliberationOutput:
        raise NotImplementedError("Human agents are out of scope for Sprint 1")

    async def poll(self, context: RoundContext) -> PollingOutput:
        raise NotImplementedError("Human agents are out of scope for Sprint 1")

    async def vote(self, context: RoundContext) -> VotingOutput:
        raise NotImplementedError("Human agents are out of scope for Sprint 1")

    async def react(self, context: RoundContext) -> ReactionOutput:
        raise NotImplementedError("Human agents are out of scope for Sprint 1")
