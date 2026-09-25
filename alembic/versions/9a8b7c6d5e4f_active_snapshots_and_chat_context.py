"""active discovery snapshots and structured chat context

Revision ID: 9a8b7c6d5e4f
Revises: 4e9c1b0d2a11
Create Date: 2026-09-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "4e9c1b0d2a11"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_aws_scans_is_active", ["is_active"], unique=False)
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.add_column(sa.Column("context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.execute("""
        UPDATE aws_scans SET is_active = 1, activated_at = COALESCE(completed_at, started_at)
        WHERE id IN (
            SELECT s.id FROM aws_scans AS s WHERE s.id = (
                SELECT s2.id FROM aws_scans AS s2
                WHERE s2.user_id = s.user_id AND s2.aws_connection_id = s.aws_connection_id
                ORDER BY s2.started_at DESC, s2.id DESC LIMIT 1
            )
        )
    """)

def downgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.drop_column("context_json")
    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.drop_index("ix_aws_scans_is_active")
        batch_op.drop_column("activated_at")
        batch_op.drop_column("is_active")
