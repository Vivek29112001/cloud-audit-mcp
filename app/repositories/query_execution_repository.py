from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.query_execution import QueryExecution


class QueryExecutionRepository:
    async def create(
        self,
        db: AsyncSession,
        *,
        chat_session_id: int,
        service: str,
        operation: str,
        regions: list[str],
        params: dict,
        status: str,
        timings: dict,
        warnings: list,
    ) -> QueryExecution:
        execution = QueryExecution(
            chat_session_id=chat_session_id,
            service=service,
            operation=operation,
            regions_json=regions,
            params_json=params,
            status=status,
            timings_json=timings,
            warnings_json=warnings,
        )
        db.add(execution)
        await db.flush()
        return execution
