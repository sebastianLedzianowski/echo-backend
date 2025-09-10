from fastapi import (
    APIRouter,
    Depends,
    status,
    BackgroundTasks,
    Request,
    HTTPException
)
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.email import email_service, logger
from src.database.db import get_db
from src.schemas import (
    UserModel,
    UserResponse,
    TokenModel,
    RequestEmail,
    ResetPasswordRequest
)
from src.repository import users as repository_users
from src.services.auth import auth_service

router = APIRouter(prefix='/auth', tags=["auth"])
security = HTTPBearer()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: UserModel,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse | dict:

    if await repository_users.get_user_by_username(body.username, db):
        raise HTTPException(status_code=409, detail="Nazwa użytkownika jest już zajęta.")

    if body.email and await repository_users.get_user_by_email(body.email, db):
        raise HTTPException(status_code=409, detail="Podany e-mail jest już zajęty.")

    auth_service.validate_password(body.password)
    body.password = auth_service.get_password_hash(body.password)
    new_user = await repository_users.create_user(body, db)

    if new_user.email:
        token = auth_service.create_token(
            subject=new_user.email,
            scope="email_confirm",
            expires_delta=3600 * 24
        )
        template_body = {
            "host": str(request.base_url),
            "username": new_user.username,
            "token": token
        }
        background_tasks.add_task(
            email_service.send_email,
            email=new_user.email,
            subject="Potwierdź swój e-mail",
            template_name="email_template.html",
            template_body=template_body
        )

    return {
        "user": new_user,
        "detail": "Użytkownik utworzony. Jeżeli podałeś e-mail, sprawdź skrzynkę."
    }


@router.post("/login", response_model=TokenModel)
async def login(
    body: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse | dict:

    db_user = await repository_users.get_user_by_username(body.username, db)
    if not db_user:
        logger.info("bledny username %s", body.username)
        return JSONResponse(status_code=401, content={"detail": "Błędny Username."})
    if not await auth_service.verify_password(body.password, db_user.password):
        logger.info("bledny password %s", body.password)
        return JSONResponse(status_code=401, content={"detail": "Złe hasło."})

    access_token = auth_service.create_token(subject=db_user.username, scope="access_token")
    refresh_token = auth_service.create_token(subject=db_user.username, scope="refresh_token")
    await repository_users.update_token(db_user, refresh_token, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/refresh_token", response_model=TokenModel)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    try:
        username = await auth_service.decode_token(token, expected_scope="refresh_token")
    except Exception:
        raise HTTPException(status_code=401, detail="Nieprawidłowy refresh token.")
    user = await repository_users.get_user_by_username(username, db)
    if not user or user.refresh_token != token:
        if user:
            await repository_users.update_token(user, None, db)
        raise HTTPException(status_code=401, detail="Nieprawidłowy refresh token.")

    access_token = auth_service.create_token(subject=username, scope="access_token")
    refresh_token = auth_service.create_token(subject=username, scope="refresh_token", expires_delta=3600 * 24 * 7)
    await repository_users.update_token(user, refresh_token, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get('/confirmed_email/{token}')
async def confirmed_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        email = await auth_service.decode_token(token, expected_scope="email_confirm")
    except Exception:
        raise HTTPException(status_code=400, detail="Błąd weryfikacji.")

    user = await repository_users.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=400, detail="Błąd weryfikacji.")
    if user.confirmed:
        return {"message": "Twój e-mail jest już potwierdzony."}
    await repository_users.confirmed_email(email, db)
    return {"message": "E-mail potwierdzony."}


@router.post('/request_email')
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user = await repository_users.get_user_by_email(body.email, db)
    if not user:
        logger.info(f"Nie znaleziono użytkownika z adresem {body.email}")
        return {"message": "Nie znaleziono użytkownika z tym adresem e-mail."}
    if user.confirmed:
        logger.info(f"Email {user.email} jest już potwierdzony")
        return {"message": "Twój e-mail jest już potwierdzony."}

    token = auth_service.create_token(subject=user.email, scope="email_confirm", expires_delta=3600 * 24)
    template_body = {"host": str(request.base_url), "username": user.username, "token": token}
    background_tasks.add_task(
        email_service.send_email,
        email=user.email,
        subject="Potwierdź swój e-mail",
        template_name="email_template.html",
        template_body=template_body
    )
    return {"message": "Wysłano e-mail z potwierdzeniem."}


@router.post('/request_password_reset')
async def request_password_reset(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user = await repository_users.get_user_by_email(body.email, db)
    if not user or not user.confirmed:
        return {"message": "Nie znaleziono potwierdzonego e-maila powiązanego z kontem."}

    token = auth_service.create_token(subject=user.email, scope="reset_password", expires_delta=3600)
    template_body = {
        "host": str(request.base_url),
        "username": user.username,
        "token": token,
        "reset_link": f"{str(request.base_url)}reset_password?token={token}"
    }
    background_tasks.add_task(
        email_service.send_email,
        email=user.email,
        subject="Reset hasła",
        template_name="reset_password_email.html",
        template_body=template_body
    )
    return {"message": "Wysłano link do resetu hasła (jeśli e-mail istnieje i jest potwierdzony)."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        email = await auth_service.decode_token(data.token, expected_scope="reset_password")
    except Exception:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token resetu hasła.")

    user = await repository_users.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika.")

    auth_service.validate_password(data.new_password)
    hashed_password = auth_service.get_password_hash(data.new_password)
    await repository_users.update_password(user.username, hashed_password, db)

    return {"detail": "Hasło zostało zaktualizowane."}