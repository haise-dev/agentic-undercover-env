"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-03
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "episodes",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("role_assignments", JSONB(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("result", sa.VARCHAR(20), nullable=True),
        sa.Column("elimination_result", JSONB(), nullable=True),
        sa.Column("export_json", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "action_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("episode_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", sa.VARCHAR(20), nullable=False),
        sa.Column("phase", sa.VARCHAR(20), nullable=False),
        sa.Column("round_number", sa.INT(), nullable=False),
        sa.Column("deliberation_round", sa.INT(), nullable=True),
        sa.Column("prompt_context", JSONB(), nullable=False),
        sa.Column("raw_llm_response", sa.TEXT(), nullable=False),
        sa.Column("structured_output", JSONB(), nullable=False),
        sa.Column("prompt_tokens", sa.INT(), nullable=True),
        sa.Column("completion_tokens", sa.INT(), nullable=True),
        sa.Column("total_tokens", sa.INT(), nullable=True),
        sa.Column("latency_ms", sa.INT(), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_action_logs_episode_id", "action_logs", ["episode_id"])
    op.create_index(
        "idx_action_logs_agent_phase",
        "action_logs",
        ["episode_id", "agent_id", "phase"],
    )


def downgrade() -> None:
    op.drop_index("idx_action_logs_agent_phase", table_name="action_logs")
    op.drop_index("idx_action_logs_episode_id", table_name="action_logs")
    op.drop_table("action_logs")
    op.drop_table("episodes")
