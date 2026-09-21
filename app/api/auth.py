from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.auth.dependencies import (
    get_current_user,
)
from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from app.auth.service import AuthService
from app.db.models.user import User
from app.db.session import get_db


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

service = AuthService()


@router.post(
    "/register",
    response_model=UserResponse,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    return await service.register(
        db,
        request,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await service.login(
        db,
        request,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
    )
    
    
