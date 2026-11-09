"""Argon2id password operations. Values handled here must never be logged."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from app.core.config import Settings, get_settings

MIN_LENGTH = 12
MAX_LENGTH = 128
MAX_UTF8_BYTES = 1024


class PasswordPolicyError(ValueError):
    """Raised before expensive hashing when a password violates the policy."""


def validate_password_policy(password: str) -> None:
    if not isinstance(password, str) or not password:
        raise PasswordPolicyError("Password is required.")
    if len(password) < MIN_LENGTH:
        raise PasswordPolicyError(f"Password must contain at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(f"Password must not exceed {MAX_LENGTH} characters.")
    if len(password.encode("utf-8")) > MAX_UTF8_BYTES:
        raise PasswordPolicyError("Password exceeds the maximum encoded size.")


def _hasher(settings: Settings | None = None) -> PasswordHasher:
    settings = settings or get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
        hash_len=settings.argon2_hash_length,
        salt_len=settings.argon2_salt_length,
        type=Type.ID,
    )


def hash_password(password: str, settings: Settings | None = None) -> str:
    """Validate then return a new salted Argon2id hash for internal persistence."""
    validate_password_policy(password)
    return _hasher(settings).hash(password)


def verify_password(password: str, encoded_hash: str, settings: Settings | None = None) -> bool:
    """Return a safe failure for invalid input, mismatches, and malformed hashes."""
    if (
        not isinstance(password, str)
        or not isinstance(encoded_hash, str)
        or not password
        or not encoded_hash
    ):
        return False
    if len(password.encode("utf-8")) > MAX_UTF8_BYTES:
        return False
    try:
        return bool(_hasher(settings).verify(encoded_hash, password))
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def needs_rehash(encoded_hash: str, settings: Settings | None = None) -> bool:
    """Return True for a valid but outdated hash; malformed hashes safely return False."""
    if not isinstance(encoded_hash, str) or not encoded_hash:
        return False
    try:
        return _hasher(settings).check_needs_rehash(encoded_hash)
    except InvalidHashError:
        return False
