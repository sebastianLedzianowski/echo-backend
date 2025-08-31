import os
import logging
from pathlib import Path
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def str_to_bool(value: str) -> bool:
    return value.lower() in {"true", "1", "yes"}


class EmailService:
    def __init__(self):
        self.conf = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            MAIL_FROM=os.getenv("MAIL_FROM"),
            MAIL_PORT=int(os.getenv("MAIL_PORT")),
            MAIL_SERVER=os.getenv("MAIL_SERVER"),
            MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "Echo Team"),
            MAIL_STARTTLS=str_to_bool(os.getenv("MAIL_STARTTLS", "False")),
            MAIL_SSL_TLS=str_to_bool(os.getenv("MAIL_SSL_TLS", "False")),
            USE_CREDENTIALS=str_to_bool(os.getenv("USE_CREDENTIALS", "True")),
            VALIDATE_CERTS=str_to_bool(os.getenv("VALIDATE_CERTS", "True")),
            TEMPLATE_FOLDER=Path(__file__).parent / "templates",
        )
        self.fast_mail = FastMail(self.conf)

    async def send_email(
            self,
            email: EmailStr,
            subject: str,
            template_name: str,
            template_body: dict,
    ) -> None:
        """
        Wysyła e-mail asynchronicznie przy użyciu szablonu HTML.

        Args:
            email (EmailStr): Adres odbiorcy
            subject (str): Temat wiadomości
            template_name (str): Nazwa szablonu HTML
            template_body (dict): Dane do wstawienia w szablon

        Raises:
            ConnectionErrors: Błąd połączenia z serwerem SMTP
        """
        try:
            logger.info(f"Próba wysłania e-maila do {email}")
            logger.info(f"Konfiguracja SMTP: {self.conf.MAIL_SERVER}:{self.conf.MAIL_PORT}")
            logger.info(f"Szablon: {template_name}")
            logger.info(f"Dane szablonu: {template_body}")
            
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                template_body=template_body,
                subtype=MessageType.html,
            )
            await self.fast_mail.send_message(message, template_name=template_name)
            logger.info(f"E-mail wysłany pomyślnie do {email}")
        except ConnectionErrors as err:
            logger.error(f"Błąd wysyłki e-maila do {email}: {err}")
            raise
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas wysyłania e-maila do {email}: {e}")
            raise


# Tworzymy instancję serwisu, gotową do użycia
email_service = EmailService()
