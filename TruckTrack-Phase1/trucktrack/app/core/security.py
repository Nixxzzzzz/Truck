"""Portable scrypt password hashing and opaque-token primitives."""
import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(key).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        kind, salt, expected = encoded.split('$')
        if kind != 'scrypt':
            return False
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
