from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schemas import UserModel


async def get_user_by_username(
        username: str,
        db: AsyncSession
) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: int, db: AsyncSession) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None
) -> List[User]:
    query = select(User)
    if user_id is not None:
        query = query.where(User.id == user_id)
    else:
        if username:
            query = query.where(User.username.ilike(f"%{username}%"))
        if email:
            query = query.where(User.email.ilike(f"%{email}%"))

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def count_active_admins(db: AsyncSession) -> int:
    stmt = select(User).where(User.is_admin.is_(True), User.is_active.is_(True))
    result = await db.execute(stmt)
    return len(result.scalars().all())


async def create_user(body: UserModel, db: AsyncSession) -> User:
    user = User(
        username=body.username,
        password=body.password,
        email=body.email,
        full_name=body.full_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_token(user: User, token: Optional[str], db: AsyncSession) -> None:
    user.refresh_token = token
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession) -> None:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.confirmed = True
        await db.commit()


async def update_profile(
        user: User,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        db: Optional[AsyncSession] = None
) -> User:
    if full_name is not None:
        user.full_name = full_name
    if email is not None:
        user.email = email
    if db:
        await db.commit()
        await db.refresh(user)
    return user


async def update_password(user: User, hashed_password: str, db: AsyncSession) -> None:
    user.password = hashed_password
    await db.commit()


async def admin_update_profile(
        user: User,
        username: Optional[str] = None,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        db: Optional[AsyncSession] = None
) -> User:
    if username is not None:
        user.username = username
    if email is not None:
        user.email = email
    if full_name is not None:
        user.full_name = full_name
    if is_active is not None:
        user.is_active = is_active
    if db:
        await db.commit()
        await db.refresh(user)
    return user


async def admin_confirm_email(user: User, db: AsyncSession) -> User:
    user.confirmed = True
    await db.commit()
    await db.refresh(user)
    return user


async def admin_update_admin_status(
        user: User,
        is_admin: bool,
        db: AsyncSession
) -> User:
    user.is_admin = is_admin
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(user: User, db: AsyncSession) -> None:
    await db.delete(user)
    await db.commit()