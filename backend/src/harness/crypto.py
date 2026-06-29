from cryptography.fernet import Fernet, InvalidToken
from harness.config import settings
import base64, hashlib


def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(settings.encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_value(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str | None:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return None
