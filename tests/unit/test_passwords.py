"""Тесты хеширования паролей."""
import base64

import pytest

from backend.domain.passwords import hash_password, verify_password


def test_hash_stores_algorithm_iterations_salt_and_digest():
    stored = hash_password("секретный пароль")

    algorithm, iterations, salt, digest = stored.split("$")

    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) > 0
    assert base64.b64decode(salt)
    assert base64.b64decode(digest)


def test_verify_accepts_correct_password():
    stored = hash_password("секретный пароль")

    assert verify_password("секретный пароль", stored) is True


def test_verify_rejects_wrong_password():
    stored = hash_password("секретный пароль")

    assert verify_password("другой пароль", stored) is False


def test_same_password_gets_different_salts_and_hashes():
    first = hash_password("одинаковый пароль")
    second = hash_password("одинаковый пароль")

    assert first != second


def test_verify_uses_iterations_from_stored_record():
    stored = hash_password("пароль", iterations=1000)

    assert verify_password("пароль", stored) is True


def test_verify_rejects_garbage_stored_value():
    assert verify_password("пароль", "not-a-hash") is False
    assert verify_password("пароль", "") is False
    assert verify_password("пароль", None) is False


def test_hash_rejects_non_string_password():
    with pytest.raises(TypeError):
        hash_password(None)
