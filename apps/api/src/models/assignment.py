from pydantic import BaseModel, ConfigDict

from src.models.enums import Role


class AgentRoleAssignment(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    role: Role
    secret_word: str | None
    topic: str
