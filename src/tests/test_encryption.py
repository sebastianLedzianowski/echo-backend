
import pytest
from src.services.encryption import EncryptionService
from src.conf.config import settings
from cryptography.fernet import Fernet


@pytest.fixture
def encryption_service():
    """Fixture to provide an instance of EncryptionService."""
    # Ensure the key is properly encoded for Fernet
    if isinstance(settings.encryption_key, str):
        key = settings.encryption_key.encode('utf-8')
    else:
        key = settings.encryption_key

    # Validate key length for Fernet
    if len(key) != 32:
        # If the key is not 32 bytes, generate a valid one for testing
        key = Fernet.generate_key()
    
    settings.encryption_key = key.decode('utf-8')
    return EncryptionService()


def test_encryption_service_initialization(encryption_service):
    """Test that EncryptionService initializes correctly."""
    assert isinstance(encryption_service, EncryptionService)
    assert hasattr(encryption_service, 'fernet')


def test_encrypt_decrypt_cycle(encryption_service):
    """Test that data can be encrypted and then decrypted back to the original."""
    original_data = "This is a secret message."
    encrypted_data = encryption_service.encrypt(original_data)
    decrypted_data = encryption_service.decrypt(encrypted_data)
    
    assert encrypted_data != original_data
    assert decrypted_data == original_data


def test_decrypt_invalid_token(encryption_service):
    """Test that decrypting an invalid token returns an error message."""
    invalid_token = "this_is_not_a_valid_fernet_token"
    decrypted_data = encryption_service.decrypt(invalid_token)
    
    assert decrypted_data == "[Encrypted content could not be decrypted]"


def test_decrypt_empty_string(encryption_service):
    """Test decrypting an empty string, which should fail."""
    decrypted_data = encryption_service.decrypt("")
    assert decrypted_data == "[Encrypted content could not be decrypted]"
