import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    secret = str(settings.SECRET_KEY).encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(b"whatsapp-commerce:" + secret).digest())
    return Fernet(key)


def encrypt_access_token(token):
    if not token:
        return ""
    return _fernet().encrypt(str(token).encode("utf-8")).decode("ascii")


def decrypt_access_token(encrypted_token):
    if not encrypted_token:
        return ""
    try:
        return _fernet().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError):
        return ""
