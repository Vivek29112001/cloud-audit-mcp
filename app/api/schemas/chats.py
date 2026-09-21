from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.ai.query_router import (
    AWSQueryRouter,
)

from app.api.schemas.chat import (
    ChatQueryRequest,
    CreateChatRequest,
)

from app.auth.dependencies import (
    get_current_user,
)

from app.db.models.user import User
from app.db.session import get_db

from app.providers.aws.session_store import (
    aws_credential_sessions,
)

from app.repositories.chat_repository import (
    ChatRepository,
)

from app.services.aws_scan_context_service import (
    AWSScanContextService,
)

from app.services.chat_service import (
    ChatService,
)


router = APIRouter(
    prefix="/api/chats",
    tags=["Chats"],
)


chat_service = ChatService()

chat_repository = ChatRepository()

query_router = AWSQueryRouter()

scan_context_service = (
    AWSScanContextService()
)