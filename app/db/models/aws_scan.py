# from __future__ import annotations

# from datetime import datetime

# from sqlalchemy import (
#     DateTime,
#     ForeignKey,
#     Integer,
#     JSON,
#     String,
# )
# from sqlalchemy.orm import (
#     Mapped,
#     mapped_column,
# )

# from app.db.base import Base


# class AWSScan(Base):
#     __tablename__ = "aws_scans"

#     id: Mapped[int] = mapped_column(
#         Integer,
#         primary_key=True,
#         autoincrement=True,
#     )

#     scan_id: Mapped[str] = mapped_column(
#         String(64),
#         unique=True,
#         nullable=False,
#         index=True,
#     )

#     user_id: Mapped[int] = mapped_column(
#         ForeignKey(
#             "users.id",
#             ondelete="CASCADE",
#         ),
#         nullable=False,
#         index=True,
#     )

#     aws_connection_id: Mapped[int] = (
#         mapped_column(
#             ForeignKey(
#                 "aws_connections.id",
#                 ondelete="CASCADE",
#             ),
#             nullable=False,
#             index=True,
#         )
#     )

#     status: Mapped[str] = mapped_column(
#         String(32),
#         nullable=False,
#     )

#     started_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True),
#         nullable=False,
#     )

#     completed_at: Mapped[
#         datetime | None
#     ] = mapped_column(
#         DateTime(timezone=True),
#         nullable=True,
#     )

#     account_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     summary_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     regions_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     zones_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     resources_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     billing_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     classification_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )

#     warnings_json: Mapped[list] = mapped_column(
#         JSON,
#         default=list,
#         nullable=False,
#     )

#     timings_json: Mapped[dict] = mapped_column(
#         JSON,
#         default=dict,
#         nullable=False,
#     )


from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AWSScan(Base):
    __tablename__ = "aws_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aws_connection_id: Mapped[int] = mapped_column(
        ForeignKey("aws_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Discovery snapshots are immutable. This flag only points at the snapshot
    # currently selected for an AWS connection; refreshing creates a new row.
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    regions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    zones_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    resources_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    billing_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    classification_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    timings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


