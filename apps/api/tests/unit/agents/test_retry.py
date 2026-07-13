from unittest.mock import AsyncMock

import httpx
import pytest
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError

from src.agents.exceptions import AgentOutputError
from src.agents.retry import invoke_with_retry
from src.models.enums import Phase


class DummyOutput(BaseModel):
    inner_thought: str
    public_statement: str


@pytest.fixture
def mock_chain():
    return AsyncMock()


@pytest.mark.asyncio
async def test_invoke_with_retry_success(mock_chain):
    expected_output = DummyOutput(inner_thought="think", public_statement="hello")
    mock_chain.ainvoke.return_value = expected_output

    messages = [SystemMessage(content="You are an agent.")]
    result = await invoke_with_retry(mock_chain, messages, "agent_1", Phase.SPEAKING)

    assert result == expected_output
    assert mock_chain.ainvoke.call_count == 1
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_invoke_with_retry_semantic_failure_then_success(mock_chain):
    expected_output = DummyOutput(inner_thought="think", public_statement="hello")
    
    # Create a dummy validation error
    error = ValidationError.from_exception_data("DummyOutput", [{"type": "missing", "loc": ("public_statement",), "input": {}}])
    
    mock_chain.ainvoke.side_effect = [error, expected_output]

    messages = [SystemMessage(content="You are an agent.")]
    result = await invoke_with_retry(mock_chain, messages, "agent_1", Phase.SPEAKING)

    assert result == expected_output
    assert mock_chain.ainvoke.call_count == 2
    assert len(messages) == 2  # Original message + Error feedback message
    assert isinstance(messages[-1], HumanMessage)
    assert "Your previous output failed validation" in messages[-1].content


@pytest.mark.asyncio
async def test_invoke_with_retry_semantic_failure_twice_raises(mock_chain):
    error = ValidationError.from_exception_data("DummyOutput", [{"type": "missing", "loc": ("public_statement",), "input": {}}])
    
    mock_chain.ainvoke.side_effect = [error, error]

    messages = [SystemMessage(content="You are an agent.")]
    
    with pytest.raises(AgentOutputError) as exc_info:
        await invoke_with_retry(mock_chain, messages, "agent_1", Phase.SPEAKING)
        
    assert exc_info.value.agent_id == "agent_1"
    assert exc_info.value.phase == Phase.SPEAKING
    assert mock_chain.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_invoke_with_retry_network_failure_then_success(mock_chain):
    expected_output = DummyOutput(inner_thought="think", public_statement="hello")
    
    # Simulate a network error
    error = httpx.RequestError("Connection timeout")
    
    # Needs 2 failures then success
    mock_chain.ainvoke.side_effect = [error, error, expected_output]

    messages = [SystemMessage(content="You are an agent.")]
    
    # We should override retry wait for tests to avoid slow tests
    import src.agents.retry
    src.agents.retry.RETRY_WAIT_SECONDS = 0.01  # speed up

    result = await invoke_with_retry(mock_chain, messages, "agent_1", Phase.SPEAKING)

    assert result == expected_output
    assert mock_chain.ainvoke.call_count == 3


@pytest.mark.asyncio
async def test_invoke_with_retry_network_failure_max_retries(mock_chain):
    error = httpx.RequestError("Connection timeout")
    
    mock_chain.ainvoke.side_effect = [error, error, error, error]  # will stop at 3 internally via tenacity

    messages = [SystemMessage(content="You are an agent.")]
    
    import src.agents.retry
    src.agents.retry.RETRY_WAIT_SECONDS = 0.01

    with pytest.raises(AgentOutputError):
        await invoke_with_retry(mock_chain, messages, "agent_1", Phase.SPEAKING)
        
    # Tenacity stops at 3 attempts
    assert mock_chain.ainvoke.call_count == 3


@pytest.mark.asyncio
async def test_invoke_with_retry_rate_limit_error(mock_chain):
    from src.engine.exceptions import RateLimitError
    # We simulate an exception that looks like a rate limit error
    class FakeRateLimitException(Exception):
        pass
    error = FakeRateLimitException("Rate limit exceeded 429")
    
    mock_chain.ainvoke.side_effect = [error, error, error]
    
    messages = [SystemMessage(content="You are an agent.")]
    
    import src.agents.retry
    src.agents.retry.RETRY_WAIT_SECONDS = 0.01

    with pytest.raises(RateLimitError) as exc_info:
        await invoke_with_retry(mock_chain, messages, "agent_1", Phase.SPEAKING, provider="gemini")
        
    assert exc_info.value.provider == "gemini"
    assert "Rate limit hit for provider gemini" in str(exc_info.value)

