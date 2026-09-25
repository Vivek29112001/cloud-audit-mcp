from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.providers.aws.credentials import AWSCredentials


@dataclass
class AWSSessionEntry:
    credentials: AWSCredentials


class AWSCredentialSessionStore:
    """
    Legacy transient credential cache.

    Entries are scoped by (user_id, aws_connection_id) so switching between
    client workspaces cannot accidentally reuse another connection's keys.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[int, int], AWSSessionEntry] = {}
        self._lock = asyncio.Lock()

    async def set(
        self,
        *,
        user_id: int,
        aws_connection_id: int,
        credentials: AWSCredentials,
    ) -> None:
        async with self._lock:
            self._entries[(user_id, aws_connection_id)] = AWSSessionEntry(
                credentials=credentials,
            )

    async def get(
        self,
        *,
        user_id: int,
        aws_connection_id: int,
    ) -> AWSCredentials | None:
        async with self._lock:
            entry = self._entries.get((user_id, aws_connection_id))
            return entry.credentials if entry else None

    async def remove(
        self,
        *,
        user_id: int,
        aws_connection_id: int | None = None,
    ) -> None:
        async with self._lock:
            if aws_connection_id is not None:
                self._entries.pop((user_id, aws_connection_id), None)
                return

            keys = [key for key in self._entries if key[0] == user_id]
            for key in keys:
                self._entries.pop(key, None)


aws_credential_sessions = AWSCredentialSessionStore()
