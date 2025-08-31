from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.repository import users as repository_users
from src.services.auth import auth_service
from src.schemas import UserDb, ChangePassword, UpdateProfile, ConfirmPassword

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/", response_model=UserDb)
async def read_users_me(
        current_user: User = Depends(auth_service.get_current_user)
) -> UserDb:
    """
    Zwraca dane aktualnie zalogowanego użytkownika.
    Wymaga ważnego access_token.
    """
    return current_user


@router.patch("/me/", response_model=UserDb)
async def update_me(
        data: UpdateProfile = Body(...),
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
) -> UserDb:
    """
    Zmień dane profilowe (full_name i/lub email).
    """
    user = await repository_users.update_profile(
        current_user,
        full_name=data.full_name,
        email=data.email,
        db=db
    )
    return user


@router.patch("/me/password/")
async def change_password(
        data: ChangePassword = Body(...),
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Zmień hasło użytkownika.
    """
    if not await auth_service.verify_password(
            data.old_password,
            current_user.password
    ):
        raise HTTPException(
            status_code=400,
            detail="Nieprawidłowe stare hasło."
        )
    # walidacja nowego hasła
    auth_service.validate_password(data.new_password)
    new_hash = auth_service.get_password_hash(data.new_password)
    await repository_users.update_password(current_user, new_hash, db)
    return {"detail": "Hasło zostało zmienione."}


@router.delete("/me/")
async def delete_account(
        data: ConfirmPassword = Body(...),
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Usuń konto (potwierdzenie hasłem).
    """
    if not await auth_service.verify_password(data.password, current_user.password):
        raise HTTPException(status_code=400, detail="Nieprawidłowe hasło.")
    await repository_users.delete_user(current_user, db)
    return {"detail": "Konto zostało usunięte."}
