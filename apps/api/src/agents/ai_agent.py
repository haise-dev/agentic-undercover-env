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

    def __init__(self, config: AgentConfig, role_assignment: AgentRoleAssignment) -> None:
        super().__init__(config, role_assignment)
        if not config.llm_config:
            raise ValueError("AIAgent requires an AgentLLMConfig")
        self._llm = get_llm_client(config.llm_config, settings)

    def _create_action_log(
        self,
        phase: Phase,
        context: RoundContext,
        structured_output: dict,
        latency_ms: int,
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
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
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
            **kwargs
        )
        
        messages = [
            SystemMessage(content=system_prompt_str),
            HumanMessage(content=user_prompt_str)
        ]
        
        # 3. Setup chain with schema
        chain = self._llm.with_structured_output(output_schema)
        
        start_time = time.perf_counter()
        
        # 4. Invoke with retry
        result = await invoke_with_retry(chain, messages, self.config.agent_id, phase)
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # 5. Log action
        log = self._create_action_log(
            phase=phase,
            context=context,
            structured_output=result.model_dump(),
            latency_ms=latency_ms,
        )
        self.action_logs.append(log)
        
        return result

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
