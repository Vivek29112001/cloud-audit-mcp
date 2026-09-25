from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.aws_connection import AWSConnection


class AWSConnectionRepository:
    async def find_by_workspace_and_account(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        account_id: str,
    ) -> AWSConnection | None:
        result = await db.execute(
            select(AWSConnection).where(
                AWSConnection.workspace_id == workspace_id,
                AWSConnection.account_id == account_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_id(
        self,
        db: AsyncSession,
        *,
        connection_id: int,
        workspace_id: int,
    ) -> AWSConnection | None:
        result = await db.execute(
            select(AWSConnection).where(
                AWSConnection.id == connection_id,
                AWSConnection.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user_id: int,
        account_id: str,
        account_arn: str | None,
    ) -> AWSConnection:
        now = datetime.now(timezone.utc)
        connection = AWSConnection(
            workspace_id=workspace_id,
            user_id=user_id,
            provider="AWS",
            account_id=account_id,
            account_arn=account_arn,
            last_connected_at=now,
            last_verified_at=now,
        )
        db.add(connection)
        await db.flush()
        return connection

    async def upsert_auth_config(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user_id: int,
        account_id: str,
        account_arn: str | None,
        auth_type: str,
        default_region: str,
        role_arn: str | None = None,
        external_id: str | None = None,
        credential_ciphertext: str | None = None,
    ) -> AWSConnection:
        connection = await self.find_by_workspace_and_account(
            db,
            workspace_id=workspace_id,
            account_id=account_id,
        )
        if connection is None:
            connection = await self.create(
                db,
                workspace_id=workspace_id,
                user_id=user_id,
                account_id=account_id,
                account_arn=account_arn,
            )
        now = datetime.now(timezone.utc)
        connection.account_arn = account_arn
        connection.auth_type = auth_type
        connection.default_region = default_region or "us-east-1"
        connection.role_arn = role_arn
        connection.external_id = external_id
        connection.credential_ciphertext = credential_ciphertext
        connection.auth_status = "VERIFIED"
        connection.last_auth_error = None
        connection.last_verified_at = now
        connection.last_connected_at = now
        await db.flush()
        return connection

    async def mark_auth_success(self, connection: AWSConnection) -> None:
        now = datetime.now(timezone.utc)
        connection.auth_status = "VERIFIED"
        connection.last_auth_error = None
        connection.last_verified_at = now
        connection.last_connected_at = now

    async def mark_auth_error(self, connection: AWSConnection, message: str) -> None:
        connection.auth_status = "ERROR"
        connection.last_auth_error = message[:4000]

    async def update_connection_time(
        self,
        connection: AWSConnection,
        *,
        account_arn: str | None,
    ) -> AWSConnection:
        connection.account_arn = account_arn
        connection.last_connected_at = datetime.now(timezone.utc)
        return connection

    async def find_all_by_workspace(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
    ) -> list[AWSConnection]:
        result = await db.execute(
            select(AWSConnection)
            .where(AWSConnection.workspace_id == workspace_id)
            .order_by(AWSConnection.last_connected_at.desc())
        )
        return list(result.scalars().all())
