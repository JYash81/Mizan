"""Process-wide test safety configuration.

Tests must never inherit a developer's or production SMTP configuration from
``backend/.env``.  In addition to making test outcomes deterministic, this
prevents fixtures using example addresses from attempting real delivery.
"""

from __future__ import annotations

import os

import pytest

# This module is imported by pytest before application test modules import
# ``app.main`` and construct its cached settings.
os.environ.update(
    {
        "APP_ENV": "test",
        "DEBUG": "false",
        "SMTP_ENABLED": "false",
        "SMTP_HOST": "",
    }
)

from app.core.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_cached_settings() -> None:
    """Ensure no test reuses cached settings from another test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
