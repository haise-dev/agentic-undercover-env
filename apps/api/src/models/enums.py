from enum import StrEnum


class Role(StrEnum):
    VILLAGER = "villager"
    IMPOSTER = "imposter"


class AgentType(StrEnum):
    AI = "ai"
    HUMAN = "human"


class Phase(StrEnum):
    INIT = "init"
    SPEAKING = "speaking"
    DELIBERATION = "deliberation"
    POLLING = "polling"
    VOTING = "voting"
    REACTION = "reaction"
    ENDGAME = "endgame"


class PollVote(StrEnum):
    VOTE_NOW = "vote_now"
    SKIP = "skip"


class GameResult(StrEnum):
    VILLAGERS_WIN = "villagers_win"
    IMPOSTER_WINS = "imposter_wins"


class LLMProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
