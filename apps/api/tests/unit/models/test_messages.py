import pytest
from pydantic import ValidationError

from src.models.assignment import AgentRoleAssignment
from src.models.enums import Phase, Role
from src.models.messages import PublicMessage, RoundContext, SystemAnnouncement


def test_public_message_valid():
    msg = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        deliberation_round=None,
        content="Hello",
        timestamp="2026-07-02T10:00:00Z",
    )
    assert msg.agent_id == "agent_1"
    assert msg.content == "Hello"


def test_public_message_deliberation_round_optional():
    msg = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.DELIBERATION,
        round_number=1,
        deliberation_round=2,
        content="Hello",
        timestamp="2026-07-02T10:00:00Z",
    )
    assert msg.deliberation_round == 2


def test_public_message_frozen():
    msg = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        deliberation_round=None,
        content="Hello",
        timestamp="2026-07-02T10:00:00Z",
    )
    with pytest.raises(ValidationError):
        msg.content = "New content"


def test_system_announcement_valid():
    ann = SystemAnnouncement(
        phase=Phase.SPEAKING,
        round_number=1,
        content="System broadcast",
        timestamp="2026-07-02T10:00:00Z",
    )
    assert ann.phase == Phase.SPEAKING
    assert ann.content == "System broadcast"


def test_round_context_empty_history():
    ra = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    ctx = RoundContext(
        role_assignment=ra,
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=None,
        public_history=[],
        announcements=[],
        alive_agents=[],
        all_agent_names="Alice, Bob, Charlie, Diana",
        game_language="English",
    )
    assert ctx.public_history == []


def test_round_context_is_final_round_default():
    ra = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    ctx = RoundContext(
        role_assignment=ra,
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=None,
        public_history=[],
        announcements=[],
        alive_agents=[],
        all_agent_names="Alice, Bob, Charlie, Diana",
        game_language="English",
    )
    assert ctx.is_final_round is False


def test_round_context_frozen():
    ra = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    ctx = RoundContext(
        role_assignment=ra,
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=None,
        public_history=[],
        announcements=[],
        alive_agents=[],
        all_agent_names="Alice, Bob, Charlie, Diana",
        game_language="English",
    )
    with pytest.raises(ValidationError):
        ctx.current_round = 2


def test_round_context_serializable():
    ra = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    ctx = RoundContext(
        role_assignment=ra,
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=None,
        public_history=[],
        announcements=[],
        alive_agents=[],
        all_agent_names="Alice, Bob, Charlie, Diana",
        game_language="English",
    )
    dumped = ctx.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["role_assignment"]["role"] == "villager"


def test_alive_agents_structure():
    ra = AgentRoleAssignment(
        agent_id="agent_1", role=Role.VILLAGER, secret_word="Durian", topic="Fruit"
    )
    ctx = RoundContext(
        role_assignment=ra,
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=None,
        public_history=[],
        announcements=[],
        alive_agents=[{"agent_id": "agent_0", "display_name": "Alice"}],
        all_agent_names="Alice, Bob, Charlie, Diana",
        game_language="English",
    )
    assert ctx.alive_agents == [{"agent_id": "agent_0", "display_name": "Alice"}]
