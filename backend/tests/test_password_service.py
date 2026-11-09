import logging

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type

from app.core.config import Settings
from app.modules.auth.services.password_service import (
    MAX_LENGTH,
    PasswordPolicyError,
    hash_password,
    needs_rehash,
    validate_password_policy,
    verify_password,
)


def test_argon2id_hashing_uses_fresh_salts() -> None:
    password = "correct horse battery staple"
    first, second = hash_password(password), hash_password(password)
    assert first.startswith("$argon2id$") and first != password and first != second
    assert verify_password(password, first)


def test_verification_is_safe_for_wrong_and_malformed_values() -> None:
    encoded = hash_password("long enough secret")
    assert not verify_password("wrong password", encoded)
    assert not verify_password("long enough secret", "not-an-argon-hash")
    assert not verify_password("", encoded)


def test_unicode_and_whitespace_are_preserved() -> None:
    password = "  a secure multilingual 密码 phrase  "
    encoded = hash_password(password)
    assert verify_password(password, encoded) and not verify_password(password.strip(), encoded)


@pytest.mark.parametrize("password", ["", "short", "x" * (MAX_LENGTH + 1), "x" * 1025])
def test_policy_rejects_invalid_input(password: str) -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password_policy(password)


def test_policy_allows_passphrases() -> None:
    validate_password_policy("just a sufficiently long phrase")
    validate_password_policy("é" * 12)


def test_hash_upgrade_and_malformed_safety() -> None:
    legacy = PasswordHasher(
        time_cost=2, memory_cost=19456, parallelism=1, hash_len=16, salt_len=16, type=Type.ID
    )
    assert needs_rehash(legacy.hash("long enough secret"))
    assert not needs_rehash("malformed") and not needs_rehash(hash_password("long enough secret"))


def test_insecure_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(argon2_memory_cost=1).validate_argon2_settings()


def test_passwords_and_hashes_are_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    password = "super secret passphrase"
    with caplog.at_level(logging.DEBUG):
        encoded = hash_password(password)
        verify_password(password, encoded)
    assert password not in caplog.text and encoded not in caplog.text
