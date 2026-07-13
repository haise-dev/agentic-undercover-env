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
    assert formatted == "[Round 1 - Guess] [Alice]: I like milk.\n[Round 1 - Guess] [Bob]: I like chasing mice."


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
    assert "== INTENT SYSTEM ==" in prompt
    assert "general_opinion" in prompt
    assert "accuse" in prompt


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


def test_build_user_prompt_speaking_villager_uses_villager_template(round_context):
    prompt = build_user_prompt(Phase.SPEAKING, round_context, "Bob")
    # Villager speaking prompt should not contain the Imposter's deduction step
    assert "LISTEN & DEDUCE" not in prompt
    assert "CROSS-ROUND CONSISTENCY" in prompt


def test_build_user_prompt_speaking_imposter_uses_imposter_template(round_context):
    imposter_role = AgentRoleAssignment(
        agent_id="agent_1", role=Role.IMPOSTER, secret_word=None, topic="Animals"
    )
    object.__setattr__(round_context, "role_assignment", imposter_role)
    prompt = build_user_prompt(Phase.SPEAKING, round_context, "Bob")
    # Imposter speaking prompt must contain deduction instructions
    assert "LISTEN & DEDUCE" in prompt
    assert "CROSS-ROUND CONSISTENCY" in prompt


def test_build_user_prompt_deliberation_villager_uses_villager_template(round_context):
    object.__setattr__(round_context, "deliberation_round", 1)
    prompt = build_user_prompt(Phase.DELIBERATION, round_context, "Bob")
    # Villager deliberation prompt must contain Clue Audit instructions and reference the secret word
    assert "CLUE AUDIT" in prompt
    assert "Cat" in prompt


def test_build_user_prompt_deliberation_imposter_uses_imposter_template(round_context):
    imposter_role = AgentRoleAssignment(
        agent_id="agent_1", role=Role.IMPOSTER, secret_word=None, topic="Animals"
    )
    object.__setattr__(round_context, "role_assignment", imposter_role)
    object.__setattr__(round_context, "deliberation_round", 1)
    prompt = build_user_prompt(Phase.DELIBERATION, round_context, "Bob")
    # Imposter deliberation prompt should not contain Clue Audit or refer to secret word
    assert "CLUE AUDIT" not in prompt
    assert "secret word" not in prompt.lower()


def test_build_user_prompt_polling_same_for_both_roles(round_context):
    prompt_villager = build_user_prompt(Phase.POLLING, round_context, "Bob")
    
    imposter_role = AgentRoleAssignment(
        agent_id="agent_1", role=Role.IMPOSTER, secret_word=None, topic="Animals"
    )
    object.__setattr__(round_context, "role_assignment", imposter_role)
    prompt_imposter = build_user_prompt(Phase.POLLING, round_context, "Bob")
    
    assert prompt_villager == prompt_imposter


def test_build_user_prompt_voting_same_for_both_roles(round_context):
    prompt_villager = build_user_prompt(Phase.VOTING, round_context, "Bob")
    
    imposter_role = AgentRoleAssignment(
        agent_id="agent_1", role=Role.IMPOSTER, secret_word=None, topic="Animals"
    )
    object.__setattr__(round_context, "role_assignment", imposter_role)
    prompt_imposter = build_user_prompt(Phase.VOTING, round_context, "Bob")
    
    assert prompt_villager == prompt_imposter


def test_new_prompt_templates_vars():
    from src.agents.prompt_templates import (
        IMPOSTER_SPEAKING_PROMPT,
        VILLAGER_DELIBERATION_PROMPT,
        IMPOSTER_DELIBERATION_PROMPT,
    )
    
    # Verify templates have expected keywords/placeholders
    assert "past_history" in IMPOSTER_SPEAKING_PROMPT
    assert "chat_history" in IMPOSTER_SPEAKING_PROMPT
    assert "topic" in IMPOSTER_SPEAKING_PROMPT
    
    assert "past_history" in VILLAGER_DELIBERATION_PROMPT
    assert "chat_history" in VILLAGER_DELIBERATION_PROMPT
    assert "deliberation_history" in VILLAGER_DELIBERATION_PROMPT
    assert "secret_word" in VILLAGER_DELIBERATION_PROMPT
    assert "topic" in VILLAGER_DELIBERATION_PROMPT
    
    assert "past_history" in IMPOSTER_DELIBERATION_PROMPT
    assert "chat_history" in IMPOSTER_DELIBERATION_PROMPT
    assert "deliberation_history" in IMPOSTER_DELIBERATION_PROMPT
    assert "secret_word" not in IMPOSTER_DELIBERATION_PROMPT


