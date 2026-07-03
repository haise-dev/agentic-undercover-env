import pytest
from src.engine import EngineError, NodeError, AgentOutputError


def test_engine_error():
    err = EngineError("msg")
    assert str(err) == "msg"
    assert err.episode_id is None

    err_w_id = EngineError("msg", episode_id="abc")
    assert err_w_id.episode_id == "abc"


def test_node_error():
    err = NodeError("msg", node_name="test_node", episode_id="abc")
    assert isinstance(err, EngineError)
    assert err.node_name == "test_node"
    assert err.episode_id == "abc"


def test_agent_output_error():
    err = AgentOutputError("msg", agent_id="agent_1", phase="speaking", episode_id="abc")
    assert isinstance(err, NodeError)
    assert isinstance(err, EngineError)
    assert err.agent_id == "agent_1"
    assert err.phase == "speaking"
    assert err.node_name == "speaking_node"
    assert err.episode_id == "abc"
