# from datetime import datetime

# from pydantic import BaseModel, Field


# class CreateChatRequest(BaseModel):
#     scan_id: str
#     title: str = Field(
#         default="New AWS Chat",
#         max_length=200,
#     )


# class RenameChatRequest(BaseModel):
#     title: str = Field(
#         min_length=1,
#         max_length=200,
#     )


# class ChatQueryRequest(BaseModel):
#     question: str = Field(
#         min_length=1,
#         max_length=4000,
#     )


# class ChatSessionResponse(BaseModel):
#     id: int
#     scan_id: str
#     aws_connection_id: int
#     title: str
#     created_at: datetime
#     updated_at: datetime


# class ChatMessageResponse(BaseModel):
#     id: int
#     role: str
#     content: str
#     response_time_ms: int | None
#     created_at: datetime



from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    scan_id: str
    title: str = Field(default="New AWS Chat", max_length=200)
    context: dict[str, Any] = Field(default_factory=dict)


class RenameChatRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatSessionResponse(BaseModel):
    id: int
    scan_id: str
    aws_connection_id: int
    title: str
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    response_time_ms: int | None
    created_at: datetime

