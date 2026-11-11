"""Хеширование и проверка паролей через стандартную библиотеку."""
import base64
import hashlib
import hmac
import secrets

PASSWORD_MIN_LENGTH = 8

_ALGORITHM = "pbkdf2_sha256"
_DEFAULT_ITERATIONS = 310_000
_SALT_BYTES = 16
_KEY_BYTES = 32


def hash_password(password: str, iterations: int = _DEFAULT_ITERATIONS) -> str:
    """Захешировать пароль строкой формата pbkdf2_sha256$итерации$соль$хеш."""
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = _derive_key(password, salt, iterations)
    return "$".join([
        _ALGORITHM,
        str(iterations),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ])


def verify_password(password: str, stored: str) -> bool:
    """Проверить пароль, используя итерации и соль из сохранённой строки."""
    if not isinstance(password, str) or not isinstance(stored, str):
        return False
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = stored.split("$")
        iterations = int(raw_iterations)
        salt = base64.b64decode(raw_salt.encode("ascii"))
        expected = base64.b64decode(raw_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False
    if algorithm != _ALGORITHM or iterations <= 0 or not expected:
        return False
    digest = _derive_key(password, salt, iterations, length=len(expected))
    return hmac.compare_digest(digest, expected)


def _derive_key(password, salt, iterations, length=_KEY_BYTES):
    """Считать ключ PBKDF2-HMAC-SHA256 для пароля и соли."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=length,
    )
