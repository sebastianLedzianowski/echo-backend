from cryptography.fernet import Fernet, InvalidToken
from src.conf.config import settings


class EncryptionService:
    def __init__(self):
        self.fernet = Fernet(settings.encryption_key.encode('utf-8'))

    def encrypt(self, data: str) -> str:
        """
        Szyfruje tekst przy użyciu klucza Fernet.
        
        Args:
            data (str): Tekst do zaszyfrowania
        
        Returns:
            str: Zaszyfrowany tekst w formacie Base64
        """
        return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """
        Odszyfrowuje tekst zaszyfrowany kluczem Fernet.
        
        Args:
            encrypted_data (str): Zaszyfrowany tekst w formacie Base64
        
        Returns:
            str: Odszyfrowany tekst lub komunikat o błędzie
        """
        try:
            return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except (InvalidToken, TypeError, ValueError, UnicodeDecodeError):
            return "[Encrypted content could not be decrypted]"


# Instancja gotowa do użycia
encryption_service = EncryptionService()
