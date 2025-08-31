import os
import re
from typing import Optional, Dict, Union
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from src.database.models import User
from src.database.db import get_db
from src.repository import users as repository_users

load_dotenv()


class AuthService:
    SECRET_KEY: str = os.getenv("SECRET_KEY") or ""
    if not SECRET_KEY:
        raise RuntimeError("Brak ustawionej zmiennej środowiskowej SECRET_KEY")

    ALGORITHM: str = os.getenv("ALGORITHM") or "HS256"
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

    # -------------------------
    # Hashowanie i weryfikacja haseł
    # -------------------------

    def get_password_hash(self, password: str) -> str:
        """
        Generate a hashed password.

        Args:
            password (str): The password to hash.

        Returns:
            str: The hashed password.
        """
        return self.pwd_context.hash(password)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify the plain password against the hashed password.

        Args:
            plain_password (str): The plain text password.
            hashed_password (str): The hashed password.

        Returns:
            bool: True if passwords match, False otherwise.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

        # -------------------------
        # Walidacja hasła
        # -------------------------

    def validate_password(self, password: str) -> None:
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Hasło musi mieć co najmniej 8 znaków.")
        if not re.search(r"[A-Z]", password):
            raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jedną wielką literę.")
        if not re.search(r"[a-z]", password):
            raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jedną małą literę.")
        if not re.search(r"[0-9]", password):
            raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jedną cyfrę.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jeden znak specjalny.")

        # -------------------------
        # Tworzenie tokenów
        # -------------------------

    def create_token(
            self, subject: str, scope: str, expires_delta: Optional[float] = None
    ) -> str:

        now = datetime.utcnow()
        to_encode = {"sub": subject, "scope": scope, "iat": now}

        if expires_delta is not None:
            expire = now + timedelta(seconds=expires_delta)
        else:
            expire = {
                "access_token": now + timedelta(minutes=15),
                "refresh_token": now + timedelta(days=7)
            }.get(scope, now + timedelta(hours=1))

        to_encode["exp"] = expire
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

        # -------------------------
        # Dekodowanie tokenów
        # -------------------------

    async def decode_token(self, token: str, expected_scope: str) -> str:
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload.get("scope") != expected_scope:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Nieprawidłowy typ tokena."
                )
            subject = payload.get("sub")
            if not subject:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Brak danych w tokenie."
                )
            return subject
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nie można zweryfikować tokenu."
            )

        # -------------------------
        # Pobranie aktualnego użytkownika
        # -------------------------

    async def get_current_user(
            self,
            token: str = Depends(oauth2_scheme),
            db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        Pobiera aktualnie zalogowanego użytkownika na podstawie tokenu.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowe dane uwierzytelniające.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        username = await self.decode_token(token, expected_scope="access_token")
        user: Optional[User] = await repository_users.get_user_by_username(username, db)
        if not user:
            raise credentials_exception
        return user

        # -------------------------
        # Odświeżanie tokenów
        # -------------------------

    async def refresh_access_token(self, refresh_token: str, db: AsyncSession) -> str:
        username = await self.decode_token(refresh_token, expected_scope="refresh_token")
        user = await repository_users.get_user_by_username(username, db)
        if not user:
            raise HTTPException(status_code=401, detail="Nieprawidłowy refresh token")
        return self.create_token(subject=username, scope="access_token")


auth_service = AuthService()
