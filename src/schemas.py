from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, constr


class UserModel(BaseModel):
    username: str = Field(min_length=5, max_length=55)
    password: str = Field(min_length=6, max_length=55)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, min_length=5, max_length=64)


class UserLogin(BaseModel):
    username: str = Field(min_length=5, max_length=55)
    password: str = Field(min_length=6, max_length=55)


class UserDb(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserDb(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    user: UserDb
    detail: str = "User successfully created."


class TokenModel(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RequestEmail(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=55)


class UpdateProfile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class AdminUpdateProfile(BaseModel):
    username: Optional[str] = Field(None, min_length=5, max_length=55)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=64)
    is_active: Optional[bool] = None


class AdminUpdateAdminStatus(BaseModel):
    is_admin: bool


class ChangePassword(BaseModel):
    old_password: constr(min_length=6, max_length=55)
    new_password: constr(min_length=6, max_length=55)


class ConfirmPassword(BaseModel):
    password: constr(min_length=6, max_length=55)


class EchoRequest(BaseModel):
    """Model żądania dla endpointu echo"""
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,  # Maksymalna długość tekstu
        description="Tekst użytkownika do przetworzenia"
    )


