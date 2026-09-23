# from __future__ import annotations

# from fastapi import HTTPException
# from sqlalchemy.ext.asyncio import (
#     AsyncSession,
# )

# from app.db.models.user import User
# from app.repositories.aws_scan_repository import (
#     AWSScanRepository,
# )
# from app.repositories.chat_repository import (
#     ChatRepository,
# )


# class ChatService:

#     def __init__(self) -> None:
#         self._chats = ChatRepository()
#         self._scans = AWSScanRepository()

#     async def create_chat(
#         self,
#         db: AsyncSession,
#         *,
#         user: User,
#         scan_id: str,
#         title: str = "New AWS Chat",
#     ):
#         #
#         # Make sure this scan belongs
#         # to the authenticated user.
#         #
#         scan = (
#             await self._scans
#             .find_by_scan_id(
#                 db,
#                 scan_id=scan_id,
#                 user_id=user.id,
#             )
#         )

#         if scan is None:
#             raise HTTPException(
#                 status_code=404,
#                 detail=(
#                     "AWS scan not found for "
#                     "the authenticated user."
#                 ),
#             )

#         if scan.status != "COMPLETED":
#             raise HTTPException(
#                 status_code=409,
#                 detail=(
#                     "Chat can only be created "
#                     "for a completed AWS scan."
#                 ),
#             )

#         chat = (
#             await self._chats
#             .create_session(
#                 db,
#                 user_id=user.id,
#                 aws_connection_id=(
#                     scan.aws_connection_id
#                 ),
#                 scan_id=scan.scan_id,
#                 title=title,
#             )
#         )

#         #
#         # IMPORTANT:
#         # this is what actually persists
#         # chat_sessions into SQLite.
#         #
#         await db.commit()

#         await db.refresh(
#             chat
#         )

#         return chat



from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.repositories.aws_scan_repository import AWSScanRepository
from app.repositories.chat_repository import ChatRepository


class ChatService:
    def __init__(self) -> None:
        self._chats = ChatRepository()
        self._scans = AWSScanRepository()

    async def create_chat(
        self,
        db: AsyncSession,
        *,
        user: User,
        scan_id: str,
        title: str = "New AWS Chat",
        context: dict | None = None,
    ):
        scan = await self._scans.find_by_scan_id(
            db,
            scan_id=scan_id,
            user_id=user.id,
        )

        if scan is None:
            raise HTTPException(
                status_code=404,
                detail="AWS scan not found for the authenticated user.",
            )

        if scan.status != "COMPLETED":
            raise HTTPException(
                status_code=409,
                detail="Chat can only be created for a completed AWS scan.",
            )

        chat = await self._chats.create_session(
            db,
            user_id=user.id,
            aws_connection_id=scan.aws_connection_id,
            scan_id=scan.scan_id,
            title=title,
            context_json=dict(context or {}),
        )

        await db.commit()
        await db.refresh(chat)
        return chat


