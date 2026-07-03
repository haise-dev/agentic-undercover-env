import uuid
from datetime import datetime

from sqlalchemy import (
    INT,
    JSON,
    TEXT,
    TIMESTAMP,
    UUID,
    VARCHAR,
    ForeignKey,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Use JSONB on PostgreSQL and fallback to standard JSON on SQLite (integration tests)
JSONB_VARIANT = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class EpisodeORM(Base):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    config: Mapped[dict] = mapped_column(JSONB_VARIANT, nullable=False)
    role_assignments: Mapped[list] = mapped_column(JSONB_VARIANT, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    result: Mapped[str | None] = mapped_column(VARCHAR(20), nullable=True)
    elimination_result: Mapped[dict | None] = mapped_column(
        JSONB_VARIANT, nullable=True
    )
    export_json: Mapped[dict] = mapped_column(JSONB_VARIANT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    action_logs: Mapped[list["ActionLogORM"]] = relationship(
        "ActionLogORM", back_populates="episode", cascade="all, delete-orphan"
    )


class ActionLogORM(Base):
    __tablename__ = "action_logs"
    __table_args__ = (
        Index("idx_action_logs_episode_id", "episode_id"),
        Index("idx_action_logs_agent_phase", "episode_id", "agent_id", "phase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    episode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    phase: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    round_number: Mapped[int] = mapped_column(INT, nullable=False)
    deliberation_round: Mapped[int | None] = mapped_column(INT, nullable=True)
    prompt_context: Mapped[dict] = mapped_column(JSONB_VARIANT, nullable=False)
    raw_llm_response: Mapped[str] = mapped_column(TEXT, nullable=False)
    structured_output: Mapped[dict] = mapped_column(JSONB_VARIANT, nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(INT, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(INT, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(INT, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(INT, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    episode: Mapped["EpisodeORM"] = relationship(
        "EpisodeORM", back_populates="action_logs"
    )
