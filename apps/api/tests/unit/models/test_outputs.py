import pytest
from pydantic import ValidationError

from src.models.enums import PollVote
from src.models.outputs import (
    DeliberationOutput,
    PollingOutput,
    ReactionOutput,
    SpeakingOutput,
    VotingOutput,
)


def test_speaking_output_valid():
    out = SpeakingOutput(inner_thought="thought", public_statement="statement")
    assert out.inner_thought == "thought"
    assert out.public_statement == "statement"


def test_speaking_output_missing_field():
    with pytest.raises(ValidationError):
        SpeakingOutput(inner_thought="thought")


def test_speaking_output_frozen():
    out = SpeakingOutput(inner_thought="thought", public_statement="statement")
    with pytest.raises(ValidationError):
        out.inner_thought = "new thought"


def test_deliberation_output_valid():
    out = DeliberationOutput(inner_thought="thought", public_statement="statement")
    assert out.inner_thought == "thought"
    assert out.public_statement == "statement"


def test_polling_output_vote_now():
    out = PollingOutput(inner_thought="thought", poll_vote=PollVote.VOTE_NOW)
    assert out.poll_vote == PollVote.VOTE_NOW


def test_polling_output_skip():
    out = PollingOutput(inner_thought="thought", poll_vote=PollVote.SKIP)
    assert out.poll_vote == PollVote.SKIP


def test_polling_output_invalid_vote():
    with pytest.raises(ValidationError):
        PollingOutput(inner_thought="thought", poll_vote="invalid_vote")


def test_voting_output_valid():
    out = VotingOutput(inner_thought="thought", vote_target="agent_1")
    assert out.vote_target == "agent_1"


def test_reaction_output_valid():
    out = ReactionOutput(inner_thought="thought", public_statement="statement")
    assert out.inner_thought == "thought"
    assert out.public_statement == "statement"


def test_all_outputs_serializable():
    s = SpeakingOutput(inner_thought="thought", public_statement="statement")
    d = DeliberationOutput(inner_thought="thought", public_statement="statement")
    p = PollingOutput(inner_thought="thought", poll_vote=PollVote.SKIP)
    v = VotingOutput(inner_thought="thought", vote_target="agent_1")
    r = ReactionOutput(inner_thought="thought", public_statement="statement")

    for model in [s, d, p, v, r]:
        assert isinstance(model.model_dump(), dict)


def test_inner_thought_required_on_all():
    with pytest.raises(ValidationError):
        SpeakingOutput(public_statement="statement")
    with pytest.raises(ValidationError):
        DeliberationOutput(public_statement="statement")
    with pytest.raises(ValidationError):
        PollingOutput(poll_vote=PollVote.SKIP)
    with pytest.raises(ValidationError):
        VotingOutput(vote_target="agent_1")
    with pytest.raises(ValidationError):
        ReactionOutput(public_statement="statement")
