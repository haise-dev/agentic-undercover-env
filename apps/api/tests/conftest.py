import os
import uuid
from datetime import UTC, datetime

import pytest

# Set mock environment variables before importing any application code
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["APP_ENV"] = "test"

# Import models now that env vars are set
from src.models import (
    AgentConfig,
    AgentLLMConfig,
    AgentRoleAssignment,
    AgentType,
    EpisodeConfig,
    GameState,
    LLMProvider,
    Role,
)

# ── Primitive helpers ──────────────────────────────────────────────────────────

def now_iso() -> str:
    """Returns current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def make_uuid() -> str:
    return str(uuid.uuid4())


# ── LLM config fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def llm_config() -> AgentLLMConfig:
    """Default AI agent LLM config using Groq (free tier)."""
    return AgentLLMConfig(
        provider=LLMProvider.GROQ,
        smart_model_name="llama-3.3-70b-versatile",
        fast_model_name="llama3-8b-8192",
    )


# ── Agent config factory ───────────────────────────────────────────────────────

_AGENT_NAMES  = ["Alice", "Bob", "Charlie", "Diana"]
_AGENT_COLORS = ["cyan", "magenta", "yellow", "green"]


@pytest.fixture
def make_agent_config(llm_config):
    """Factory fixture: make_agent_config(index, agent_type) -> AgentConfig."""
    def _make(index: int, agent_type: AgentType = AgentType.AI) -> AgentConfig:
        assert 0 <= index <= 3, "Agent index must be 0-3"
        return AgentConfig(
            agent_id=f"agent_{index}",
            display_name=_AGENT_NAMES[index],
            display_color=_AGENT_COLORS[index],
            agent_type=agent_type,
            llm_config=llm_config if agent_type == AgentType.AI else None,
        )
    return _make


# ── Episode config fixture ─────────────────────────────────────────────────────

@pytest.fixture
def episode_config(make_agent_config) -> EpisodeConfig:
    """4-agent episode config. agent_0 = Imposter by convention in tests."""
    return EpisodeConfig(
        episode_id=make_uuid(),
        topic="Fruit",
        secret_word="Durian",
        agents=[make_agent_config(i) for i in range(4)],
        max_rounds=3,
    )


# ── Role assignments fixture ───────────────────────────────────────────────────

@pytest.fixture
def role_assignments() -> dict[str, AgentRoleAssignment]:
    """
    Standard 4-agent role assignment.
    agent_0 = IMPOSTER (secret_word=None)
    agent_1,2,3 = VILLAGER (secret_word="Durian")
    """
    return {
        "agent_0": AgentRoleAssignment(
            agent_id="agent_0", role=Role.IMPOSTER,
            secret_word=None, topic="Fruit",
        ),
        "agent_1": AgentRoleAssignment(
            agent_id="agent_1", role=Role.VILLAGER,
            secret_word="Durian", topic="Fruit",
        ),
        "agent_2": AgentRoleAssignment(
            agent_id="agent_2", role=Role.VILLAGER,
            secret_word="Durian", topic="Fruit",
        ),
        "agent_3": AgentRoleAssignment(
            agent_id="agent_3", role=Role.VILLAGER,
            secret_word="Durian", topic="Fruit",
        ),
    }


# ── GameState fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def game_state(episode_config, role_assignments) -> GameState:
    """Fresh GameState at INIT phase, all 4 agents alive."""
    return GameState(
        episode_id=episode_config.episode_id,
        config=episode_config,
        role_assignments=role_assignments,
        current_turn_order=["agent_0", "agent_1", "agent_2", "agent_3"],
        agent_alive={
            "agent_0": True,
            "agent_1": True,
            "agent_2": True,
            "agent_3": True,
        },
        started_at=now_iso(),
    )
