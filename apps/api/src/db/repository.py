import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ActionLogORM, EpisodeORM
from src.models import ActionLog, EpisodeExport


class ActionLogRepository:
    @staticmethod
    async def bulk_insert(
        session: AsyncSession,
        episode_uuid: uuid.UUID,
        logs: list[ActionLog],
    ) -> int:
        """
        Bulk-inserts a list of ActionLog Pydantic models as ActionLogORM rows.
        Returns the count of inserted rows.

        Called internally by EpisodeRepository.create() — callers
        should NOT call this directly; use EpisodeRepository.create() instead.
        """
        if not logs:
            return 0

        orm_logs = []
        for log in logs:
            timestamp_dt = datetime.fromisoformat(log.timestamp)
            phase_val = (
                log.phase.value if hasattr(log.phase, "value") else str(log.phase)
            )
            orm_log = ActionLogORM(
                id=uuid.uuid4(),
                episode_id=episode_uuid,
                agent_id=log.agent_id,
                phase=phase_val,
                round_number=log.round_number,
                deliberation_round=log.deliberation_round,
                prompt_context=log.prompt_context,
                raw_llm_response=log.raw_llm_response,
                structured_output=log.structured_output,
                prompt_tokens=log.prompt_tokens,
                completion_tokens=log.completion_tokens,
                total_tokens=log.total_tokens,
                latency_ms=log.latency_ms,
                timestamp=timestamp_dt,
            )
            orm_logs.append(orm_log)

        session.add_all(orm_logs)
        await session.flush()
        return len(orm_logs)

    @staticmethod
    async def get_by_episode(
        session: AsyncSession,
        episode_id: str,
    ) -> list[ActionLog]:
        """
        Returns all ActionLog records for an episode, ordered by timestamp ASC.
        Returns [] if episode not found or has no logs.
        """
        try:
            episode_uuid = uuid.UUID(episode_id)
        except ValueError:
            return []

        stmt = (
            select(ActionLogORM)
            .where(ActionLogORM.episode_id == episode_uuid)
            .order_by(ActionLogORM.timestamp.asc())
        )
        result = await session.execute(stmt)
        orm_logs = result.scalars().all()

        pydantic_logs = []
        for orm in orm_logs:
            log = ActionLog(
                episode_id=str(orm.episode_id),
                agent_id=orm.agent_id,
                phase=orm.phase,
                round_number=orm.round_number,
                deliberation_round=orm.deliberation_round,
                prompt_context=orm.prompt_context,
                raw_llm_response=orm.raw_llm_response,
                structured_output=orm.structured_output,
                prompt_tokens=orm.prompt_tokens,
                completion_tokens=orm.completion_tokens,
                total_tokens=orm.total_tokens,
                latency_ms=orm.latency_ms,
                timestamp=orm.timestamp.isoformat(),
            )
            pydantic_logs.append(log)

        return pydantic_logs


class EpisodeRepository:
    @staticmethod
    async def create(session: AsyncSession, export: EpisodeExport) -> uuid.UUID:
        """
        Persists a completed EpisodeExport to the `episodes` table.
        Also bulk-inserts all ActionLog records into `action_logs`.
        Returns the UUID of the created episode row.

        Raises:
            sqlalchemy.exc.IntegrityError: if episode_id already exists
        """
        episode_uuid = uuid.UUID(export.episode_id)
        started_dt = datetime.fromisoformat(export.started_at)
        ended_dt = datetime.fromisoformat(export.ended_at)

        result_val = (
            export.result.value
            if hasattr(export.result, "value")
            else str(export.result)
        )
        episode_orm = EpisodeORM(
            id=episode_uuid,
            config=export.config.model_dump(),
            role_assignments=[r.model_dump() for r in export.role_assignments],
            started_at=started_dt,
            ended_at=ended_dt,
            result=result_val,
            elimination_result=export.elimination_result.model_dump(),
            export_json=export.model_dump(mode="json"),
        )

        session.add(episode_orm)
        await session.flush()

        # Bulk insert associated action logs
        if export.action_logs:
            await ActionLogRepository.bulk_insert(
                session, episode_uuid, export.action_logs
            )

        return episode_uuid

    @staticmethod
    async def get_by_id(session: AsyncSession, episode_id: str) -> EpisodeExport | None:
        """
        Retrieves a full EpisodeExport from the `export_json` JSONB column.
        Returns None if not found.
        """
        try:
            episode_uuid = uuid.UUID(episode_id)
        except ValueError:
            return None

        stmt = select(EpisodeORM).where(EpisodeORM.id == episode_uuid)
        result = await session.execute(stmt)
        episode_orm = result.scalar_one_or_none()

        if not episode_orm:
            return None

        return EpisodeExport(**episode_orm.export_json)

    @staticmethod
    async def list_recent(
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Returns a lightweight list of recent episodes.
        Returns dicts with: {id, started_at, ended_at, result, total_rounds_played}
        Does NOT return full EpisodeExport (too heavy for listing).
        """
        stmt = (
            select(EpisodeORM)
            .order_by(EpisodeORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        episodes_orm = result.scalars().all()

        lightweight_list = []
        for ep in episodes_orm:
            # Extract total rounds played from export_json
            total_rounds = ep.export_json.get("total_rounds_played", 0)
            lightweight_list.append(
                {
                    "id": str(ep.id),
                    "started_at": ep.started_at.isoformat(),
                    "ended_at": ep.ended_at.isoformat() if ep.ended_at else None,
                    "result": ep.result,
                    "total_rounds_played": total_rounds,
                }
            )

        return lightweight_list
