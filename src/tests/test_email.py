import pytest
from unittest.mock import patch
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr, BaseModel

class EmailData(BaseModel):
    email: EmailStr

from src.services.email import EmailService, str_to_bool


# ================== HELPER FUNCTIONS ==================
def create_test_email_service():
    """Tworzy instancję serwisu email do testów"""
    with patch("os.getenv") as mock_getenv:
        # Ustaw podstawowe wartości dla konfiguracji
        mock_getenv.side_effect = lambda key, default=None: {
            "MAIL_USERNAME": "test@example.com",
            "MAIL_PASSWORD": "test_password",
            "MAIL_FROM": "noreply@example.com",
            "MAIL_PORT": "587",
            "MAIL_SERVER": "smtp.example.com",
            "MAIL_FROM_NAME": "Test Team",
            "MAIL_STARTTLS": "True",
            "MAIL_SSL_TLS": "False",
            "USE_CREDENTIALS": "True",
            "VALIDATE_CERTS": "True"
        }.get(key, default)
        
        return EmailService()


# ================== CONFIGURATION TESTS ==================
def test_str_to_bool():
    """Test konwersji string na bool"""
    assert str_to_bool("true") is True
    assert str_to_bool("True") is True
    assert str_to_bool("1") is True
    assert str_to_bool("yes") is True
    assert str_to_bool("false") is False
    assert str_to_bool("False") is False
    assert str_to_bool("0") is False
    assert str_to_bool("no") is False
    assert str_to_bool("random") is False


def test_email_service_configuration():
    """Test konfiguracji serwisu email"""
    service = create_test_email_service()
    
    assert service.conf.MAIL_USERNAME == "test@example.com"
    assert service.conf.MAIL_PASSWORD.get_secret_value() == "test_password"
    assert service.conf.MAIL_FROM == "noreply@example.com"
    assert service.conf.MAIL_PORT == 587
    assert service.conf.MAIL_SERVER == "smtp.example.com"
    assert service.conf.MAIL_FROM_NAME == "Test Team"
    assert service.conf.MAIL_STARTTLS is True
    assert service.conf.MAIL_SSL_TLS is False
    assert service.conf.USE_CREDENTIALS is True
    assert service.conf.VALIDATE_CERTS is True


# ================== SEND EMAIL TESTS ==================
@pytest.mark.asyncio
async def test_send_email_success():
    """Test pomyślnego wysłania emaila"""
    service = create_test_email_service()
    
    # Mock FastMail.send_message
    with patch.object(service.fast_mail, "send_message") as mock_send:
        mock_send.return_value = None
        
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject="Test Subject",
            template_name="email_template.html",
            template_body={
                "username": "testuser",
                "host": "http://localhost:8000/",
                "token": "test_token"
            }
        )
        
        # Sprawdź czy send_message został wywołany
        assert mock_send.called
        # Sprawdź argumenty wywołania
        call_args = mock_send.call_args
        message = call_args[0][0]
        template_name = call_args[1]["template_name"]
        
        assert message.subject == "Test Subject"
        assert message.recipients == ["user@example.com"]
        assert template_name == "email_template.html"


@pytest.mark.asyncio
async def test_send_email_connection_error():
    """Test błędu połączenia SMTP"""
    service = create_test_email_service()
    
    # Mock FastMail.send_message aby rzucał ConnectionErrors
    with patch.object(service.fast_mail, "send_message") as mock_send:
        mock_send.side_effect = ConnectionErrors("Connection failed")
        
        with pytest.raises(ConnectionErrors) as exc_info:
            await service.send_email(
                email=EmailData(email="user@example.com").email,
                subject="Test Subject",
                template_name="email_template.html",
                template_body={"username": "testuser"}
            )
        
        assert "Connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_email_unexpected_error():
    """Test nieoczekiwanego błędu"""
    service = create_test_email_service()
    
    # Mock FastMail.send_message aby rzucał nieoczekiwany błąd
    with patch.object(service.fast_mail, "send_message") as mock_send:
        mock_send.side_effect = Exception("Unexpected error")
        
        with pytest.raises(Exception) as exc_info:
            await service.send_email(
                email=EmailData(email="user@example.com").email,
                subject="Test Subject",
                template_name="email_template.html",
                template_body={"username": "testuser"}
            )
        
        assert "Unexpected error" in str(exc_info.value)


