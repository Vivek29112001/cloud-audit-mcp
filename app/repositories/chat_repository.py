# from __future__ import annotations

# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.models.chat_message import ChatMessage
# from app.db.models.chat_session import ChatSession


# class ChatRepository:
#     async def create_session(
#         self,
#         db: AsyncSession,
#         *,
#         user_id: int,
#         aws_connection_id: int,
#         scan_id: str,
#         title: str = "New AWS Chat",
#     ) -> ChatSession:
#         session = ChatSession(
#             user_id=user_id,
#             aws_connection_id=aws_connection_id,
#             scan_id=scan_id,
#             title=title,
#         )
#         db.add(session)
#         await db.commit()
#         await db.refresh(session)
#         return session

#     async def find_session(
#         self,
#         db: AsyncSession,
#         *,
#         chat_id: int,
#         user_id: int,
#     ) -> ChatSession | None:
#         result = await db.execute(
#             select(ChatSession).where(
#                 ChatSession.id == chat_id,
#                 ChatSession.user_id == user_id,
#             )
#         )
#         return result.scalar_one_or_none()

#     async def list_sessions(
#         self,
#         db: AsyncSession,
#         *,
#         user_id: int,
#         scan_id: str | None = None,
#         aws_connection_id: int | None = None,
#     ) -> list[ChatSession]:
#         query = select(ChatSession).where(
#             ChatSession.user_id == user_id
#         )

#         if scan_id:
#             query = query.where(
#                 ChatSession.scan_id == scan_id
#             )

#         if aws_connection_id:
#             query = query.where(
#                 ChatSession.aws_connection_id
#                 == aws_connection_id
#             )

#         query = query.order_by(
#             ChatSession.updated_at.desc()
#         )

#         result = await db.execute(query)
#         return list(result.scalars().all())

#     async def add_message(
#         self,
#         db: AsyncSession,
#         *,
#         chat_session_id: int,
#         role: str,
#         content: str,
#         intent_json: dict | None = None,
#         evidence_json: dict | None = None,
#         response_time_ms: int | None = None,
#     ) -> ChatMessage:
#         message = ChatMessage(
#             chat_session_id=chat_session_id,
#             role=role,
#             content=content,
#             intent_json=intent_json,
#             evidence_json=evidence_json,
#             response_time_ms=response_time_ms,
#         )
#         db.add(message)
#         await db.flush()
#         return message

#     async def list_messages(
#         self,
#         db: AsyncSession,
#         *,
#         chat_session_id: int,
#     ) -> list[ChatMessage]:
#         result = await db.execute(
#             select(ChatMessage)
#             .where(
#                 ChatMessage.chat_session_id
#                 == chat_session_id
#             )
#             .order_by(
#                 ChatMessage.created_at.asc()
#             )
#         )
#         return list(result.scalars().all())

#     async def get_recent_messages(
#         self,
#         db: AsyncSession,
#         *,
#         chat_session_id: int,
#         limit: int = 8,
#     ) -> list[ChatMessage]:
#         result = await db.execute(
#             select(ChatMessage)
#             .where(
#                 ChatMessage.chat_session_id
#                 == chat_session_id
#             )
#             .order_by(
#                 ChatMessage.created_at.desc()
#             )
#             .limit(limit)
#         )

#         messages = list(result.scalars().all())
#         messages.reverse()
#         return messages

#     async def update_title(
#         self,
#         db: AsyncSession,
#         *,
#         chat: ChatSession,
#         title: str,
#     ) -> ChatSession:
#         chat.title = title
#         await db.flush()
#         return chat

#     async def delete_session(
#         self,
#         db: AsyncSession,
#         *,
#         chat: ChatSession,
#     ) -> None:
#         await db.delete(chat)
#         await db.flush()



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
        user_id: int,
        aws_connection_id: int,
        scan_id: str,
        title: str = "New AWS Chat",
        context_json: dict | None = None,
    ) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            aws_connection_id=aws_connection_id,
            scan_id=scan_id,
            title=title,
            context_json=dict(context_json or {}),
        )
        db.add(session)
        await db.flush()
        return session

    async def find_session(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        user_id: int,
    ) -> ChatSession | None:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == chat_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        scan_id: str | None = None,
        aws_connection_id: int | None = None,
    ) -> list[ChatSession]:
        query = select(ChatSession).where(ChatSession.user_id == user_id)

        if scan_id:
            query = query.where(ChatSession.scan_id == scan_id)

        if aws_connection_id:
            query = query.where(ChatSession.aws_connection_id == aws_connection_id)

        query = query.order_by(ChatSession.updated_at.desc())
        result = await db.execute(query)
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
        # SQLAlchemy JSON columns require JSON-native values. Persisted scan
        # evidence can contain datetime/date values loaded from ORM models;
        # normalize them at the repository boundary so a chat response can
        # never fail during flush solely because of serialization.
        safe_intent = (
            jsonable_encoder(intent_json)
            if intent_json is not None
            else None
        )
        safe_evidence = (
            jsonable_encoder(evidence_json)
            if evidence_json is not None
            else None
        )

        message = ChatMessage(
            chat_session_id=chat_session_id,
            role=role,
            content=content,
            intent_json=safe_intent,
            evidence_json=safe_evidence,
            response_time_ms=response_time_ms,
        )
        db.add(message)
        await db.flush()
        return message

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
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

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


