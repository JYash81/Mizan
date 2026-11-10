"""Security tests for Production Configuration Hardening and Secret Validation."""

import pytest

from app.core.config import Settings


def test_default_secret_rejected_in_production():
    """Default development secret must be rejected when app_env=production."""
    with pytest.raises(ValueError, match="Production secret_key must be configured"):
        Settings(
            app_env="production",
            secret_key="replace-with-local-secret",
            session_cookie_secure=True,
            debug=False,
            cors_origins=["https://mizan.ai"],
        )


def test_empty_secret_rejected_in_production():
    """Empty or whitespace secret must be rejected in production."""
    with pytest.raises(ValueError, match="Production secret_key must be configured"):
        Settings(
            app_env="production",
            secret_key="",
            session_cookie_secure=True,
            debug=False,
            cors_origins=["https://mizan.ai"],
        )


def test_secret_below_minimum_rejected_in_production():
    """Secret below 32 characters must be rejected in production."""
    # 31 characters
    short_secret = "a" * 31
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            app_env="production",
            secret_key=short_secret,
            session_cookie_secure=True,
            debug=False,
            cors_origins=["https://mizan.ai"],
        )


def test_secret_at_minimum_accepted_in_production():
    """Valid secret with exactly 32 characters is accepted in production."""
    exact_32_secret = "b" * 32
    settings = Settings(
        app_env="production",
        secret_key=exact_32_secret,
        session_cookie_secure=True,
        debug=False,
        cors_origins=["https://mizan.ai"],
    )
    assert settings.secret_key == exact_32_secret


def test_strong_secret_accepted_in_production():
    """Cryptographically strong 64-character hex secret is accepted in production."""
    strong_secret = "94e8c1b72a084ff5a7114e4cbefea78d052a23337a5f6e80b2a74c43149ef182"
    settings = Settings(
        app_env="production",
        secret_key=strong_secret,
        session_cookie_secure=True,
        debug=False,
        cors_origins=["https://mizan.ai"],
    )
    assert settings.secret_key == strong_secret


def test_debug_enabled_in_production_rejected():
    """Production cannot run with debug=True."""
    with pytest.raises(ValueError, match="Production environment cannot run with debug=True"):
        Settings(
            app_env="production",
            debug=True,
            secret_key="c" * 32,
            session_cookie_secure=True,
            cors_origins=["https://mizan.ai"],
        )


def test_insecure_production_cookie_rejected():
    """Production requires session_cookie_secure=True."""
    with pytest.raises(ValueError, match="Production session cookies must be Secure"):
        Settings(
            _env_file=None,
            app_env="production",
            session_cookie_secure=False,
            session_cookie_samesite="lax",
            secret_key="c" * 32,
            debug=False,
            cors_origins=["https://mizan.ai"],
        )


def test_wildcard_production_cors_rejected():
    """Production rejects wildcard '*' CORS origins."""
    with pytest.raises(ValueError, match="wildcard CORS origins"):
        Settings(
            _env_file=None,
            app_env="production",
            cors_origins="*",
            secret_key="c" * 32,
            session_cookie_secure=True,
            debug=False,
        )


def test_development_defaults_remain_usable():
    """In development mode, development defaults remain usable without error."""
    dev_settings = Settings(
        _env_file=None,
        app_env="development",
        secret_key="replace-with-local-secret",
        debug=False,
        session_cookie_secure=False,
        session_cookie_samesite="lax",
        cors_origins=["http://localhost:5173"],
    )
    assert dev_settings.app_env == "development"
    assert dev_settings.secret_key == "replace-with-local-secret"
