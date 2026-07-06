import pytest

from src.agents.prompt_builder import (
    build_system_prompt,
    build_user_prompt,
    format_alive_agents,
    format_chat_history,
)
from src.models import (
    AgentRoleAssignment,
    Phase,
    PublicMessage,
    Role,
    RoundContext,
)


@pytest.fixture
def round_context():
    return RoundContext(
        role_assignment=AgentRoleAssignment(
            agent_id="agent_1", role=Role.VILLAGER, secret_word="Cat", topic="Animals"
        ),
        current_phase=Phase.SPEAKING,
        current_round=1,
        deliberation_round=0,
        public_history=[],
        announcements=[],
        alive_agents=[
            {"agent_id": "agent_0", "display_name": "Alice"},
            {"agent_id": "agent_1", "display_name": "Bob"},
            {"agent_id": "agent_3", "display_name": "Dave"},
        ],
        all_agent_names="Alice, Bob, Charlie, Dave",
        game_language="English",
        is_final_round=False,
    )


def test_format_alive_agents():
    alive_agents = [
        {"agent_id": "agent_0", "display_name": "Alice"},
        {"agent_id": "agent_3", "display_name": "Dave"},
    ]
    formatted = format_alive_agents(alive_agents)
    assert formatted == "Alice, Dave"


def test_format_chat_history():
    messages = [
        PublicMessage(
            agent_id="agent_0",
            display_name="Alice",
            phase=Phase.SPEAKING,
            round_number=1,
            content="I like milk.",
            timestamp="2026-07-06T00:00:00Z"
        ),
        PublicMessage(
            agent_id="agent_1",
            display_name="Bob",
            phase=Phase.SPEAKING,
            round_number=1,
            content="I like chasing mice.",
            timestamp="2026-07-06T00:00:01Z"
        ),
    ]
    formatted = format_chat_history(messages)
    assert formatted == "[Alice]: I like milk.\n[Bob]: I like chasing mice."


def test_format_chat_history_empty():
    assert format_chat_history([]) == ""


def test_build_system_prompt_villager():
    role_assignment = AgentRoleAssignment(
        agent_id="agent_0", role=Role.VILLAGER, secret_word="Cat", topic="Animals"
    )
    prompt = build_system_prompt(
        role_assignment, "Alice", "Alice, Bob, Dave", "English"
    )
    
    assert "Cat" in prompt
    assert "Alice" in prompt
    assert "Alice, Bob, Dave" in prompt
    assert "Animals" in prompt
    assert "English" in prompt
    assert "VILLAGER" in prompt


def test_build_system_prompt_imposter():
    role_assignment = AgentRoleAssignment(
        agent_id="agent_1", role=Role.IMPOSTER, secret_word=None, topic="Animals"
    )
    prompt = build_system_prompt(
        role_assignment, "Bob", "Alice, Bob, Dave", "English"
    )
    
    assert "Cat" not in prompt
    assert "Bob" in prompt
    assert "Alice, Bob, Dave" in prompt
    assert "Animals" in prompt
    assert "English" in prompt
    assert "IMPOSTER" in prompt


def test_build_user_prompt_speaking(round_context):
    msg = PublicMessage(
        agent_id="agent_0", display_name="Alice", phase=Phase.SPEAKING,
        round_number=1, content="Meow.", timestamp="time"
    )
    # Use object.__setattr__ since RoundContext is frozen
    object.__setattr__(round_context, "public_history", [msg])
    
    prompt = build_user_prompt(Phase.SPEAKING, round_context, "Bob")
    
    assert "Speaking Round: 1 of 3" in prompt
    assert "Currently alive players: Alice, Bob, Dave" in prompt
    assert "[Alice]: Meow." in prompt


def test_build_user_prompt_speaking_final_round(round_context):
    object.__setattr__(round_context, "current_round", 3)
    object.__setattr__(round_context, "is_final_round", True)
    
    prompt = build_user_prompt(Phase.SPEAKING, round_context, "Bob")
    
    assert "This is the FINAL ROUND. A vote will be forced after deliberation." in prompt


def test_build_user_prompt_deliberation(round_context):
    object.__setattr__(round_context, "deliberation_round", 1)
    prompt = build_user_prompt(Phase.DELIBERATION, round_context, "Bob")
    
    assert "Deliberation Round: 1 of 2" in prompt


def test_build_user_prompt_polling(round_context):
    prompt = build_user_prompt(Phase.POLLING, round_context, "Bob")
    assert "proceed to an immediate binding vote" in prompt


def test_build_user_prompt_voting(round_context):
    prompt = build_user_prompt(Phase.VOTING, round_context, "Bob")
    assert "FINAL VOTE" in prompt


def test_build_user_prompt_reaction_eliminated(round_context):
    prompt = build_user_prompt(
        Phase.REACTION, 
        round_context, 
        "Bob",
        is_eliminated_agent=True
    )
    assert "YOU HAVE BEEN ELIMINATED" in prompt
    assert "Bob" in prompt


def test_build_user_prompt_reaction_survivor(round_context):
    prompt = build_user_prompt(
        Phase.REACTION, 
        round_context, 
        "Alice",
        is_eliminated_agent=False,
        eliminated_agent_name="Bob",
        eliminated_role=Role.IMPOSTER,
        outcome_statement="The Villagers have won.",
        last_words="I'll be back."
    )
    
    assert "RESULT REVEALED" in prompt
    assert "Bob has been eliminated" in prompt
    assert "Their role was: imposter" in prompt
    assert "The Villagers have won." in prompt
    assert "I'll be back." in prompt


def test_build_user_prompt_invalid_phase(round_context):
    with pytest.raises(ValueError, match="Unsupported phase for user prompt"):
        build_user_prompt("UNKNOWN_PHASE", round_context, "Bob")
