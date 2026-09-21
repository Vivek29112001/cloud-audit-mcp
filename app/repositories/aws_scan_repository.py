from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.aws_scan import AWSScan


class AWSScanRepository:
    async def save(
        self,
        db: AsyncSession,
        scan: AWSScan,
    ) -> AWSScan:
        db.add(scan)
        await db.flush()
        return scan

    async def find_by_scan_id(
        self,
        db: AsyncSession,
        *,
        scan_id: str,
        user_id: int,
    ) -> AWSScan | None:
        result = await db.execute(
            select(AWSScan).where(
                AWSScan.scan_id == scan_id,
                AWSScan.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_all_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[AWSScan]:
        result = await db.execute(
            select(AWSScan)
            .where(AWSScan.user_id == user_id)
            .order_by(AWSScan.started_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_connection(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        aws_connection_id: int,
    ) -> list[AWSScan]:
        result = await db.execute(
            select(AWSScan)
            .where(
                AWSScan.user_id == user_id,
                AWSScan.aws_connection_id
                == aws_connection_id,
            )
            .order_by(AWSScan.started_at.desc())
        )
        return list(result.scalars().all())
