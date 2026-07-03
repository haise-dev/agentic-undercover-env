from src.models.enums import Phase
from src.models.messages import PublicMessage


def test_gamestate_init(game_state):
    assert game_state.current_phase == Phase.INIT
    assert game_state.current_round == 1
    assert game_state.current_deliberation_round == 1


def test_gamestate_is_mutable(game_state):
    game_state.current_phase = Phase.SPEAKING
    assert game_state.current_phase == Phase.SPEAKING


def test_alive_agent_ids_all_alive(game_state):
    assert game_state.alive_agent_ids == ["agent_0", "agent_1", "agent_2", "agent_3"]


def test_alive_agent_ids_one_dead(game_state):
    game_state.agent_alive["agent_2"] = False
    assert game_state.alive_agent_ids == ["agent_0", "agent_1", "agent_3"]


def test_alive_agent_ids_order_stable(game_state):
    # Dict key insertion order: 0, 1, 2, 3
    # Mark 1 dead
    game_state.agent_alive["agent_1"] = False
    assert game_state.alive_agent_ids == ["agent_0", "agent_2", "agent_3"]
    # Mark 1 alive again
    game_state.agent_alive["agent_1"] = True
    assert game_state.alive_agent_ids == ["agent_0", "agent_1", "agent_2", "agent_3"]


def test_imposter_id_returns_correct(game_state):
    assert game_state.imposter_id == "agent_0"


def test_messages_in_current_round_empty(game_state):
    assert game_state.messages_in_current_round == []


def test_messages_in_current_round_filtered(game_state):
    msg1 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="Msg in round 1",
        timestamp="2026-07-02T10:00:00Z",
    )
    game_state.all_messages.append(msg1)
    game_state.current_round = 2
    assert game_state.messages_in_current_round == []


def test_messages_in_current_round_correct(game_state):
    msg1 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="Msg in round 1",
        timestamp="2026-07-02T10:00:00Z",
    )
    msg2 = PublicMessage(
        agent_id="agent_2",
        display_name="Charlie",
        phase=Phase.SPEAKING,
        round_number=2,
        content="Msg in round 2",
        timestamp="2026-07-02T10:01:00Z",
    )
    game_state.all_messages.extend([msg1, msg2])
    game_state.current_round = 2
    assert game_state.messages_in_current_round == [msg2]


def test_all_messages_never_reset(game_state):
    msg1 = PublicMessage(
        agent_id="agent_1",
        display_name="Bob",
        phase=Phase.SPEAKING,
        round_number=1,
        content="Msg in round 1",
        timestamp="2026-07-02T10:00:00Z",
    )
    game_state.all_messages.append(msg1)
    # Go to next round
    game_state.current_round = 2
    # Ensure all_messages still has msg1
    assert len(game_state.all_messages) == 1
    assert game_state.all_messages[0] == msg1


def test_poll_history_default_empty(game_state):
    assert game_state.poll_history == {}


def test_elimination_result_default_none(game_state):
    assert game_state.elimination_result is None


def test_gamestate_serializable(game_state):
    dumped = game_state.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["episode_id"] == game_state.episode_id
    assert dumped["current_phase"] == "init"


def test_started_at_is_string(game_state):
    assert isinstance(game_state.started_at, str)
