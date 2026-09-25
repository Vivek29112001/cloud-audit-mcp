from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AWSConnection(Base):
    __tablename__ = "aws_connections"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "account_id",
            name="uq_aws_connection_workspace_account",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Creator/audit identity. Workspace is the tenant boundary.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), default="AWS", nullable=False)
    account_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_arn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Connection-level authentication configuration.
    # PERSISTED_KEYS: encrypted client access keys (POC/backward-compatible).
    # ASSUME_ROLE: production cross-account role assumed automatically via STS.
    auth_type: Mapped[str] = mapped_column(
        String(32), default="TRANSIENT_KEYS", nullable=False, index=True
    )
    default_region: Mapped[str] = mapped_column(
        String(64), default="us-east-1", nullable=False
    )
    role_arn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    credential_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_status: Mapped[str] = mapped_column(
        String(32), default="CONFIGURED", nullable=False
    )
    last_auth_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
