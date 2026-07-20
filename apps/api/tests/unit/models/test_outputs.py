import pytest
from pydantic import ValidationError

from src.models.enums import PollVote, DeliberationIntent
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
    out = DeliberationOutput(
        step_1_audit="thought",
        step_2_anti_repetition="thought",
        step_3_intent_and_target="thought",

        public_statement="statement",
        intent=DeliberationIntent.GENERAL_OPINION,
    )
    assert out.inner_thought == "Audit: thought\nAnti-Repetition: thought\nIntent: thought"
    assert out.public_statement == "statement"
    assert out.intent == DeliberationIntent.GENERAL_OPINION
    assert out.target_name is None


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
    d = DeliberationOutput(
        step_1_audit="t", step_2_anti_repetition="t", step_3_intent_and_target="t", public_statement="s", intent=DeliberationIntent.GENERAL_OPINION
    )
    p = PollingOutput(inner_thought="thought", poll_vote=PollVote.SKIP)
    v = VotingOutput(inner_thought="thought", vote_target="agent_1")
    r = ReactionOutput(inner_thought="thought", public_statement="statement")

    for model in [s, d, p, v, r]:
        assert isinstance(model.model_dump(), dict)


def test_inner_thought_required_on_all():
    with pytest.raises(ValidationError):
        SpeakingOutput(public_statement="statement")
    with pytest.raises(ValidationError):
        DeliberationOutput(
            public_statement="statement", intent=DeliberationIntent.GENERAL_OPINION
        )
    with pytest.raises(ValidationError):
        PollingOutput(poll_vote=PollVote.SKIP)
    with pytest.raises(ValidationError):
        VotingOutput(vote_target="agent_1")
    with pytest.raises(ValidationError):
        ReactionOutput(public_statement="statement")


def test_deliberation_output_valid_accuse_with_target():
    out = DeliberationOutput(
        step_1_audit="thought",
        step_2_anti_repetition="thought",
        step_3_intent_and_target="thought",

        public_statement="statement",
        intent=DeliberationIntent.ACCUSE,
        target_name="Beta",
    )
    assert out.intent == DeliberationIntent.ACCUSE
    assert out.target_name == "Beta"


def test_deliberation_output_accuse_missing_target():
    with pytest.raises(ValidationError) as exc_info:
        DeliberationOutput(
            step_1_audit="thought",
            step_2_anti_repetition="thought",
            step_3_intent_and_target="thought",

            public_statement="statement",
            intent=DeliberationIntent.ACCUSE,
        )
    assert "requires a non-empty target_name" in str(exc_info.value)


def test_deliberation_output_agree_with_missing_target():
    with pytest.raises(ValidationError) as exc_info:
        DeliberationOutput(
            step_1_audit="thought",
            step_2_anti_repetition="thought",
            step_3_intent_and_target="thought",

            public_statement="statement",
            intent=DeliberationIntent.AGREE_WITH,
        )
    assert "requires a non-empty target_name" in str(exc_info.value)


def test_deliberation_output_invalid_intent():
    with pytest.raises(ValidationError):
        DeliberationOutput(
            step_1_audit="thought",
            step_2_anti_repetition="thought",
            step_3_intent_and_target="thought",

            public_statement="statement",
            intent="invalid_intent",
        )

