from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.db.models.user import User


class UserRepository:

    async def find_by_username(
        self,
        db: AsyncSession,
        username: str,
    ) -> User | None:

        result = await db.execute(
            select(User).where(
                User.username == username
            )
        )

        return result.scalar_one_or_none()

    async def find_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> User | None:

        result = await db.execute(
            select(User).where(
                User.email == email
            )
        )

        return result.scalar_one_or_none()

    async def find_by_login(
        self,
        db: AsyncSession,
        login: str,
    ) -> User | None:

        result = await db.execute(
            select(User).where(
                or_(
                    User.username == login,
                    User.email == login,
                )
            )
        )

        return result.scalar_one_or_none()

    async def save(
        self,
        db: AsyncSession,
        user: User,
    ) -> User:

        db.add(user)

        await db.commit()
        await db.refresh(user)

        return user