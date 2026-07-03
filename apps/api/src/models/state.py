from pydantic import BaseModel, ConfigDict, Field

from src.models.assignment import AgentRoleAssignment
from src.models.config import EpisodeConfig
from src.models.enums import GameResult, Phase, Role
from src.models.messages import PublicMessage, SystemAnnouncement
from src.models.votes import EliminationResult, PollRecord, VoteRecord


class GameState(BaseModel):
    model_config = ConfigDict(frozen=False)  # MUTABLE — engine only

    # Identity
    episode_id: str
    config: EpisodeConfig

    # Role assignments — keyed by agent_id
    role_assignments: dict[str, AgentRoleAssignment]

    # Turn tracking
    current_turn_order: list[str]  # list of agent_ids in current round order
    current_phase: Phase = Phase.INIT
    current_round: int = 1
    current_deliberation_round: int = 1

    # Agent liveness
    agent_alive: dict[str, bool]  # {agent_id: True/False}

    # Full history (never reset — needed for complete log)
    all_messages: list[PublicMessage] = Field(default_factory=list)
    all_announcements: list[SystemAnnouncement] = Field(default_factory=list)

    # Vote history
    poll_history: dict[int, list[PollRecord]] = Field(default_factory=dict)
    vote_records: list[VoteRecord] = Field(default_factory=list)
    elimination_result: EliminationResult | None = None

    # Result
    result: GameResult | None = None
    winning_agent_ids: list[str] | None = None

    # Timestamps
    started_at: str  # ISO 8601 UTC, set at INIT
    ended_at: str | None = None

    # ── Computed properties ─────────────────────────────────────
    @property
    def alive_agent_ids(self) -> list[str]:
        """Returns list of agent_ids that are still alive, in stable order."""
        return [aid for aid, alive in self.agent_alive.items() if alive]

    @property
    def imposter_id(self) -> str:
        """Returns the agent_id of the Imposter. Raises StopIteration if not found."""
        return next(
            aid for aid, ra in self.role_assignments.items() if ra.role == Role.IMPOSTER
        )

    @property
    def messages_in_current_round(self) -> list[PublicMessage]:
        """Returns only messages from the current Speaking round.
        Used for context injection.
        """
        return [m for m in self.all_messages if m.round_number == self.current_round]
