from pydantic import BaseModel, ConfigDict, model_validator

from src.models.enums import DeliberationIntent, PollVote


class SpeakingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    public_statement: str


class DeliberationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    inner_thought: str
    public_statement: str
    intent: DeliberationIntent
    target_name: str | None = None

    @model_validator(mode="after")
    def _target_required_for_directional_intents(self) -> "DeliberationOutput":
        requires_target = {
            DeliberationIntent.ACCUSE,
            DeliberationIntent.QUESTION,
            DeliberationIntent.AGREE_WITH,
        }
        if self.intent in requires_target and not self.target_name:
            raise ValueError(f"intent='{self.intent}' requires a non-empty target_name")
        return self


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
