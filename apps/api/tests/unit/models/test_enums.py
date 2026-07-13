from src.models.enums import GameResult, LLMProvider, Phase, PollVote, Role, DeliberationIntent


def test_role_values():
    assert Role.VILLAGER == "villager"
    assert Role.IMPOSTER == "imposter"


def test_phase_values():
    assert Phase.INIT == "init"
    assert Phase.SPEAKING == "speaking"
    assert Phase.DELIBERATION == "deliberation"
    assert Phase.POLLING == "polling"
    assert Phase.VOTING == "voting"
    assert Phase.REACTION == "reaction"
    assert Phase.ENDGAME == "endgame"


def test_poll_vote_values():
    assert PollVote.VOTE_NOW == "vote_now"
    assert PollVote.SKIP == "skip"


def test_game_result_values():
    assert GameResult.VILLAGERS_WIN == "villagers_win"
    assert GameResult.IMPOSTER_WINS == "imposter_wins"


def test_llm_provider_values():
    assert LLMProvider.OPENAI == "openai"
    assert LLMProvider.GEMINI == "gemini"
    assert LLMProvider.GROQ == "groq"
    assert LLMProvider.DEEPSEEK == "deepseek"


def test_deliberation_intent_values():
    assert DeliberationIntent.GENERAL_OPINION == "general_opinion"
    assert DeliberationIntent.ACCUSE == "accuse"
    assert DeliberationIntent.QUESTION == "question"
    assert DeliberationIntent.DEFEND == "defend"
    assert DeliberationIntent.AGREE_WITH == "agree_with"
    assert DeliberationIntent.SUGGEST_VOTE == "suggest_vote"
    assert DeliberationIntent.SUGGEST_SKIP == "suggest_skip"


def test_enums_are_str():
    assert isinstance(Role.VILLAGER, str)
    assert isinstance(Phase.INIT, str)
    assert isinstance(PollVote.VOTE_NOW, str)
    assert isinstance(GameResult.VILLAGERS_WIN, str)
    assert isinstance(LLMProvider.OPENAI, str)
    assert isinstance(DeliberationIntent.ACCUSE, str)


def test_enum_from_string():
    assert Role("villager") == Role.VILLAGER
    assert Phase("speaking") == Phase.SPEAKING
    assert DeliberationIntent("accuse") == DeliberationIntent.ACCUSE

