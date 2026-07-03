from pydantic import BaseModel, ConfigDict

from src.models.enums import PollVote


class SpeakingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    public_statement: str


class DeliberationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    public_statement: str


class PollingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    poll_vote: PollVote


class VotingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    vote_target: str


class ReactionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    public_statement: str


PhaseOutput = (
    SpeakingOutput | DeliberationOutput | PollingOutput | VotingOutput | ReactionOutput
)
