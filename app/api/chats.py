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
from app.providers.aws.session_store import (
    aws_credential_sessions,
)
from app.repositories.chat_repository import ChatRepository
from app.repositories.query_execution_repository import (
    QueryExecutionRepository,
)
from app.services.aws_scan_context_service import (
    AWSScanContextService,
)
from app.services.chat_service import ChatService
from app.services.chat_title_service import ChatTitleService
from app.services.conversation_context_service import (
    ConversationContextService,
)


router = APIRouter(
    prefix="/api/chats",
    tags=["Chats"],
)

chat_service = ChatService()
chat_repository = ChatRepository()
scan_context_service = AWSScanContextService()
conversation_context_service = ConversationContextService()
chat_title_service = ChatTitleService()
query_execution_repository = QueryExecutionRepository()
query_router = AWSQueryRouter()


@router.post(
    "",
    response_model=ChatSessionResponse,
)
async def create_chat(
    request: CreateChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    chat = await chat_service.create_chat(
        db,
        user=current_user,
        scan_id=request.scan_id,
        title=request.title,
    )

    return ChatSessionResponse(
        id=chat.id,
        scan_id=chat.scan_id,
        aws_connection_id=chat.aws_connection_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("")
async def list_chats(
    scan_id: str | None = None,
    aws_connection_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    chats = await chat_repository.list_sessions(
        db,
        user_id=current_user.id,
        scan_id=scan_id,
        aws_connection_id=aws_connection_id,
    )

    return [
        {
            "id": chat.id,
            "scan_id": chat.scan_id,
            "aws_connection_id":
                chat.aws_connection_id,
            "title": chat.title,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
        }
        for chat in chats
    ]


@router.get("/{chat_id}")
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        user_id=current_user.id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    messages = await chat_repository.list_messages(
        db,
        chat_session_id=chat.id,
    )

    return {
        "id": chat.id,
        "scan_id": chat.scan_id,
        "title": chat.title,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "response_time_ms":
                    message.response_time_ms,
                "created_at":
                    message.created_at,
            }
            for message in messages
        ],
    }


@router.patch("/{chat_id}")
async def rename_chat(
    chat_id: int,
    request: RenameChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        user_id=current_user.id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    await chat_repository.update_title(
        db,
        chat=chat,
        title=request.title.strip(),
    )

    chat.updated_at = datetime.now(
        timezone.utc
    )

    await db.commit()
    await db.refresh(chat)

    return {
        "id": chat.id,
        "title": chat.title,
        "updated_at": chat.updated_at,
    }


@router.delete(
    "/{chat_id}",
    status_code=204,
)
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        user_id=current_user.id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    await chat_repository.delete_session(
        db,
        chat=chat,
    )

    await db.commit()
    return None


@router.post("/{chat_id}/query")
async def query_chat(
    chat_id: int,
    request: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    chat = await chat_repository.find_session(
        db,
        chat_id=chat_id,
        user_id=current_user.id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    credentials = await aws_credential_sessions.get(
        user_id=current_user.id
    )

    if credentials is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "AWS session expired. "
                "Please reconnect AWS."
            ),
        )

    scan_context = (
        await scan_context_service.load_scan_context(
            db,
            user=current_user,
            scan_id=chat.scan_id,
        )
    )

    conversation = (
        await conversation_context_service.build(
            db,
            chat_session_id=chat.id,
        )
    )
    conversation_text = conversation.as_text()

    existing_messages = (
        await chat_repository.get_recent_messages(
            db,
            chat_session_id=chat.id,
            limit=1,
        )
    )
    is_first_message = (
        len(existing_messages) == 0
    )

    await chat_repository.add_message(
        db,
        chat_session_id=chat.id,
        role="user",
        content=request.question,
    )

    if (
        is_first_message
        and chat.title == "New AWS Chat"
    ):
        chat.title = chat_title_service.generate(
            request.question
        )

    result = await query_router.execute(
        question=request.question,
        credentials=credentials,
        scan_result=scan_context,
        conversation_context=conversation_text,
    )

    answer = result.get(
        "answer",
        "No answer was generated.",
    )

    await chat_repository.add_message(
        db,
        chat_session_id=chat.id,
        role="assistant",
        content=answer,
        intent_json=result.get("intent"),
        evidence_json=result.get("data"),
        response_time_ms=result.get(
            "response_time_ms"
        ),
    )

    intent_data = result.get(
        "intent",
        {},
    )
    params: dict = {}

    if intent_data:
        try:
            params = AWSQueryIntent(
                **intent_data
            ).get_params()
        except Exception:
            params = {}

    data = result.get(
        "data",
        {},
    )

    await query_execution_repository.create(
        db,
        chat_session_id=chat.id,
        service=intent_data.get(
            "service",
            "unknown",
        ),
        operation=intent_data.get(
            "operation",
            "unknown",
        ),
        regions=data.get(
            "regions",
            [],
        ),
        params=params,
        status=result.get(
            "status",
            "UNKNOWN",
        ),
        timings=result.get(
            "timings",
            {},
        ),
        warnings=result.get(
            "warnings",
            [],
        ),
    )

    chat.updated_at = datetime.now(
        timezone.utc
    )

    await db.commit()

    return {
        **result,
        "chat_id": chat.id,
        "chat_title": chat.title,
    }
