from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.models.enums import AgentType, LLMProvider


class AgentLLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: LLMProvider
    smart_model_name: str
    fast_model_name: str
    temperature: float = 0.8
    max_tokens: int | None = None

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_model_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "model_name" in data:
                if "smart_model_name" not in data:
                    data["smart_model_name"] = data["model_name"]
                if "fast_model_name" not in data:
                    data["fast_model_name"] = data["model_name"]
        return data


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    display_name: str
    display_color: str
    agent_type: AgentType
    llm_config: AgentLLMConfig | None = None
    api_key_index: int = Field(default=1, ge=1, le=4)


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
