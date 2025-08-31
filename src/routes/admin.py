from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.repository import users as repository_users
from src.services.auth import auth_service
from src.services.email import email_service
from src.schemas import AdminUserDb, AdminUpdateProfile, AdminUpdateAdminStatus

router = APIRouter(prefix="/admin", tags=["admin"])

# ===== GET USERS =====
@router.get("/users", response_model=List[AdminUserDb])
async def get_users(
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
) -> List[AdminUserDb]:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )

    if limit > 1000:
        limit = 1000

    users = await repository_users.get_users(
        db=db,
        skip=skip,
        limit=limit,
    )
    return users


# ===== GET USER BY ID =====
@router.get("/user/", response_model=AdminUserDb)
async def get_user_by_id(
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
) -> AdminUserDb:

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    if not any([user_id, username, email]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Musisz podać przynajmniej jedno kryterium wyszukiwania: user_id, username lub email"
        )
    user = None
    if user_id is not None:
        user = await repository_users.get_user_by_id(user_id, db)
    elif username is not None:
        user = await repository_users.get_user_by_username(username, db)
    elif email is not None:
        user = await repository_users.get_user_by_email(email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono użytkownika"
        )
    return user


# ===== UPDATE USER PROFILE =====
@router.patch("/users/{user_id}/profile", response_model=AdminUserDb)
async def update_user_profile(
        user_id: int,
        profile_data: AdminUpdateProfile,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
) -> AdminUserDb:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    user = await repository_users.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono użytkownika")

    if profile_data.username and profile_data.username != user.username:
        existing_user = await repository_users.get_user_by_username(profile_data.username, db)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nazwa użytkownika jest już zajęta")

    if profile_data.email and profile_data.email != user.email:
        existing_user = await repository_users.get_user_by_email(profile_data.email, db)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adres e-mail jest już zajęty")

    updated_user = await repository_users.admin_update_profile(
        user=user,
        username=profile_data.username,
        email=profile_data.email,
        full_name=profile_data.full_name,
        is_active=profile_data.is_active,
        db=db
    )

    return updated_user


# ===== CONFIRM USER EMAIL =====
@router.patch("/users/{user_id}/confirm-email", response_model=AdminUserDb)
async def confirm_user_email(
        user_id: int,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
) -> AdminUserDb:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    user = await repository_users.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono użytkownika")

    updated_user = await repository_users.admin_confirm_email(user, db)
    return updated_user


# ===== REQUEST PASSWORD RESET =====
@router.post("/users/{user_id}/request-password-reset")
async def request_password_reset_for_user(
        user_id: int,
        background_tasks: BackgroundTasks,
        request: Request,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    user = await repository_users.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono użytkownika")

    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Użytkownik nie posiada adresu e-mail")

    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Adres e-mail użytkownika nie jest potwierdzony")

    reset_token = auth_service.create_token(
        subject=user.email,
        scope="reset_password",
        expires_delta=3600
    )

    template_body = {
        "host": str(request.base_url),
        "username": user.username,
        "token": reset_token,
        "reset_link": f"{str(request.base_url)}reset_password?token={reset_token}"
    }
    background_tasks.add_task(
        email_service.send_email,
        email=user.email,
        subject="Reset hasła - zlecenie administratora",
        template_name="reset_password_email.html",
        template_body=template_body
    )

    return {"detail": "Wysłano e-mail do resetu hasła"}


# ===== UPDATE ADMIN STATUS =====
@router.patch("/users/{user_id}/admin-status", response_model=AdminUserDb)
async def update_user_admin_status(
        user_id: int,
        admin_status: AdminUpdateAdminStatus,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
) -> AdminUserDb:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    user = await repository_users.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono użytkownika")

    if user.id == current_user.id and not admin_status.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nie można odebrać sobie uprawnień administratora")

    if user.is_admin and not admin_status.is_admin and user.is_active:
        active_admin_count = await repository_users.count_active_admins(db)
        if active_admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Nie można odebrać uprawnień ostatniemu aktywnemu administratorowi")

    updated_user = await repository_users.admin_update_admin_status(
        user=user,
        is_admin=admin_status.is_admin,
        db=db
    )

    return updated_user


# ===== DELETE USER =====
@router.delete("/users/{user_id}")
async def delete_user(
        user_id: int,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    user = await repository_users.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono użytkownika")

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nie można usunąć własnego konta")

    await repository_users.delete_user(user, db)
    return {"detail": "Konto użytkownika zostało usunięte"}
