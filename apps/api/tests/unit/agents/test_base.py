import pytest

from src.agents.base import BaseAgent
from src.models import (
    AgentConfig,
    AgentRoleAssignment,
    AgentType,
    DeliberationOutput,
    Phase,
    PollingOutput,
    ReactionOutput,
    RoundContext,
    SpeakingOutput,
    VotingOutput,
)


def test_base_agent_cannot_be_instantiated_directly():
    """Verify that BaseAgent is an abstract class and cannot be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class BaseAgent"):
        BaseAgent(config=None, role_assignment=None)


def test_subclass_missing_methods_raises_type_error():
    """Verify that a subclass missing required abstract methods raises TypeError."""

    class IncompleteAgent(BaseAgent):
        # Missing all abstract methods
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class IncompleteAgent"):
        IncompleteAgent(config=None, role_assignment=None)


def test_subclass_with_all_methods_can_be_instantiated(make_agent_config, role_assignments):
    """Verify that a subclass implementing all methods can be instantiated and has action_logs."""

    class CompleteAgent(BaseAgent):
        async def speak(self, context: RoundContext) -> SpeakingOutput:
            pass

        async def deliberate(self, context: RoundContext) -> DeliberationOutput:
            pass

        async def poll(self, context: RoundContext) -> PollingOutput:
            pass

        async def vote(self, context: RoundContext) -> VotingOutput:
            pass

        async def react(self, context: RoundContext) -> ReactionOutput:
            pass

    config = make_agent_config(0, AgentType.AI)
    role_assignment = role_assignments["agent_0"]
    agent = CompleteAgent(config=config, role_assignment=role_assignment)

    assert agent.config == config
    assert agent.role_assignment == role_assignment
    assert agent.action_logs == []  # Should initialize with empty list
