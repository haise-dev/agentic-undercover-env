from pydantic import BaseModel, ConfigDict, field_validator

from src.models.enums import AgentType, LLMProvider


class AgentLLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: LLMProvider
    model_name: str
    temperature: float = 0.8
    max_tokens: int | None = None


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    display_name: str
    display_color: str
    agent_type: AgentType
    llm_config: AgentLLMConfig | None = None


class EpisodeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    topic: str
    secret_word: str
    agents: list[AgentConfig]
    max_rounds: int = 3

    @field_validator("agents")
    @classmethod
    def must_have_four_agents(cls, v: list[AgentConfig]) -> list[AgentConfig]:
        if len(v) != 4:
            raise ValueError("Episode must have exactly 4 agents.")
        return v
