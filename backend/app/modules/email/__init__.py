"""Email notifications module."""

from app.modules.email.provider import (
    DevelopmentEmailProvider,
    EmailProvider,
    SentEmail,
    get_email_provider,
)

__all__ = [
    "DevelopmentEmailProvider",
    "EmailProvider",
    "SentEmail",
    "get_email_provider",
]
