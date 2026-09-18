from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class QueryExecution(Base):
    __tablename__ = "query_executions"

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

    service: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    operation: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    regions_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    params_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    timings_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    warnings_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )