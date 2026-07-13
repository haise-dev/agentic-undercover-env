import pytest
from src.models import (
    GameState,
    Phase,
    Role,
    PublicMessage,
    AgentRoleAssignment,
)
from src.engine.context_builder import ContextBuilder


def test_context_builder_speaking_happy_path(game_state):
    game_state.current_phase = Phase.SPEAKING
    game_state.current_round = 1

    # Add a public message
    msg = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="Hello!",
        timestamp="2026-07-03T10:00:00Z",
    )
    game_state.all_messages.append(msg)

    # Build context for agent_1 (Villager)
    ctx = ContextBuilder.build(game_state, "agent_1")

    assert ctx.role_assignment.role == Role.VILLAGER
    assert ctx.role_assignment.secret_word == "Durian"
    assert ctx.current_phase == Phase.SPEAKING
    assert ctx.current_round == 1
    assert ctx.deliberation_round is None
    assert len(ctx.public_history) == 1
    assert ctx.public_history[0].content == "Hello!"
    assert ctx.is_final_round is False


def test_context_builder_speaking_history_filtering(game_state):
    game_state.current_phase = Phase.SPEAKING
    game_state.current_round = 2

    # Round 1 Speaking Message
    msg1 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="R1 Speaking",
        timestamp="2026-07-03T10:00:00Z",
    )
    # Round 2 Speaking Message
    msg2 = PublicMessage(
        agent_id="agent_2",
        display_name="Charlie",
        phase=Phase.SPEAKING,
        round_number=2,
        content="R2 Speaking",
        timestamp="2026-07-03T10:05:00Z",
    )
    # Round 2 Deliberation Message (should not be in Speaking context)
    msg3 = PublicMessage(
        agent_id="agent_3",
        display_name="Diana",
        phase=Phase.DELIBERATION,
        round_number=2,
        content="R2 Delib",
        timestamp="2026-07-03T10:10:00Z",
    )

    game_state.all_messages.extend([msg1, msg2, msg3])

    ctx = ContextBuilder.build(game_state, "agent_1")
    assert len(ctx.public_history) == 2
    assert ctx.public_history[0].content == "R1 Speaking"
    assert ctx.public_history[1].content == "R2 Speaking"


def test_context_builder_deliberation_history(game_state):
    game_state.current_phase = Phase.DELIBERATION
    game_state.current_round = 1
    game_state.current_deliberation_round = 2

    msg1 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="R1 Speaking",
        timestamp="2026-07-03T10:00:00Z",
    )
    msg2 = PublicMessage(
        agent_id="agent_2",
        display_name="Charlie",
        phase=Phase.DELIBERATION,
        round_number=1,
        content="R1 Delib",
        timestamp="2026-07-03T10:05:00Z",
    )
    msg3 = PublicMessage(
        agent_id="agent_3",
        display_name="Diana",
        phase=Phase.SPEAKING,
        round_number=2,
        content="R2 Speaking",
        timestamp="2026-07-03T10:10:00Z",
    )

    game_state.all_messages.extend([msg1, msg2, msg3])

    ctx = ContextBuilder.build(game_state, "agent_1")
    assert ctx.deliberation_round == 2
    assert len(ctx.public_history) == 2
    assert ctx.public_history[0].content == "R1 Speaking"
    assert ctx.public_history[1].content == "R1 Delib"


def test_context_builder_reaction_history(game_state):
    game_state.current_phase = Phase.REACTION
    game_state.current_round = 2

    msg1 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="Msg 1",
        timestamp="2026-07-03T10:00:00Z",
    )
    msg2 = PublicMessage(
        agent_id="agent_2",
        display_name="Charlie",
        phase=Phase.SPEAKING,
        round_number=2,
        content="Msg 2",
        timestamp="2026-07-03T10:05:00Z",
    )

    game_state.all_messages.extend([msg1, msg2])

    ctx = ContextBuilder.build(game_state, "agent_1")
    assert len(ctx.public_history) == 2
    assert ctx.public_history[0].content == "Msg 1"
    assert ctx.public_history[1].content == "Msg 2"


def test_context_builder_alive_agents(game_state):
    game_state.current_phase = Phase.SPEAKING
    game_state.agent_alive["agent_2"] = False  # Charlie is dead

    ctx = ContextBuilder.build(game_state, "agent_1")
    alive_agents = ctx.alive_agents

    # Should only contain agent_0, agent_1, agent_3 in correct order
    assert len(alive_agents) == 3
    assert alive_agents[0] == {"agent_id": "agent_0", "display_name": "Alice"}
    assert alive_agents[1] == {"agent_id": "agent_1", "display_name": "Bob"}
    assert alive_agents[2] == {"agent_id": "agent_3", "display_name": "Diana"}


def test_context_builder_imposter_no_leak(game_state):
    game_state.current_phase = Phase.SPEAKING
    ctx = ContextBuilder.build(game_state, "agent_0")  # Imposter

    assert ctx.role_assignment.role == Role.IMPOSTER
    assert ctx.role_assignment.secret_word is None


def test_context_builder_is_final_round_toggle(game_state):
    game_state.current_phase = Phase.SPEAKING
    ctx_final = ContextBuilder.build(game_state, "agent_1", is_final_round=True)
    assert ctx_final.is_final_round is True

    ctx_not_final = ContextBuilder.build(game_state, "agent_1", is_final_round=False)
    assert ctx_not_final.is_final_round is False


def test_context_builder_invalid_phases(game_state):
    # Phase.INIT
    game_state.current_phase = Phase.INIT
    with pytest.raises(ValueError) as exc_info:
        ContextBuilder.build(game_state, "agent_1")
    assert "Cannot build context for non-interactive phase" in str(exc_info.value)

    # Phase.ENDGAME
    game_state.current_phase = Phase.ENDGAME
    with pytest.raises(ValueError) as exc_info:
        ContextBuilder.build(game_state, "agent_1")
    assert "Cannot build context for non-interactive phase" in str(exc_info.value)


def test_context_builder_unknown_agent(game_state):
    game_state.current_phase = Phase.SPEAKING
    with pytest.raises(KeyError):
        ContextBuilder.build(game_state, "unknown_agent")


def test_context_builder_imposter_leak_assert(game_state):
    game_state.current_phase = Phase.SPEAKING
    # Intentionally corrupt the role assignment to leak the secret word
    game_state.role_assignments["agent_0"] = AgentRoleAssignment(
        agent_id="agent_0",
        role=Role.IMPOSTER,
        secret_word="Durian",  # Invalid for Imposter
        topic="Fruit",
    )

    with pytest.raises(AssertionError) as exc_info:
        ContextBuilder.build(game_state, "agent_0")
    assert "Leak detected!" in str(exc_info.value)


def test_context_builder_empty_round_history(game_state):
    game_state.current_phase = Phase.SPEAKING
    game_state.current_round = 2

    # Message from round 1
    msg = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="R1",
        timestamp="2026-07-03T10:00:00Z",
    )
    game_state.all_messages.append(msg)

    # Round 2 is empty
    ctx = ContextBuilder.build(game_state, "agent_1")
    assert len(ctx.public_history) == 1
    assert ctx.public_history[0].content == "R1"


def test_context_builder_partial_round_history(game_state):
    game_state.current_phase = Phase.SPEAKING
    game_state.current_round = 1

    msg1 = PublicMessage(
        agent_id="agent_0",
        display_name="Alice",
        phase=Phase.SPEAKING,
        round_number=1,
        content="M1",
        timestamp="2026-07-03T10:00:00Z",
    )
    msg2 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="M2",
        timestamp="2026-07-03T10:05:00Z",
    )
    game_state.all_messages.extend([msg1, msg2])

    ctx = ContextBuilder.build(game_state, "agent_2")  # Agent 2 has not spoken yet
    assert len(ctx.public_history) == 2
    assert ctx.public_history[0].content == "M1"
    assert ctx.public_history[1].content == "M2"
