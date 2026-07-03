import pytest
from pydantic import ValidationError

from src.models.assignment import AgentRoleAssignment
from src.models.enums import Role


def test_villager_assignment():
    assignment = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    assert assignment.agent_id == "agent_1"
    assert assignment.role == Role.VILLAGER
    assert assignment.secret_word == "Durian"
    assert assignment.topic == "Fruit"


def test_imposter_assignment():
    assignment = AgentRoleAssignment(
        agent_id="agent_0", role=Role.IMPOSTER, secret_word=None, topic="Fruit"
    )
    assert assignment.agent_id == "agent_0"
    assert assignment.role == Role.IMPOSTER
    assert assignment.secret_word is None
    assert assignment.topic == "Fruit"


def test_assignment_frozen():
    assignment = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    with pytest.raises(ValidationError):
        assignment.agent_id = "agent_2"


def test_assignment_serializable():
    assignment = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    dumped = assignment.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["agent_id"] == "agent_1"
    assert dumped["role"] == "villager"
