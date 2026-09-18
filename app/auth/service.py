from fastapi import HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.repositories.user_repository import (
    UserRepository,
)


class AuthService:

    def __init__(self) -> None:
        self._users = UserRepository()

    async def register(
        self,
        db: AsyncSession,
        request: RegisterRequest,
    ) -> UserResponse:

        if await self._users.find_by_username(
            db,
            request.username,
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Username is already "
                    "registered."
                ),
            )

        if await self._users.find_by_email(
            db,
            request.email,
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Email is already "
                    "registered."
                ),
            )

        user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(
                request.password
            ),
        )

        user = await self._users.save(
            db,
            user,
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
        )

    async def login(
        self,
        db: AsyncSession,
        request: LoginRequest,
    ) -> LoginResponse:

        user = (
            await self._users.find_by_login(
                db,
                request.username,
            )
        )

        if (
            user is None
            or not verify_password(
                request.password,
                user.password_hash,
            )
        ):
            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid username/email "
                    "or password."
                ),
            )

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User is inactive.",
            )

        token = create_access_token(
            user_id=user.id,
            username=user.username,
        )

        return LoginResponse(
            access_token=token,
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
            ),
        )