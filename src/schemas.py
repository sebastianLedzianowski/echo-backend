from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, constr
from enum import Enum


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

    model_config = {
        "from_attributes": True
    }


class AdminUserDb(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    confirmed: bool

    model_config = {
        "from_attributes": True
    }


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


# Enums dla testów psychologicznych
class TestTypeEnum(str, Enum):
    ASRS = "asrs"
    GAD7 = "gad7"
    PHQ9 = "phq9"


# Schematy dla testów psychologicznych
class ASRSAnswers(BaseModel):
    """Odpowiedzi dla testu ASRS v1.1"""
    part_a: List[int] = Field(..., min_items=6, max_items=6,
                              description="Odpowiedzi na część A (6 pytań)")
    part_b: List[int] = Field(..., min_items=12, max_items=12,
                              description="Odpowiedzi na część B (12 pytań)")

    class Config:
        json_schema_extra = {
            "example": {
                "part_a": [2, 3, 1, 4, 2, 3],
                "part_b": [1, 2, 3, 2, 1, 0, 2, 3, 1, 2, 1, 3]
            }
        }


class GAD7Answers(BaseModel):
    """Odpowiedzi dla testu GAD-7"""
    answers: List[int] = Field(..., min_items=7, max_items=7,
                               description="Odpowiedzi na 7 pytań (0-3)")

    class Config:
        json_schema_extra = {
            "example": {
                "answers": [1, 2, 1, 3, 0, 2, 1]
            }
        }


class PHQ9Answers(BaseModel):
    """Odpowiedzi dla testu PHQ-9"""
    answers: List[int] = Field(..., min_items=9, max_items=9,
                               description="Odpowiedzi na 9 pytań (0-3)")

    class Config:
        json_schema_extra = {
            "example": {
                "answers": [2, 1, 3, 2, 1, 0, 2, 1, 0]
            }
        }


class TestSubmission(BaseModel):
    """Model dla przesyłania odpowiedzi na test"""
    test_type: TestTypeEnum
    answers: Dict[str, Any] = Field(...,
                                    description="Odpowiedzi na pytania testowe")


class TestResult(BaseModel):
    """Model wyniku testu"""
    id: int
    test_type: str
    score: Optional[float]
    interpretation: Optional[str]
    ai_analysis: Optional[str]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class TestAnalysis(BaseModel):
    """Model analizy testu"""
    score: float
    interpretation: str
    ai_analysis: str
    recommendations: Optional[str] = None


class TestHistoryResponse(BaseModel):
    """Model odpowiedzi z historią testów"""
    tests: List[TestResult]
    total_count: int


# Schematy dla wiadomości kontaktowych
class ContactMessageType(str, Enum):
    """Typy wiadomości kontaktowych"""
    GENERAL = "general"  # Ogólne pytanie
    SUPPORT = "support"  # Wsparcie techniczne
    BUG_REPORT = "bug_report"  # Zgłoszenie błędu
    FEATURE_REQUEST = "feature_request"  # Prośba o funkcję
    COMPLAINT = "complaint"  # Skarga
    OTHER = "other"  # Inne


class ContactMessageCreate(BaseModel):
    """Model tworzenia wiadomości kontaktowej"""
    name: str = Field(..., min_length=2, max_length=100,
                      description="Imię i nazwisko")
    email: EmailStr = Field(..., description="Adres email")
    subject: str = Field(..., min_length=5, max_length=200,
                         description="Temat wiadomości")
    message: str = Field(..., min_length=10, max_length=2000,
                         description="Treść wiadomości")
    message_type: ContactMessageType = Field(
        default=ContactMessageType.GENERAL, description="Typ wiadomości")
    priority: int = Field(default=1, ge=1, le=5,
                          description="Priorytet (1-5, gdzie 5 to najwyższy)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Jan Kowalski",
                "email": "jan.kowalski@example.com",
                "subject": "Problem z logowaniem",
                "message": "Nie mogę się zalogować do aplikacji. Otrzymuję błąd 500.",
                "message_type": "bug_report",
                "priority": 3
            }
        }


class ContactMessageResponse(BaseModel):
    """Model odpowiedzi dla wiadomości kontaktowej"""
    id: int
    name: str
    email: str
    subject: str
    message: str
    message_type: str
    priority: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    admin_notes: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class ContactMessageUpdate(BaseModel):
    """Model aktualizacji wiadomości kontaktowej (dla adminów)"""
    status: Optional[str] = Field(None, description="Status wiadomości")
    admin_notes: Optional[str] = Field(None, max_length=1000,
                                       description="Notatki administratora")
    priority: Optional[int] = Field(None, ge=1, le=5,
                                    description="Priorytet (1-5)")


class ContactMessageListResponse(BaseModel):
    """Model odpowiedzi z listą wiadomości kontaktowych"""
    messages: List[ContactMessageResponse]
    total_count: int
    page: int
    per_page: int
