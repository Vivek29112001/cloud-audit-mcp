from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.providers.aws.credentials import AWSCredentials


class AWSMCPCollector(ABC):
    @property
    @abstractmethod
    def service_name(self) -> str:
        """AWS service handled by this collector."""

    @abstractmethod
    async def collect(
        self,
        credentials: AWSCredentials,
        regions: list[str],
    ) -> dict[str, Any]:
        """  Collect configuration only through
        the official AWS Managed MCP Server."""
