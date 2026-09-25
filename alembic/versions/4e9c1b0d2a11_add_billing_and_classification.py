"""add billing and classification json to aws scans

Revision ID: 4e9c1b0d2a11
Revises: d7815c1a9394
Create Date: 2026-09-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "4e9c1b0d2a11"
down_revision: Union[str, Sequence[str], None] = "d7815c1a9394"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.add_column(sa.Column("billing_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("classification_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

def downgrade() -> None:
    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.drop_column("classification_json")
        batch_op.drop_column("billing_json")