def test_cr5_t1_prompt_optimization_no_vietnamese():
    from src.agents.prompt_templates import (
        VILLAGER_SYSTEM_PROMPT,
        IMPOSTER_SYSTEM_PROMPT,
        SPEAKING_PHASE_PROMPT,
        IMPOSTER_SPEAKING_PROMPT,
        VILLAGER_DELIBERATION_PROMPT,
        IMPOSTER_DELIBERATION_PROMPT,
    )
    
    all_prompts = [
        VILLAGER_SYSTEM_PROMPT,
        IMPOSTER_SYSTEM_PROMPT,
        SPEAKING_PHASE_PROMPT,
        IMPOSTER_SPEAKING_PROMPT,
        VILLAGER_DELIBERATION_PROMPT,
        IMPOSTER_DELIBERATION_PROMPT,
    ]
    
    # Assert that no Vietnamese characters are in the prompt templates.
    # Vietnamese characters: á, à, ả, ã, ạ, â, ấ, ầ, ẩn, ẫ, ậ, ă, ắ, ằ, ẳ, ẵ, ặ, é, è, ẻ, ẽ, ẹ, ê, ế, ề, ể, ễ, ệ, í, ì, ỉ, ĩ, ị, ó, ò, ỏ, õ, ọ, ô, ố, ồ, ổ, ỗ, ộ, ơ, ớ, ờ, ở, ỡ, ợ, ú, ù, ủ, ũ, ụ, ư, ứ, ừ, ử, ữ, ự, ý, ỳ, ỷ, ỹ, ỵ, đ
    vietnamese_chars = "áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
    for prompt in all_prompts:
        found_chars = [c for c in prompt.lower() if c in vietnamese_chars]
        assert not found_chars, f"Found Vietnamese characters {found_chars} in prompt"


def test_cr5_t1_identity_rules():
    from src.agents.prompt_templates import VILLAGER_SYSTEM_PROMPT, IMPOSTER_SYSTEM_PROMPT
    
    assert "CRITICAL IDENTITY RULE" in VILLAGER_SYSTEM_PROMPT
    assert "CRITICAL IDENTITY RULE" in IMPOSTER_SYSTEM_PROMPT
    assert "third person" in VILLAGER_SYSTEM_PROMPT.lower()
    assert "third person" in IMPOSTER_SYSTEM_PROMPT.lower()


def test_cr5_t2_reaction_prompt_has_variables():
    from src.agents.prompt_templates import REACTION_SURVIVOR_PROMPT
    
    assert "{agent_vote_target}" in REACTION_SURVIVOR_PROMPT
    assert "{game_outcome}" in REACTION_SURVIVOR_PROMPT
    assert "{vote_correct_status}" in REACTION_SURVIVOR_PROMPT
    assert "{you_won_status}" in REACTION_SURVIVOR_PROMPT


def test_cr5_t2_prompt_builder_passes_reaction_context(round_context):
    prompt = build_user_prompt(
        Phase.REACTION, 
        round_context, 
        "Alice",
        is_eliminated_agent=False,
        eliminated_agent_name="Bob",
        eliminated_role=Role.IMPOSTER,
        outcome_statement="The Villagers have won.",
        last_words="I'll be back.",
        agent_vote_target="Dave",
        game_outcome="villagers_win",
        vote_correct_status="YES — you voted for the right person.",
        you_won_status="YOU WON this game."
    )
    
    assert "You voted for: Dave" in prompt
    assert "Overall outcome: villagers_win" in prompt
    assert "Did you vote correctly? YES — you voted for the right person." in prompt
    assert "Did you win? YOU WON this game." in prompt


