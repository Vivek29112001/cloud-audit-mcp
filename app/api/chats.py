from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.intent_models import AWSQueryIntent
from app.ai.query_router import AWSQueryRouter
from app.api.schemas.chat import (
    ChatQueryRequest,
    ChatSessionResponse,
    CreateChatRequest,
    RenameChatRequest,
)
from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.providers.aws.credential_provider import aws_credential_provider
from app.repositories.chat_repository import ChatRepository
from app.repositories.query_execution_repository import QueryExecutionRepository
from app.services.aws_scan_context_service import AWSScanContextService
from app.services.chat_service import ChatService
from app.services.chat_title_service import ChatTitleService
from app.services.conversation_context_service import ConversationContextService
from app.workspace_dependencies import WorkspaceContext, get_current_workspace


router = APIRouter(prefix="/api/chats", tags=["Chats"])
chat_service = ChatService()
chat_repository = ChatRepository()
scan_context_service = AWSScanContextService()
conversation_context_service = ConversationContextService()
chat_title_service = ChatTitleService()
query_execution_repository = QueryExecutionRepository()
query_router = AWSQueryRouter()


@router.post("", response_model=ChatSessionResponse)
async def create_chat(
    request: CreateChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    chat = await chat_service.create_chat(
        db,
        workspace_id=workspace.id,
        user=current_user,
        scan_id=request.scan_id,
        title=request.title,
        context=request.context,
    )
    return ChatSessionResponse(
        id=chat.id,
        workspace_id=chat.workspace_id,
        scan_id=chat.scan_id,
        aws_connection_id=chat.aws_connection_id,
        title=chat.title,
        context=chat.context_json or {},
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("")
async def list_chats(
    scan_id: str | None = None,
    aws_connection_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    rows = await chat_repository.list_sessions(
        db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        scan_id=scan_id,
        aws_connection_id=aws_connection_id,
    )
    return [
        {
            "id": chat.id,
            "workspace_id": chat.workspace_id,
            "scan_id": chat.scan_id,
            "aws_connection_id": chat.aws_connection_id,
            "title": chat.title,
            "context": chat.context_json or {},
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
        }
        for chat in rows
    ]


@router.get("/{chat_id}")
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found in this workspace.")

    messages = await chat_repository.list_messages(db, chat_session_id=chat.id)
    return {
        "id": chat.id,
        "workspace_id": chat.workspace_id,
        "scan_id": chat.scan_id,
        "aws_connection_id": chat.aws_connection_id,
        "title": chat.title,
        "context": chat.context_json or {},
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "intent": message.intent_json,
                "evidence": message.evidence_json,
                "response_time_ms": message.response_time_ms,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }


@router.patch("/{chat_id}")
async def rename_chat(
    chat_id: int,
    request: RenameChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found in this workspace.")

    await chat_repository.update_title(db, chat=chat, title=request.title.strip())
    chat.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(chat)
    return {
        "id": chat.id,
        "workspace_id": chat.workspace_id,
        "title": chat.title,
        "updated_at": chat.updated_at,
    }


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found in this workspace.")
    await chat_repository.delete_session(db, chat=chat)
    await db.commit()
    return None


@router.post("/{chat_id}/query")
async def query_chat(
    chat_id: int,
    request: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found in this workspace.")

    scan = await scan_context_service.load_scan_context(
        db,
        user=current_user,
        workspace_id=workspace.id,
        scan_id=chat.scan_id,
    )
    conversation = (
        await conversation_context_service.build(
            db,
            chat_session_id=chat.id,
        )
    ).as_text()
    existing = await chat_repository.get_recent_messages(
        db,
        chat_session_id=chat.id,
        limit=1,
    )
    first = not existing

    await chat_repository.add_message(
        db,
        chat_session_id=chat.id,
        role="user",
        content=request.question,
    )
    if first and chat.title == "New AWS Chat":
        chat.title = chat_title_service.generate(request.question)

    async def load_credentials():
        return await aws_credential_provider.get_credentials(
            db,
            user_id=current_user.id,
            workspace_id=workspace.id,
            aws_connection_id=chat.aws_connection_id,
        )

    # Workspace identity is deliberately injected as immutable query context.
    # The model receives data only from this workspace's linked scan/connection.
    selected_context = {
        **(chat.context_json or {}),
        "workspace_id": workspace.id,
        "workspace_name": workspace.workspace.name,
    }
    result = await query_router.execute(
        question=request.question,
        scan_result=scan,
        credential_loader=load_credentials,
        conversation_context=conversation,
        selected_context=selected_context,
    )

    answer = result.get("answer", "No answer was generated.")
    evidence = {
        "source": result.get("source"),
        "workspace_id": workspace.id,
        "scan_id": result.get("scan_id") or chat.scan_id,
        "selected_context": result.get("selected_context") or selected_context,
        "data": result.get("data"),
        "warnings": result.get("warnings") or [],
        "status": result.get("status"),
    }
    await chat_repository.add_message(
        db,
        chat_session_id=chat.id,
        role="assistant",
        content=answer,
        intent_json=result.get("intent"),
        evidence_json=evidence,
        response_time_ms=result.get("response_time_ms"),
    )

    intent_data = result.get("intent") or {}
    params = {}
    if intent_data:
        try:
            params = AWSQueryIntent(**intent_data).get_params()
        except Exception:
            params = {}

    selected_region = (chat.context_json or {}).get("region")
    execution_regions: list[str] = []
    data = result.get("data") or {}
    if result.get("source", " ").startswith("LIVE_AWS_MCP") and isinstance(data, dict):
        raw = data.get("regions") or []
        execution_regions = raw if isinstance(raw, list) else []
    elif selected_region:
        execution_regions = [selected_region]

    await query_execution_repository.create(
        db,
        chat_session_id=chat.id,
        service=(intent_data.get("service") or "snapshot"),
        operation=(intent_data.get("operation") or "SnapshotLookup"),
        regions=execution_regions,
        params=params,
        status=result.get("status", "UNKNOWN"),
        timings=result.get("timings", {}),
        warnings=result.get("warnings", []),
    )
    chat.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        **result,
        "workspace_id": workspace.id,
        "workspace_name": workspace.workspace.name,
        "chat_id": chat.id,
        "chat_title": chat.title,
        "chat_context": chat.context_json or {},
    }
