from __future__ import annotations

from fastapi import (
    Depends,
    HTTPException,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import (
    JWTError,
    jwt,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_db


bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: (
        HTTPAuthorizationCredentials
    ) = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[
                settings.jwt_algorithm
            ],
        )

        user_id = int(
            payload["sub"]
        )

    except (
        JWTError,
        KeyError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=401,
            detail="Invalid access token.",
        ) from exc

    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User does not exist.",
        )

    return user