# ================== TEMPLATE TESTS ==================
@pytest.mark.asyncio
async def test_confirmation_email_template():
    """Test szablonu emaila potwierdzającego"""
    service = create_test_email_service()
    template_data = {
        "username": "testuser",
        "host": "http://localhost:8000/",
        "token": "test_token"
    }
    
    # Mock FastMail.send_message aby przechwycić dane szablonu
    with patch.object(service.fast_mail, "send_message") as mock_send:
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject="Potwierdź email",
            template_name="email_template.html",
            template_body=template_data
        )
        
        # Sprawdź czy szablon otrzymał poprawne dane
        call_args = mock_send.call_args
        message = call_args[0][0]
        assert message.template_body == template_data


@pytest.mark.asyncio
async def test_reset_password_email_template():
    """Test szablonu emaila resetującego hasło"""
    service = create_test_email_service()
    template_data = {
        "username": "testuser",
        "reset_link": "http://localhost:8000/reset?token=test_token"
    }
    
    # Mock FastMail.send_message aby przechwycić dane szablonu
    with patch.object(service.fast_mail, "send_message") as mock_send:
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject="Reset hasła",
            template_name="reset_password_email.html",
            template_body=template_data
        )
        
        # Sprawdź czy szablon otrzymał poprawne dane
        call_args = mock_send.call_args
        message = call_args[0][0]
        assert message.template_body == template_data


@pytest.mark.asyncio
async def test_send_email_invalid_template():
    """Test nieistniejącego szablonu"""
    service = create_test_email_service()
    
    with pytest.raises(Exception):
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject="Test",
            template_name="nonexistent_template.html",
            template_body={"username": "testuser"}
        )


@pytest.mark.asyncio
async def test_send_email_missing_template_data():
    """Test brakujących danych w szablonie"""
    service = create_test_email_service()
    
    # Próba wysłania emaila bez wymaganych danych w szablonie
    with pytest.raises(Exception):
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject="Test",
            template_name="email_template.html",
            template_body={}  # Brak wymaganych danych
        )


# ================== EDGE CASES TESTS ==================
@pytest.mark.asyncio
async def test_send_email_empty_subject():
    """Test pustego tematu"""
    service = create_test_email_service()
    
    with patch.object(service.fast_mail, "send_message") as mock_send:
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject="",
            template_name="email_template.html",
            template_body={"username": "testuser"}
        )
        
        # Sprawdź czy email został wysłany mimo pustego tematu
        assert mock_send.called
        message = mock_send.call_args[0][0]
        assert message.subject == ""


@pytest.mark.asyncio
async def test_send_email_long_subject():
    """Test bardzo długiego tematu"""
    service = create_test_email_service()
    long_subject = "A" * 1000  # Bardzo długi temat
    
    with patch.object(service.fast_mail, "send_message") as mock_send:
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject=long_subject,
            template_name="email_template.html",
            template_body={"username": "testuser"}
        )
        
        # Sprawdź czy email został wysłany z długim tematem
        assert mock_send.called
        message = mock_send.call_args[0][0]
        assert message.subject == long_subject


@pytest.mark.asyncio
async def test_send_email_special_characters():
    """Test znaków specjalnych w danych"""
    service = create_test_email_service()
    special_chars = "!@#$%^&*()_+{}|:<>?~`-=[]\\;',./'"
    
    with patch.object(service.fast_mail, "send_message") as mock_send:
        await service.send_email(
            email=EmailData(email="user@example.com").email,
            subject=f"Test {special_chars}",
            template_name="email_template.html",
            template_body={
                "username": f"test{special_chars}user",
                "host": "http://localhost:8000/",
                "token": f"test{special_chars}token"
            }
        )
        
        # Sprawdź czy email został wysłany ze znakami specjalnymi
        assert mock_send.called
