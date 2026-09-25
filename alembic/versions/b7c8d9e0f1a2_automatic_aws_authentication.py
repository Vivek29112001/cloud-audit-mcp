"""automatic AWS authentication configuration

Revision ID: b7c8d9e0f1a2
Revises: 9a8b7c6d5e4f
Create Date: 2026-09-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "9a8b7c6d5e4f"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("aws_connections") as batch_op:
        batch_op.add_column(sa.Column("auth_type", sa.String(length=32), nullable=False, server_default="TRANSIENT_KEYS"))
        batch_op.add_column(sa.Column("default_region", sa.String(length=64), nullable=False, server_default="us-east-1"))
        batch_op.add_column(sa.Column("role_arn", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("external_id", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("credential_ciphertext", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("auth_status", sa.String(length=32), nullable=False, server_default="CONFIGURED"))
        batch_op.add_column(sa.Column("last_auth_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_aws_connections_auth_type", ["auth_type"], unique=False)

def downgrade() -> None:
    with op.batch_alter_table("aws_connections") as batch_op:
        batch_op.drop_index("ix_aws_connections_auth_type")
        batch_op.drop_column("last_verified_at")
        batch_op.drop_column("last_auth_error")
        batch_op.drop_column("auth_status")
        batch_op.drop_column("credential_ciphertext")
        batch_op.drop_column("external_id")
        batch_op.drop_column("role_arn")
        batch_op.drop_column("default_region")
        batch_op.drop_column("auth_type")
