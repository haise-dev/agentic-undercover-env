import pytest
from pydantic import ValidationError

from src.models.enums import PollVote
from src.models.votes import EliminationResult, PollRecord, VoteRecord


def test_poll_record_vote_now():
    rec = PollRecord(
        agent_id="agent_1",
        poll_vote=PollVote.VOTE_NOW,
        inner_thought="We should vote",
        round_number=1,
    )
    assert rec.poll_vote == PollVote.VOTE_NOW


def test_poll_record_frozen():
    rec = PollRecord(
        agent_id="agent_1",
        poll_vote=PollVote.VOTE_NOW,
        inner_thought="We should vote",
        round_number=1,
    )
    with pytest.raises(ValidationError):
        rec.poll_vote = PollVote.SKIP


def test_vote_record_valid():
    rec = VoteRecord(
        voter_agent_id="agent_1", target_agent_id="agent_0", inner_thought="Sus"
    )
    assert rec.voter_agent_id == "agent_1"
    assert rec.target_agent_id == "agent_0"


def test_elimination_result_no_tiebreak():
    res = EliminationResult(
        eliminated_agent_id="agent_0",
        vote_tally={"agent_0": 3, "agent_1": 1},
        was_tiebreak=False,
        tiebreak_candidates=None,
    )
    assert res.eliminated_agent_id == "agent_0"
    assert res.was_tiebreak is False
    assert res.tiebreak_candidates is None


def test_elimination_result_with_tiebreak():
    res = EliminationResult(
        eliminated_agent_id="agent_0",
        vote_tally={"agent_0": 2, "agent_1": 2},
        was_tiebreak=True,
        tiebreak_candidates=["agent_0", "agent_1"],
    )
    assert res.was_tiebreak is True
    assert res.tiebreak_candidates == ["agent_0", "agent_1"]


def test_elimination_result_vote_tally():
    res = EliminationResult(
        eliminated_agent_id="agent_0",
        vote_tally={"agent_0": 2, "agent_1": 2},
        was_tiebreak=True,
        tiebreak_candidates=["agent_0", "agent_1"],
    )
    assert res.vote_tally == {"agent_0": 2, "agent_1": 2}


def test_all_vote_models_serializable():
    p = PollRecord(
        agent_id="agent_1",
        poll_vote=PollVote.VOTE_NOW,
        inner_thought="thoughts",
        round_number=1,
    )
    v = VoteRecord(
        voter_agent_id="agent_1", target_agent_id="agent_0", inner_thought="thoughts"
    )
    e = EliminationResult(
        eliminated_agent_id="agent_0", vote_tally={"agent_0": 3}, was_tiebreak=False
    )

    for model in [p, v, e]:
        assert isinstance(model.model_dump(), dict)
