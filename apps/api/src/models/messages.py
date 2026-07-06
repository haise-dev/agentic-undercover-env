from pydantic import BaseModel, ConfigDict

from src.models.assignment import AgentRoleAssignment
from src.models.enums import Phase


class PublicMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    display_name: str
    phase: Phase
    round_number: int
    deliberation_round: int | None = None
    content: str
    timestamp: str


class SystemAnnouncement(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: Phase
    round_number: int
    content: str
    timestamp: str


class RoundContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    role_assignment: AgentRoleAssignment
    current_phase: Phase
    current_round: int
    deliberation_round: int | None
    public_history: list[PublicMessage]
    announcements: list[SystemAnnouncement]
    alive_agents: list[dict[str, str]]
    all_agent_names: str
    game_language: str
    is_final_round: bool = False
