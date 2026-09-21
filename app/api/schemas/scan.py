from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PersistedAWSScanResponse(
    BaseModel
):
    scan_id: str

    database_id: int

    aws_connection_id: int

    status: str

    account: dict[str, Any]

    summary: dict[str, Any]

    regions: dict[str, Any]

    zones: dict[str, Any]

    resources: dict[str, Any]

    warnings: list[str]

    timings: dict[str, int]