# from __future__ import annotations

# from datetime import datetime, timezone

# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.api.schemas.workspace import (
#     WorkspaceCreateRequest,
#     WorkspaceRenameRequest,
#     WorkspaceResponse,
# )
# from app.auth.dependencies import get_current_user
# from app.db.models.user import User
# from app.db.session import get_db
# from app.repositories.workspace_repository import WorkspaceRepository


# router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])
# repository = WorkspaceRepository()


# def _response(workspace, member) -> WorkspaceResponse:
#     return WorkspaceResponse(
#         id=workspace.id,
#         name=workspace.name,
#         role=member.role,
#         status=workspace.status,
#         created_by_user_id=workspace.created_by_user_id,
#         created_at=workspace.created_at,
#         updated_at=workspace.updated_at,
#     )


# @router.get("", response_model=list[WorkspaceResponse])
# async def list_workspaces(
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     rows = await repository.list_for_user(db, user_id=current_user.id)
#     return [_response(workspace, member) for workspace, member in rows]


# @router.post("", response_model=WorkspaceResponse, status_code=201)
# async def create_workspace(
#     request: WorkspaceCreateRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     name = request.name.strip()
#     if await repository.name_exists_for_creator(
#         db,
#         user_id=current_user.id,
#         name=name,
#     ):
#         raise HTTPException(
#             status_code=409,
#             detail="A workspace with this client name already exists.",
#         )

#     workspace, member = await repository.create(
#         db,
#         user_id=current_user.id,
#         name=name,
#     )
#     await db.commit()
#     await db.refresh(workspace)
#     await db.refresh(member)
#     return _response(workspace, member)


# @router.get("/{workspace_id}", response_model=WorkspaceResponse)
# async def get_workspace(
#     workspace_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     found = await repository.find_for_user(
#         db,
#         workspace_id=workspace_id,
#         user_id=current_user.id,
#     )
#     if found is None:
#         raise HTTPException(status_code=404, detail="Workspace not found.")
#     workspace, member = found
#     return _response(workspace, member)


# @router.patch("/{workspace_id}", response_model=WorkspaceResponse)
# async def rename_workspace(
#     workspace_id: int,
#     request: WorkspaceRenameRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     found = await repository.find_for_user(
#         db,
#         workspace_id=workspace_id,
#         user_id=current_user.id,
#     )
#     if found is None:
#         raise HTTPException(status_code=404, detail="Workspace not found.")

#     workspace, member = found
#     if member.role != "OWNER":
#         raise HTTPException(
#             status_code=403,
#             detail="Only the workspace owner can rename this workspace.",
#         )

#     name = request.name.strip()
#     if await repository.name_exists_for_creator(
#         db,
#         user_id=current_user.id,
#         name=name,
#         exclude_workspace_id=workspace.id,
#     ):
#         raise HTTPException(
#             status_code=409,
#             detail="A workspace with this client name already exists.",
#         )

#     workspace.name = name
#     workspace.updated_at = datetime.now(timezone.utc)
#     await db.commit()
#     await db.refresh(workspace)
#     return _response(workspace, member)



from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceRenameRequest,
    WorkspaceResponse,
)
from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.providers.aws.credential_provider import aws_credential_provider
from app.providers.aws.session_store import aws_credential_sessions
from app.repositories.aws_connection_repository import AWSConnectionRepository
from app.repositories.workspace_repository import WorkspaceRepository


router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])
repository = WorkspaceRepository()
aws_connection_repository = AWSConnectionRepository()


def _response(workspace, member) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        role=member.role,
        status=workspace.status,
        created_by_user_id=workspace.created_by_user_id,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await repository.list_for_user(db, user_id=current_user.id)
    return [_response(workspace, member) for workspace, member in rows]


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    request: WorkspaceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = request.name.strip()
    if await repository.name_exists_for_creator(
        db,
        user_id=current_user.id,
        name=name,
    ):
        raise HTTPException(
            status_code=409,
            detail="A workspace with this client name already exists.",
        )

    workspace, member = await repository.create(
        db,
        user_id=current_user.id,
        name=name,
    )
    await db.commit()
    await db.refresh(workspace)
    await db.refresh(member)
    return _response(workspace, member)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    found = await repository.find_for_user(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    if found is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    workspace, member = found
    return _response(workspace, member)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace(
    workspace_id: int,
    request: WorkspaceRenameRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    found = await repository.find_for_user(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    if found is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    workspace, member = found
    if member.role != "OWNER":
        raise HTTPException(
            status_code=403,
            detail="Only the workspace owner can rename this workspace.",
        )

    name = request.name.strip()
    if await repository.name_exists_for_creator(
        db,
        user_id=current_user.id,
        name=name,
        exclude_workspace_id=workspace.id,
    ):
        raise HTTPException(
            status_code=409,
            detail="A workspace with this client name already exists.",
        )

    workspace.name = name
    workspace.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(workspace)
    return _response(workspace, member)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    found = await repository.find_for_user(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    if found is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    workspace, member = found
    if member.role != "OWNER":
        raise HTTPException(
            status_code=403,
            detail="Only the workspace owner can delete this workspace.",
        )

    # Remove any in-memory credentials before deleting the connection rows.
    # This prevents deleted client credentials from lingering until process restart.
    connections = await aws_connection_repository.find_all_by_workspace(
        db,
        workspace_id=workspace.id,
    )
    for connection in connections:
        await aws_credential_provider.clear_cache(
            aws_connection_id=connection.id,
        )
        await aws_credential_sessions.remove(
            user_id=current_user.id,
            aws_connection_id=connection.id,
        )

    await repository.delete(db, workspace=workspace)
    await db.commit()
    return Response(status_code=204)
