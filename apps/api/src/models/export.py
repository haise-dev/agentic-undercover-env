from pydantic import BaseModel, ConfigDict

from src.models.assignment import AgentRoleAssignment
from src.models.config import EpisodeConfig
from src.models.enums import GameResult, Phase
from src.models.messages import PublicMessage, SystemAnnouncement
from src.models.votes import EliminationResult, PollRecord, VoteRecord


class ActionLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    agent_id: str
    phase: Phase
    round_number: int
    deliberation_round: int | None = None
    prompt_context: dict
    raw_llm_response: str
    structured_output: dict
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    timestamp: str
    latency_ms: int | None = None


class EpisodeExport(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Identity
    episode_id: str
    started_at: str
    ended_at: str
    duration_seconds: float

    # Config
    config: EpisodeConfig
    role_assignments: list[AgentRoleAssignment]

    # Result
    result: GameResult
    winning_agent_ids: list[str]
    elimination_result: EliminationResult

    # History
    all_messages: list[PublicMessage]
    all_announcements: list[SystemAnnouncement]
    poll_history: dict[str, list[PollRecord]]  # str keys for JSON compat
    vote_records: list[VoteRecord]

    # Logs
    action_logs: list[ActionLog]

    # Stats
    total_rounds_played: int
    total_llm_calls: int
    total_tokens_used: int | None
    tokens_per_agent: dict[str, int | None]
