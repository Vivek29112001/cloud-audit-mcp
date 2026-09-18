from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AWSRegionalQueryResult(BaseModel):
    region: str
    success: bool = True

    pages: int = 0

    data: Any = None

    error: str | None = None


class AWSQueryExecutionResult(BaseModel):
    service: str
    operation: str

    regions: list[str]

    successful_regions: list[str] = Field(
        default_factory=list
    )

    failed_regions: list[str] = Field(
        default_factory=list
    )

    results: list[
        AWSRegionalQueryResult
    ] = Field(default_factory=list)

    warnings: list[str] = Field(
        default_factory=list
    )