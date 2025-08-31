from typing import List
from pydantic_settings import BaseSettings
from pydantic import EmailStr, Field, validator


class Settings(BaseSettings):
    """
    Konfiguracja aplikacji z walidacją i wartościami domyślnymi.
    
    Atrybuty:
        sqlalchemy_database_url (str): URL do bazy danych SQLAlchemy.
        secret_key (str): Klucz sekretny aplikacji (min. 32 znaki).
        algorithm (str): Algorytm używany do uwierzytelniania (domyślnie HS256).
        encryption_key (str): Klucz Fernet (32 bajty w base64).
        
        mail_* : Konfiguracja serwera pocztowego
        postgres_* : Konfiguracja bazy danych PostgreSQL
        ollama_* : Konfiguracja serwisu Ollama
        
    Walidacja:
        - Sprawdzanie długości i formatu kluczy
        - Walidacja adresów email
        - Sprawdzanie portów
        - Walidacja URL
    """
    # Additional fields
    context_message_limit: str = "10"
    hf_token: str = "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"
    model_id: str = "speakleash/Bielik-1.5B-v3.0-Instruct"
    # Database URL
    sqlalchemy_database_url: str = Field(..., description="URL do bazy danych SQLAlchemy")

    # Security settings
    secret_key: str = Field(..., min_length=32, description="Klucz sekretny (min. 32 znaki)")
    algorithm: str = Field(default="HS256", description="Algorytm JWT")
    encryption_key: str = Field(..., min_length=32, description="Klucz Fernet (base64)")

    # Email configuration
    mail_username: str = Field(..., description="Nazwa użytkownika SMTP")
    mail_password: str = Field(..., min_length=8, description="Hasło SMTP")
    mail_port: int = Field(default=587, ge=1, le=65535, description="Port SMTP")
    mail_server: str = Field(..., description="Serwer SMTP")
    mail_from: EmailStr = Field(..., description="Adres email nadawcy")
    mail_starttls: bool = Field(default=True, description="Użyj STARTTLS")
    mail_ssl_tls: bool = Field(default=False, description="Użyj SSL/TLS")
    use_credentials: bool = Field(default=True, description="Użyj uwierzytelniania")
    validate_certs: bool = Field(default=True, description="Sprawdzaj certyfikaty")
    mail_from_name: str = Field(default="Echo Team", description="Nazwa nadawcy")

    # PostgreSQL configuration
    postgres_db: str = Field(..., description="Nazwa bazy danych")
    postgres_user: str = Field(..., description="Użytkownik PostgreSQL")
    postgres_password: str = Field(..., min_length=8, description="Hasło PostgreSQL")
    postgres_port: int = Field(default=5432, ge=1, le=65535, description="Port PostgreSQL")
    postgres_server: str = Field(default="localhost", description="Host PostgreSQL")

    # Ollama configuration
    ollama_api_url: str = Field(
        default="http://localhost:11434",
        description="URL API Ollama"
    )
    ollama_model: str = Field(
        default="llama2",
        description="Nazwa modelu Ollama"
    )

    @validator("mail_port", "postgres_port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port musi być między 1 a 65535")
        return v

    @validator("secret_key", "encryption_key")
    def validate_keys(cls, v):
        if len(v) < 32:
            raise ValueError("Klucz musi mieć minimum 32 znaki")
        return v

    @validator("ollama_api_url")
    def validate_ollama_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL Ollama musi zaczynać się od http:// lub https://")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
