from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class WorkspaceRenameRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    role: str
    status: str
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
