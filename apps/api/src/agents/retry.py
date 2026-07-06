import logging
import httpx
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.exceptions import AgentOutputError
from src.models.enums import Phase

logger = logging.getLogger(__name__)

RETRY_WAIT_SECONDS = 1.0


class NetworkError(Exception):
    pass


def _is_semantic_error(e: Exception) -> bool:
    return isinstance(e, (ValidationError, OutputParserException))


def _is_network_error(e: BaseException) -> bool:
    return not _is_semantic_error(e)


async def invoke_with_retry(
    chain, messages: list[BaseMessage], agent_id: str, phase: Phase
) -> BaseModel:
    """
    Invokes a LangChain with structured output.
    - Semantic errors (ValidationError): 1 retry with feedback message.
    - Network errors: Up to 3 retries with exponential backoff.
    Raises AgentOutputError if all retries are exhausted.
    """

    @retry(
        retry=retry_if_exception(_is_network_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, min=1, max=10),
        reraise=True,
    )
    async def _invoke_network() -> BaseModel:
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            if not _is_semantic_error(e):
                logger.warning(f"Network error in agent {agent_id} phase {phase}: {e}")
            raise e

    # Manual loop for semantic retry
    max_semantic_attempts = 2
    for attempt in range(max_semantic_attempts):
        try:
            return await _invoke_network()
        except Exception as e:
            if _is_semantic_error(e):
                if attempt < max_semantic_attempts - 1:
                    logger.info(
                        f"Semantic error for agent {agent_id} in {phase}. Retrying. Error: {e}"
                    )
                    error_msg = (
                        f"Your previous output failed validation. Please fix the following errors:\n{e}"
                    )
                    messages.append(HumanMessage(content=error_msg))
                    continue
                else:
                    logger.error(
                        f"Agent {agent_id} failed semantic validation after {max_semantic_attempts} attempts."
                    )
                    raise AgentOutputError(agent_id, phase, e)
            else:
                # Network error that exhausted tenacity retries
                logger.error(f"Agent {agent_id} failed network call: {e}")
                raise AgentOutputError(agent_id, phase, e)

    # Should not reach here
    raise AgentOutputError(agent_id, phase, Exception("Unknown error in retry loop"))
