from typing import Any

from pydantic import BaseModel, Field


class AWSQueryResult(BaseModel):
    service: str

    operation: str

    regions: list[str]

    item_count: int | None = None

    data: Any

    warnings: list[str] = Field(
        default_factory=list
    )