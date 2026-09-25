from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.aws_connection import AWSConnection
from app.db.models.aws_scan import AWSScan


class AWSScanRepository:
    async def save(self, db: AsyncSession, scan: AWSScan) -> AWSScan:
        db.add(scan)
        await db.flush()
        return scan

    async def find_by_scan_id(
        self,
        db: AsyncSession,
        *,
        scan_id: str,
        workspace_id: int,
    ) -> AWSScan | None:
        result = await db.execute(
            select(AWSScan).where(
                AWSScan.scan_id == scan_id,
                AWSScan.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_all_by_workspace(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
    ) -> list[AWSScan]:
        result = await db.execute(
            select(AWSScan)
            .where(AWSScan.workspace_id == workspace_id)
            .order_by(AWSScan.started_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_connection(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        aws_connection_id: int,
    ) -> list[AWSScan]:
        result = await db.execute(
            select(AWSScan)
            .where(
                AWSScan.workspace_id == workspace_id,
                AWSScan.aws_connection_id == aws_connection_id,
            )
            .order_by(AWSScan.started_at.desc())
        )
        return list(result.scalars().all())

    async def find_active_by_workspace(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        account_id: str | None = None,
    ) -> AWSScan | None:
        query = (
            select(AWSScan)
            .join(AWSConnection, AWSConnection.id == AWSScan.aws_connection_id)
            .where(
                AWSScan.workspace_id == workspace_id,
                AWSConnection.workspace_id == workspace_id,
                AWSScan.is_active.is_(True),
            )
        )
        if account_id:
            query = query.where(AWSConnection.account_id == account_id)
        result = await db.execute(
            query.order_by(
                AWSScan.activated_at.desc(),
                AWSScan.started_at.desc(),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def activate(self, db: AsyncSession, *, scan: AWSScan) -> AWSScan:
        await db.execute(
            update(AWSScan)
            .where(
                AWSScan.workspace_id == scan.workspace_id,
                AWSScan.aws_connection_id == scan.aws_connection_id,
                AWSScan.id != scan.id,
            )
            .values(is_active=False)
        )
        scan.is_active = True
        scan.activated_at = datetime.now(timezone.utc)
        await db.flush()
        return scan
