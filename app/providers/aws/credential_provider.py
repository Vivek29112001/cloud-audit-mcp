from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.aws_connection import AWSConnection
from app.providers.aws.assume_role import AWSAssumeRoleError, AWSAssumeRoleService
from app.providers.aws.credential_crypto import AWSCredentialCipher
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.session_store import aws_credential_sessions
from app.repositories.aws_connection_repository import AWSConnectionRepository


class AWSAutomaticAuthenticationError(RuntimeError):
    pass


@dataclass
class _CachedCredentials:
    credentials: AWSCredentials


class AWSCredentialProvider:
    """
    Connection-level AWS credential resolver.

    The caller supplies user_id + workspace_id + aws_connection_id. The provider decides
    whether to decrypt persisted POC keys, automatically assume a cross-account
    role, or fall back to a legacy transient runtime credential.
    """

    def __init__(self) -> None:
        self._connections = AWSConnectionRepository()
        self._assume_role = AWSAssumeRoleService()
        self._cipher: AWSCredentialCipher | None = None
        self._cache: dict[int, _CachedCredentials] = {}
        self._cache_lock = asyncio.Lock()
        self._connection_locks: dict[int, asyncio.Lock] = {}

    async def get_credentials(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        workspace_id: int,
        aws_connection_id: int,
    ) -> AWSCredentials:
        connection = await self._connections.find_by_id(
            db,
            connection_id=aws_connection_id,
            workspace_id=workspace_id,
        )
        if connection is None:
            raise AWSAutomaticAuthenticationError("AWS connection not found.")

        cached = await self._get_valid_cached(connection.id)
        if cached is not None:
            return cached

        lock = await self._lock_for(connection.id)
        async with lock:
            # Another request may have refreshed credentials while this request
            # was waiting for the per-connection lock.
            cached = await self._get_valid_cached(connection.id)
            if cached is not None:
                return cached

            try:
                credentials = await self._resolve(
                    db=db,
                    user_id=user_id,
                    connection=connection,
                )
            except Exception as exc:
                await self._connections.mark_auth_error(connection, str(exc))
                await db.commit()
                if isinstance(exc, AWSAutomaticAuthenticationError):
                    raise
                raise AWSAutomaticAuthenticationError(str(exc)) from exc

            async with self._cache_lock:
                self._cache[connection.id] = _CachedCredentials(
                    credentials=credentials
                )

            await self._connections.mark_auth_success(connection)
            await db.commit()
            return credentials

    async def _get_valid_cached(
        self,
        connection_id: int,
    ) -> AWSCredentials | None:
        async with self._cache_lock:
            cached = self._cache.get(connection_id)
            if cached and cached.credentials.valid_for(
                settings.aws_sts_refresh_skew_seconds
            ):
                return cached.credentials
            if cached:
                self._cache.pop(connection_id, None)
        return None

    async def _lock_for(self, connection_id: int) -> asyncio.Lock:
        async with self._cache_lock:
            lock = self._connection_locks.get(connection_id)
            if lock is None:
                lock = asyncio.Lock()
                self._connection_locks[connection_id] = lock
            return lock

    async def _resolve(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        connection: AWSConnection,
    ) -> AWSCredentials:
        auth_type = (connection.auth_type or "TRANSIENT_KEYS").upper()

        if auth_type == "ASSUME_ROLE":
            if not connection.role_arn:
                raise AWSAutomaticAuthenticationError(
                    "AWS connection has no role ARN configured."
                )
            try:
                return await self._assume_role.assume_role(
                    role_arn=connection.role_arn,
                    external_id=connection.external_id,
                    default_region=connection.default_region,
                    connection_id=connection.id,
                )
            except AWSAssumeRoleError as exc:
                raise AWSAutomaticAuthenticationError(str(exc)) from exc

        if auth_type == "PERSISTED_KEYS":
            if not connection.credential_ciphertext:
                raise AWSAutomaticAuthenticationError(
                    "Encrypted AWS credentials are not configured for this connection."
                )
            if self._cipher is None:
                self._cipher = AWSCredentialCipher()
            credentials = self._cipher.decrypt(connection.credential_ciphertext)
            credentials.default_region = (
                connection.default_region or credentials.default_region
            )
            credentials.source = "PERSISTED_ENCRYPTED_KEYS"
            return credentials

        credentials = await aws_credential_sessions.get(
            user_id=user_id,
            aws_connection_id=connection.id,
        )
        if credentials is None:
            raise AWSAutomaticAuthenticationError(
                "This legacy AWS connection only has transient credentials. "
                "Reconnect once to save encrypted POC credentials, or configure ASSUME_ROLE."
            )
        return credentials

    async def clear_cache(
        self,
        *,
        aws_connection_id: int | None = None,
    ) -> None:
        async with self._cache_lock:
            if aws_connection_id is None:
                self._cache.clear()
            else:
                self._cache.pop(aws_connection_id, None)

    @staticmethod
    def auto_connect_capable(connection: AWSConnection) -> bool:
        auth_type = (connection.auth_type or "").upper()
        if auth_type == "ASSUME_ROLE":
            return bool(connection.role_arn)
        if auth_type == "PERSISTED_KEYS":
            return bool(connection.credential_ciphertext)
        return False


aws_credential_provider = AWSCredentialProvider()
