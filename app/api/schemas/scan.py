from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class PersistedAWSScanResponse(BaseModel):
    workspace_id: int
    scan_id: str
    database_id: int
    aws_connection_id: int
    status: str
    is_active: bool = False
    activated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    account: dict[str, Any]
    summary: dict[str, Any]
    regions: dict[str, Any]
    zones: dict[str, Any]
    resources: dict[str, Any]
    billing: dict[str, Any]
    classification: dict[str, Any]
    warnings: list[str]
    timings: dict[str, int]
