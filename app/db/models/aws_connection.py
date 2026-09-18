from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class AWSConnection(Base):
    __tablename__ = "aws_connections"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "account_id",
            name=(
                "uq_aws_connection_"
                "user_account"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(32),
        default="AWS",
        nullable=False,
    )

    account_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    account_arn: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    last_connected_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )