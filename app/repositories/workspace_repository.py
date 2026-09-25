# from __future__ import annotations

# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.models.workspace import Workspace, WorkspaceMember


# class WorkspaceRepository:
#     async def create(
#         self,
#         db: AsyncSession,
#         *,
#         user_id: int,
#         name: str,
#     ) -> tuple[Workspace, WorkspaceMember]:
#         workspace = Workspace(
#             name=name.strip(),
#             created_by_user_id=user_id,
#             status="ACTIVE",
#         )
#         db.add(workspace)
#         await db.flush()

#         member = WorkspaceMember(
#             workspace_id=workspace.id,
#             user_id=user_id,
#             role="OWNER",
#             status="ACTIVE",
#         )
#         db.add(member)
#         await db.flush()
#         return workspace, member

#     async def find_membership(
#         self,
#         db: AsyncSession,
#         *,
#         workspace_id: int,
#         user_id: int,
#     ) -> WorkspaceMember | None:
#         result = await db.execute(
#             select(WorkspaceMember).where(
#                 WorkspaceMember.workspace_id == workspace_id,
#                 WorkspaceMember.user_id == user_id,
#                 WorkspaceMember.status == "ACTIVE",
#             )
#         )
#         return result.scalar_one_or_none()

#     async def find_for_user(
#         self,
#         db: AsyncSession,
#         *,
#         workspace_id: int,
#         user_id: int,
#     ) -> tuple[Workspace, WorkspaceMember] | None:
#         result = await db.execute(
#             select(Workspace, WorkspaceMember)
#             .join(
#                 WorkspaceMember,
#                 WorkspaceMember.workspace_id == Workspace.id,
#             )
#             .where(
#                 Workspace.id == workspace_id,
#                 Workspace.status == "ACTIVE",
#                 WorkspaceMember.user_id == user_id,
#                 WorkspaceMember.status == "ACTIVE",
#             )
#         )
#         row = result.first()
#         if row is None:
#             return None
#         return row[0], row[1]

#     async def list_for_user(
#         self,
#         db: AsyncSession,
#         *,
#         user_id: int,
#     ) -> list[tuple[Workspace, WorkspaceMember]]:
#         result = await db.execute(
#             select(Workspace, WorkspaceMember)
#             .join(
#                 WorkspaceMember,
#                 WorkspaceMember.workspace_id == Workspace.id,
#             )
#             .where(
#                 WorkspaceMember.user_id == user_id,
#                 WorkspaceMember.status == "ACTIVE",
#                 Workspace.status == "ACTIVE",
#             )
#             .order_by(Workspace.updated_at.desc(), Workspace.name.asc())
#         )
#         return [(row[0], row[1]) for row in result.all()]

#     async def name_exists_for_creator(
#         self,
#         db: AsyncSession,
#         *,
#         user_id: int,
#         name: str,
#         exclude_workspace_id: int | None = None,
#     ) -> bool:
#         query = select(Workspace.id).where(
#             Workspace.created_by_user_id == user_id,
#             Workspace.name == name.strip(),
#             Workspace.status == "ACTIVE",
#         )
#         if exclude_workspace_id is not None:
#             query = query.where(Workspace.id != exclude_workspace_id)
#         result = await db.execute(query.limit(1))
#         return result.scalar_one_or_none() is not None



from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workspace import Workspace, WorkspaceMember


class WorkspaceRepository:
    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        name: str,
    ) -> tuple[Workspace, WorkspaceMember]:
        workspace = Workspace(
            name=name.strip(),
            created_by_user_id=user_id,
            status="ACTIVE",
        )
        db.add(workspace)
        await db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role="OWNER",
            status="ACTIVE",
        )
        db.add(member)
        await db.flush()
        return workspace, member

    async def find_membership(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user_id: int,
    ) -> WorkspaceMember | None:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "ACTIVE",
            )
        )
        return result.scalar_one_or_none()

    async def find_for_user(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user_id: int,
    ) -> tuple[Workspace, WorkspaceMember] | None:
        result = await db.execute(
            select(Workspace, WorkspaceMember)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(
                Workspace.id == workspace_id,
                Workspace.status == "ACTIVE",
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "ACTIVE",
            )
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[tuple[Workspace, WorkspaceMember]]:
        result = await db.execute(
            select(Workspace, WorkspaceMember)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "ACTIVE",
                Workspace.status == "ACTIVE",
            )
            .order_by(Workspace.updated_at.desc(), Workspace.name.asc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def name_exists_for_creator(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        name: str,
        exclude_workspace_id: int | None = None,
    ) -> bool:
        query = select(Workspace.id).where(
            Workspace.created_by_user_id == user_id,
            Workspace.name == name.strip(),
            Workspace.status == "ACTIVE",
        )
        if exclude_workspace_id is not None:
            query = query.where(Workspace.id != exclude_workspace_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none() is not None
    async def delete(
        self,
        db: AsyncSession,
        *,
        workspace: Workspace,
    ) -> None:
        """Hard-delete a workspace. Database FKs cascade its tenant data."""
        await db.delete(workspace)
        await db.flush()



