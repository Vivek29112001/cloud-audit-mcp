from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from jose import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(
    password: str,
) -> str:

    return password_hash.hash(
        password
    )


def verify_password(
    plain_password: str,
    password_hash_value: str,
) -> bool:

    return password_hash.verify(
        plain_password,
        password_hash_value,
    )


def create_access_token(
    *,
    user_id: int,
    username: str,
) -> str:

    expires_at = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            minutes=(
                settings
                .jwt_access_token_expire_minutes
            )
        )
    )

    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=(
            settings.jwt_algorithm
        ),
    )