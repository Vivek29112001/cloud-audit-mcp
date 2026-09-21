from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.aws_connection import AWSConnection


class AWSConnectionRepository:
    async def find_by_user_and_account(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        account_id: str,
    ) -> AWSConnection | None:
        result = await db.execute(
            select(AWSConnection).where(
                AWSConnection.user_id == user_id,
                AWSConnection.account_id == account_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        account_id: str,
        account_arn: str | None,
    ) -> AWSConnection:
        connection = AWSConnection(
            user_id=user_id,
            provider="AWS",
            account_id=account_id,
            account_arn=account_arn,
            last_connected_at=datetime.now(
                timezone.utc
            ),
        )
        db.add(connection)
        await db.flush()
        return connection

    async def update_connection_time(
        self,
        connection: AWSConnection,
        *,
        account_arn: str | None,
    ) -> AWSConnection:
        connection.account_arn = account_arn
        connection.last_connected_at = datetime.now(
            timezone.utc
        )
        return connection

    async def find_all_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[AWSConnection]:
        result = await db.execute(
            select(AWSConnection)
            .where(AWSConnection.user_id == user_id)
            .order_by(
                AWSConnection.last_connected_at.desc()
            )
        )
        return list(result.scalars().all())
