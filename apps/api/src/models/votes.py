from pydantic import BaseModel, ConfigDict

from src.models.enums import PollVote


class PollRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    poll_vote: PollVote
    inner_thought: str
    round_number: int


class VoteRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    voter_agent_id: str
    target_agent_id: str
    inner_thought: str


class EliminationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    eliminated_agent_id: str
    vote_tally: dict[str, int]
    was_tiebreak: bool
    tiebreak_candidates: list[str] | None = None
