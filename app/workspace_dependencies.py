from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.models.workspace import Workspace, WorkspaceMember
from app.db.session import get_db
from app.repositories.workspace_repository import WorkspaceRepository


@dataclass(frozen=True)
class WorkspaceContext:
    workspace: Workspace
    membership: WorkspaceMember

    @property
    def id(self) -> int:
        return self.workspace.id

    @property
    def role(self) -> str:
        return self.membership.role


_workspace_repository = WorkspaceRepository()


async def get_current_workspace(
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceContext:
    if not x_workspace_id:
        raise HTTPException(
            status_code=400,
            detail="No workspace selected. Send X-Workspace-ID with this request.",
        )

    try:
        workspace_id = int(x_workspace_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="X-Workspace-ID must be a valid workspace ID.",
        ) from exc

    found = await _workspace_repository.find_for_user(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    if found is None:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to the selected workspace.",
        )

    workspace, membership = found
    return WorkspaceContext(
        workspace=workspace,
        membership=membership,
    )
