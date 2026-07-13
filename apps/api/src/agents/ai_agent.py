import time
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base import BaseAgent
from src.agents.llm_factory import get_llm_client
from src.agents.prompt_builder import build_system_prompt, build_user_prompt
from src.agents.retry import invoke_with_retry
from src.core.config import settings
from src.models import (
    ActionLog,
    AgentConfig,
    AgentRoleAssignment,
    DeliberationOutput,
    LLMProvider,
    Phase,
    PollingOutput,
    ReactionOutput,
    RoundContext,
    SpeakingOutput,
    VotingOutput,
)


class AIAgent(BaseAgent):
    """
    AI-driven agent using LangChain to communicate with LLM providers.
    Uses .with_structured_output() for Pydantic parsing and robust retry logic.
    """

    def __init__(
        self, config: AgentConfig, role_assignment: AgentRoleAssignment
    ) -> None:
        super().__init__(config, role_assignment)
        if not config.llm_config:
            raise ValueError("AIAgent requires an AgentLLMConfig")
        self._smart_llm = get_llm_client(
            config.llm_config, settings, model_name=config.llm_config.smart_model_name, api_key_index=config.api_key_index
        )
        self._fast_llm = get_llm_client(
            config.llm_config, settings, model_name=config.llm_config.fast_model_name, api_key_index=config.api_key_index
        )

    def _create_action_log(
        self,
        phase: Phase,
        context: RoundContext,
        structured_output: dict,
        latency_ms: int,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> ActionLog:
        return ActionLog(
            episode_id="unknown_episode_id",  # In Sprint 1, the engine handles injecting the real episode_id when exporting
            agent_id=self.config.agent_id,
            phase=phase,
            round_number=context.current_round,
            deliberation_round=context.deliberation_round,
            prompt_context={"stub": "false"},  # E4-T2 integrated
            raw_llm_response="",  # LangChain structured output doesn't give raw string easily without callbacks
            structured_output=structured_output,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            timestamp=datetime.now(UTC).isoformat(),
        )

    async def _invoke_llm(
        self, phase: Phase, context: RoundContext, output_schema: type, **kwargs
    ) -> any:
        """Helper to invoke LLM with structured output, retries, and record ActionLog."""

        # 1. Build System Prompt
        system_prompt_str = build_system_prompt(
            role_assignment=self.role_assignment,
            display_name=self.config.display_name,
            agent_names_list=context.all_agent_names,
            game_language=context.game_language,
        )

        # 2. Build User Prompt
        user_prompt_str = build_user_prompt(
            phase=phase,
            context=context,
            current_agent_name=self.config.display_name,
            **kwargs,
        )

        messages = [
            SystemMessage(content=system_prompt_str),
            HumanMessage(content=user_prompt_str),
        ]

        # 3. Setup chain with schema based on Phase (Model Tiering)
        if phase in (Phase.REACTION, Phase.POLLING):
            active_llm = self._fast_llm
            active_model_name = self.config.llm_config.fast_model_name
        else:
            active_llm = self._smart_llm
            active_model_name = self.config.llm_config.smart_model_name

        chain = active_llm.with_structured_output(output_schema, include_raw=True)

        start_time = time.perf_counter()

        # 4. Invoke with retry (with fallback from llama-4-scout to llama-3.3-70b for Groq)
        provider_str = self.config.llm_config.provider.value if self.config.llm_config else "unknown"
        try:
            result = await invoke_with_retry(
                chain=chain,
                messages=messages,
                agent_id=self.config.agent_id,
                phase=phase,
                provider=provider_str,
            )
        except Exception as e:
            # Check if this is a semantic validation error (we don't want to fallback on semantic errors)
            from src.agents.exceptions import AgentOutputError as AgentOutputErrorLocal
            from src.agents.retry import _is_semantic_error
            inner_exc = e.original_error if isinstance(e, AgentOutputErrorLocal) else e
            if _is_semantic_error(inner_exc):
                raise e

            is_groq = self.config.llm_config and self.config.llm_config.provider == LLMProvider.GROQ
            is_scout = self.config.llm_config and active_model_name == "meta-llama/llama-4-scout-17b-16e-instruct"
            if is_groq and is_scout:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Groq API call for {active_model_name} failed: {e}. "
                    f"Falling back to llama-3.3-70b-versatile..."
                )
                try:
                    from copy import deepcopy
                    fallback_config = deepcopy(self.config.llm_config)
                    fallback_llm = get_llm_client(
                        fallback_config,
                        settings,
                        model_name="llama-3.3-70b-versatile",
                        api_key_index=self.config.api_key_index,
                    )
                    fallback_chain = fallback_llm.with_structured_output(output_schema, include_raw=True)
                    
                    result = await invoke_with_retry(
                        chain=fallback_chain,
                        messages=messages,
                        agent_id=self.config.agent_id,
                        phase=phase,
                        provider=provider_str,
                    )
                except Exception as fallback_exc:
                    logger.error(f"Fallback to llama-3.3-70b-versatile failed: {fallback_exc}")
                    raise e
            else:
                raise e

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract parsed and raw response
        parsed_output = result["parsed"] if isinstance(result, dict) else result
        raw_message = result.get("raw") if isinstance(result, dict) else None

        # Fallback estimates (approx. 4 characters per token as fallback estimate)
        fallback_prompt_tokens = (len(system_prompt_str) + len(user_prompt_str)) // 4
        fallback_completion_tokens = len(str(parsed_output.model_dump())) // 4
        fallback_total_tokens = fallback_prompt_tokens + fallback_completion_tokens

        # Check for usage_metadata from LLM provider
        if raw_message and hasattr(raw_message, "usage_metadata") and raw_message.usage_metadata:
            usage = raw_message.usage_metadata
            prompt_tokens = usage.get("input_tokens", fallback_prompt_tokens)
            completion_tokens = usage.get("output_tokens", fallback_completion_tokens)
            total_tokens = usage.get("total_tokens", fallback_total_tokens)
        else:
            prompt_tokens = fallback_prompt_tokens
            completion_tokens = fallback_completion_tokens
            total_tokens = fallback_total_tokens

        # Record quota usage
        from src.core.quota import QuotaManager
        try:
            await QuotaManager.add_usage(self.config.api_key_index, total_tokens)
        except Exception as q_exc:
            # We don't want quota tracing errors to fail the whole agent run
            import logging
            logging.getLogger(__name__).warning(f"Failed to log quota usage: {q_exc}")

        # 5. Log action
        log = self._create_action_log(
            phase=phase,
            context=context,
            structured_output=parsed_output.model_dump(),
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self.action_logs.append(log)

        return parsed_output

    async def speak(self, context: RoundContext) -> SpeakingOutput:
        return await self._invoke_llm(Phase.SPEAKING, context, SpeakingOutput)

    async def deliberate(self, context: RoundContext) -> DeliberationOutput:
        return await self._invoke_llm(Phase.DELIBERATION, context, DeliberationOutput)

    async def poll(self, context: RoundContext) -> PollingOutput:
        return await self._invoke_llm(Phase.POLLING, context, PollingOutput)

    async def vote(self, context: RoundContext) -> VotingOutput:
        return await self._invoke_llm(Phase.VOTING, context, VotingOutput)

    async def react(self, context: RoundContext, **kwargs) -> ReactionOutput:
        return await self._invoke_llm(Phase.REACTION, context, ReactionOutput, **kwargs)
