"""Tests for SMTP email provider and email dispatch."""

from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.modules.email.provider import (
    DevelopmentEmailProvider,
    SMTPEmailProvider,
    get_email_provider,
)


def test_smtp_email_provider_dispatch():
    settings = Settings(
        smtp_enabled=True,
        smtp_host="smtp.hostinger.com",
        smtp_port=465,
        smtp_user="test@example.com",
        smtp_password="test-password",
        smtp_from_email="no-reply@example.com",
        smtp_from_name="Mizan AI",
        smtp_use_ssl=True,
        frontend_url="https://app.example.com",
    )

    provider = SMTPEmailProvider(settings)

    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_server

        # 1. Test Verification Email
        success_v = provider.send_verification_email(
            email="user@test.com",
            token="test-verify-token-123",
            user_name="Alice User",
        )
        assert success_v is True
        assert mock_server.login.called
        assert mock_server.send_message.called

        # Inspect sent message
        msg = mock_server.send_message.call_args[0][0]
        assert msg["To"] == "user@test.com"
        assert "Mizan AI" in msg["From"]
        assert "Verify your Mizan account" in msg["Subject"]

        # Check that action URL is in context
        latest = provider.get_latest_for("user@test.com")
        assert latest is not None
        assert "https://app.example.com/verify-email?token=test-verify-token-123" in latest.context["action_url"]

        # 2. Test Password Reset Email
        mock_server.reset_mock()
        success_p = provider.send_password_reset_email(
            email="user@test.com",
            token="test-reset-token-456",
            user_name="Alice User",
        )
        assert success_p is True
        assert mock_server.send_message.called
        msg_reset = mock_server.send_message.call_args[0][0]
        assert "Reset your Mizan password" in msg_reset["Subject"]

        latest_reset = provider.get_latest_for("user@test.com")
        assert latest_reset is not None
        assert "https://app.example.com/reset-password?token=test-reset-token-456" in latest_reset.context["action_url"]


def test_get_email_provider_factory():
    # Dev settings
    dev_settings = Settings(app_env="development", smtp_host=None, smtp_enabled=False)
    provider = get_email_provider(dev_settings)
    assert isinstance(provider, DevelopmentEmailProvider)

    # SMTP settings
    smtp_settings = Settings(
        app_env="production",
        session_cookie_secure=True,
        secret_key="a" * 32,
        smtp_host="smtp.hostinger.com",
        smtp_enabled=True,
    )
    provider_smtp = get_email_provider(smtp_settings)
    assert isinstance(provider_smtp, SMTPEmailProvider)
