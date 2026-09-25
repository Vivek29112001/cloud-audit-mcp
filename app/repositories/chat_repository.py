from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_message import ChatMessage
from app.db.models.chat_session import ChatSession


class ChatRepository:
    async def create_session(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user_id: int,
        aws_connection_id: int,
        scan_id: str,
        title: str = "New AWS Chat",
        context_json: dict | None = None,
    ) -> ChatSession:
        chat = ChatSession(
            workspace_id=workspace_id,
            user_id=user_id,
            aws_connection_id=aws_connection_id,
            scan_id=scan_id,
            title=title,
            context_json=dict(context_json or {}),
        )
        db.add(chat)
        await db.flush()
        return chat

    async def find_session(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        workspace_id: int,
        user_id: int,
    ) -> ChatSession | None:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == chat_id,
                ChatSession.workspace_id == workspace_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user_id: int,
        scan_id: str | None = None,
        aws_connection_id: int | None = None,
    ) -> list[ChatSession]:
        query = select(ChatSession).where(
            ChatSession.workspace_id == workspace_id,
            ChatSession.user_id == user_id,
        )
        if scan_id:
            query = query.where(ChatSession.scan_id == scan_id)
        if aws_connection_id:
            query = query.where(ChatSession.aws_connection_id == aws_connection_id)
        result = await db.execute(query.order_by(ChatSession.updated_at.desc()))
        return list(result.scalars().all())

    async def add_message(
        self,
        db: AsyncSession,
        *,
        chat_session_id: int,
        role: str,
        content: str,
        intent_json: dict | None = None,
        evidence_json: dict | None = None,
        response_time_ms: int | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            chat_session_id=chat_session_id,
            role=role,
            content=content,
            intent_json=(jsonable_encoder(intent_json) if intent_json is not None else None),
            evidence_json=(jsonable_encoder(evidence_json) if evidence_json is not None else None),
            response_time_ms=response_time_ms,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def list_messages(
        self,
        db: AsyncSession,
        *,
        chat_session_id: int,
    ) -> list[ChatMessage]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == chat_session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        db: AsyncSession,
        *,
        chat_session_id: int,
        limit: int = 8,
    ) -> list[ChatMessage]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == chat_session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def update_title(
        self,
        db: AsyncSession,
        *,
        chat: ChatSession,
        title: str,
    ) -> ChatSession:
        chat.title = title
        await db.flush()
        return chat

    async def delete_session(
        self,
        db: AsyncSession,
        *,
        chat: ChatSession,
    ) -> None:
        await db.delete(chat)
        await db.flush()
