import logging

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


def _is_rate_limit_error(e: BaseException) -> bool:
    err_type = type(e).__name__
    err_module = type(e).__module__

    if err_type in ("RateLimitError", "ResourceExhausted"):
        return True

    if "google.api_core.exceptions" in err_module and err_type == "ResourceExhausted":
        return True
    if "openai" in err_module and err_type == "RateLimitError":
        return True
    if "groq" in err_module and err_type == "RateLimitError":
        return True

    err_str = str(e).lower()
    if "rate limit" in err_str or "resourceexhausted" in err_str or "429" in err_str:
        return True

    return False


async def invoke_with_retry(
    chain,
    messages: list[BaseMessage],
    agent_id: str,
    phase: Phase,
    provider: str = "unknown",
) -> dict | BaseModel:
    """
    Invokes a LangChain with structured output.
    - Semantic errors (ValidationError): 1 retry with feedback message.
    - Network errors: Up to 3 retries with exponential backoff.
    Raises RateLimitError if it's a rate limit error.
    Raises AgentOutputError if all retries are exhausted.
    """

    @retry(
        retry=retry_if_exception(_is_network_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, min=1, max=10),
        reraise=True,
    )
    async def _invoke_network() -> dict | BaseModel:
        try:
            res = await chain.ainvoke(messages)
            if isinstance(res, dict) and res.get("parsing_error") is not None:
                raise res["parsing_error"]
            return res
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
                    error_msg = f"Your previous output failed validation. Please fix the following errors:\n{e}"
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
                if _is_rate_limit_error(e):
                    from src.engine.exceptions import RateLimitError

                    raise RateLimitError(
                        message=f"Rate limit hit for provider {provider}: {e}",
                        provider=provider,
                    )
                raise AgentOutputError(agent_id, phase, e)

    # Should not reach here
    raise AgentOutputError(agent_id, phase, Exception("Unknown error in retry loop"))
