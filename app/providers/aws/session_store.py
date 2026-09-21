from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.providers.aws.credentials import (
    AWSCredentials,
)


@dataclass
class AWSSessionEntry:
    credentials: AWSCredentials


class AWSCredentialSessionStore:

    def __init__(self) -> None:
        self._entries: dict[
            int,
            AWSSessionEntry,
        ] = {}

        self._lock = asyncio.Lock()

    async def set(
        self,
        *,
        user_id: int,
        credentials: AWSCredentials,
    ) -> None:
        async with self._lock:

            self._entries[user_id] = (
                AWSSessionEntry(
                    credentials=credentials,
                )
            )

    async def get(
        self,
        *,
        user_id: int,
    ) -> AWSCredentials | None:

        async with self._lock:

            entry = self._entries.get(
                user_id
            )

            if entry is None:
                return None

            return entry.credentials

    async def remove(
        self,
        *,
        user_id: int,
    ) -> None:

        async with self._lock:

            self._entries.pop(
                user_id,
                None,
            )


aws_credential_sessions = (
    AWSCredentialSessionStore()
)