"""multi-client workspace tenant boundary

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-25
"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "created_by_user_id",
            "name",
            name="uq_workspace_creator_name",
        ),
    )
    op.create_index("ix_workspaces_name", "workspaces", ["name"], unique=False)
    op.create_index(
        "ix_workspaces_created_by_user_id",
        "workspaces",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index("ix_workspaces_status", "workspaces", ["status"], unique=False)

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="OWNER"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index(
        "ix_workspace_members_workspace_id",
        "workspace_members",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_members_status",
        "workspace_members",
        ["status"],
        unique=False,
    )

    # Add workspace IDs as nullable first so existing Phase 2 data can be
    # migrated into one default workspace per existing user.
    with op.batch_alter_table("aws_connections") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))

    bind = op.get_bind()
    users = bind.execute(
        sa.text("SELECT id, username FROM users ORDER BY id")
    ).mappings().all()
    now = datetime.now(timezone.utc)

    for user in users:
        username = (user.get("username") or f"User {user['id']}").strip()
        workspace_name = f"{username} Workspace"[:150]
        result = bind.execute(
            sa.text(
                """
                INSERT INTO workspaces
                    (name, created_by_user_id, status, created_at, updated_at)
                VALUES
                    (:name, :user_id, 'ACTIVE', :created_at, :updated_at)
                """
            ),
            {
                "name": workspace_name,
                "user_id": user["id"],
                "created_at": now,
                "updated_at": now,
            },
        )
        workspace_id = result.lastrowid

        bind.execute(
            sa.text(
                """
                INSERT INTO workspace_members
                    (workspace_id, user_id, role, status, created_at)
                VALUES
                    (:workspace_id, :user_id, 'OWNER', 'ACTIVE', :created_at)
                """
            ),
            {
                "workspace_id": workspace_id,
                "user_id": user["id"],
                "created_at": now,
            },
        )

        for table_name in ("aws_connections", "aws_scans", "chat_sessions"):
            bind.execute(
                sa.text(
                    f"UPDATE {table_name} "
                    "SET workspace_id = :workspace_id "
                    "WHERE user_id = :user_id AND workspace_id IS NULL"
                ),
                {
                    "workspace_id": workspace_id,
                    "user_id": user["id"],
                },
            )

    # Make workspace the tenant boundary and the AWS-account uniqueness scope.
    with op.batch_alter_table("aws_connections") as batch_op:
        batch_op.drop_constraint("uq_aws_connection_user_account", type_="unique")
        batch_op.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_aws_connections_workspace_id",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_aws_connections_workspace_id",
            ["workspace_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_aws_connection_workspace_account",
            ["workspace_id", "account_id"],
        )

    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_aws_scans_workspace_id",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_aws_scans_workspace_id",
            ["workspace_id"],
            unique=False,
        )

    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_chat_sessions_workspace_id",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_chat_sessions_workspace_id",
            ["workspace_id"],
            unique=False,
        )


def downgrade() -> None:
    # Downgrading assumes a user does not have the same AWS account duplicated
    # across multiple workspaces. Production systems should normally restore a
    # backup instead of downgrading a tenant-boundary migration.
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.drop_index("ix_chat_sessions_workspace_id")
        batch_op.drop_constraint("fk_chat_sessions_workspace_id", type_="foreignkey")
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("aws_scans") as batch_op:
        batch_op.drop_index("ix_aws_scans_workspace_id")
        batch_op.drop_constraint("fk_aws_scans_workspace_id", type_="foreignkey")
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("aws_connections") as batch_op:
        batch_op.drop_constraint("uq_aws_connection_workspace_account", type_="unique")
        batch_op.drop_index("ix_aws_connections_workspace_id")
        batch_op.drop_constraint("fk_aws_connections_workspace_id", type_="foreignkey")
        batch_op.drop_column("workspace_id")
        batch_op.create_unique_constraint(
            "uq_aws_connection_user_account",
            ["user_id", "account_id"],
        )

    op.drop_index("ix_workspace_members_status", table_name="workspace_members")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")

    op.drop_index("ix_workspaces_status", table_name="workspaces")
    op.drop_index("ix_workspaces_created_by_user_id", table_name="workspaces")
    op.drop_index("ix_workspaces_name", table_name="workspaces")
    op.drop_table("workspaces")
