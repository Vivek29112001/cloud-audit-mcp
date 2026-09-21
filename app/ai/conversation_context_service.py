from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.ai.conversation_context import (
    ConversationContext,
    ConversationMessage,
)

from app.repositories.chat_repository import (
    ChatRepository,
)


class ConversationContextService:

    MAX_MESSAGES = 8

    def __init__(self) -> None:
        self._chat_repository = (
            ChatRepository()
        )

    async def build(
        self,
        db: AsyncSession,
        *,
        chat_session_id: int,
    ) -> ConversationContext:

        messages = (
            await self._chat_repository
            .get_recent_messages(
                db,
                chat_session_id=(
                    chat_session_id
                ),
                limit=self.MAX_MESSAGES,
            )
        )

        context_messages = [
            ConversationMessage(
                role=message.role,
                content=message.content,
            )
            for message in messages
            if message.role
            in {
                "user",
                "assistant",
            }
        ]

        return ConversationContext(
            messages=context_messages
        )