from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Text,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    chat_session_id: Mapped[int] = (
        mapped_column(
            ForeignKey(
                "chat_sessions.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    intent_json: Mapped[
        dict | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    evidence_json: Mapped[
        dict | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    response_time_ms: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )