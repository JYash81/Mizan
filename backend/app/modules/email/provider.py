"""Email provider abstraction, SMTP delivery engine, and development email sink."""

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger("app.modules.email")


@dataclass
class SentEmail:
    to: str
    subject: str
    template: str
    context: dict[str, Any]
    sent_at: datetime


class EmailProvider(ABC):
    @abstractmethod
    def send_verification_email(self, email: str, token: str, user_name: str) -> bool:
        pass

    @abstractmethod
    def send_password_reset_email(self, email: str, token: str, user_name: str) -> bool:
        pass

    @abstractmethod
    def send_invitation_email(
        self,
        email: str,
        token: str,
        organization_name: str,
        inviter_name: str,
        role: str,
    ) -> bool:
        pass

    @abstractmethod
    def get_latest_for(self, email: str) -> SentEmail | None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


def _render_base_html(title: str, content_html: str, action_url: str | None = None, action_label: str | None = None) -> str:
    button_html = ""
    if action_url and action_label:
        button_html = f"""
        <div style="margin: 28px 0; text-align: center;">
            <a href="{action_url}" style="background-color: #2563eb; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block; box-shadow: 0 2px 4px rgba(37,99,235,0.2);">
                {action_label}
            </a>
        </div>
        <p style="font-size: 13px; color: #64748b; word-break: break-all; margin-top: 20px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{action_url}" style="color: #2563eb;">{action_url}</a>
        </p>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 32px 16px; color: #0f172a;">
    <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
        <div style="background-color: #0f172a; padding: 24px 32px; text-align: left;">
            <span style="font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">MIZAN</span>
            <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">Enterprise AI Platform</span>
        </div>
        <div style="padding: 32px;">
            <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 16px;">{title}</h1>
            {content_html}
            {button_html}
        </div>
        <div style="background-color: #f1f5f9; padding: 16px 32px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0;">
            <p style="margin: 0;">This is an automated security transmission from Mizan. If you did not initiate this request, no action is required.</p>
        </div>
    </div>
</body>
</html>"""


class DevelopmentEmailProvider(EmailProvider):
    """In-memory sink for development, automated testing, and local console inspection."""

    def __init__(self, frontend_url: str = "http://localhost:5173") -> None:
        self.outbox: list[SentEmail] = []
        self.frontend_url = frontend_url.rstrip("/")

    def send_verification_email(self, email: str, token: str, user_name: str) -> bool:
        link = f"{self.frontend_url}/verify-email?token={token}"
        sent = SentEmail(
            to=email,
            subject="Verify your Mizan account",
            template="verify_email",
            context={"user_name": user_name, "token": token, "action_url": link},
            sent_at=datetime.now(UTC),
        )
        self.outbox.append(sent)
        logger.info(
            "\n" + "=" * 72 + "\n"
            f" [DEV EMAIL SINK] TO: {email}\n"
            f"  SUBJECT: Verify your Mizan account\n"
            f"  VERIFY LINK: {link}\n"
            f"  TOKEN: {token}\n"
            + "=" * 72
        )
        return True

    def send_password_reset_email(self, email: str, token: str, user_name: str) -> bool:
        link = f"{self.frontend_url}/reset-password?token={token}"
        sent = SentEmail(
            to=email,
            subject="Reset your Mizan password",
            template="password_reset",
            context={"user_name": user_name, "token": token, "action_url": link},
            sent_at=datetime.now(UTC),
        )
        self.outbox.append(sent)
        logger.info(
            "\n" + "=" * 72 + "\n"
            f" [DEV EMAIL SINK] TO: {email}\n"
            f"  SUBJECT: Reset your Mizan password\n"
            f"  RESET LINK: {link}\n"
            f"  TOKEN: {token}\n"
            + "=" * 72
        )
        return True

    def send_invitation_email(
        self,
        email: str,
        token: str,
        organization_name: str,
        inviter_name: str,
        role: str,
    ) -> bool:
        link = f"{self.frontend_url}/onboarding?token={token}"
        sent = SentEmail(
            to=email,
            subject=f"Invitation to join {organization_name} on Mizan",
            template="invitation",
            context={
                "organization_name": organization_name,
                "inviter_name": inviter_name,
                "role": role,
                "token": token,
                "action_url": link,
            },
            sent_at=datetime.now(UTC),
        )
        self.outbox.append(sent)
        logger.info(
            "\n" + "=" * 72 + "\n"
            f" [DEV EMAIL SINK] TO: {email}\n"
            f"  SUBJECT: Invitation to join {organization_name}\n"
            f"  ACCEPT LINK: {link}\n"
            f"  TOKEN: {token}\n"
            + "=" * 72
        )
        return True

    def get_latest_for(self, email: str) -> SentEmail | None:
        for mail in reversed(self.outbox):
            if mail.to.lower() == email.lower():
                return mail
        return None

    def clear(self) -> None:
        self.outbox.clear()


class SMTPEmailProvider(EmailProvider):
    """Production-grade SMTP email delivery provider supporting SSL/TLS and Hostinger."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.host = settings.smtp_host or "smtp.hostinger.com"
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email or "no-reply@mizan.ai"
        self.from_name = settings.smtp_from_name or "Mizan Platform"
        self.use_ssl = settings.smtp_use_ssl
        self.use_tls = settings.smtp_use_tls
        self.frontend_url = settings.frontend_url.rstrip("/")
        self.outbox: list[SentEmail] = []

    def _deliver(
        self,
        to_email: str,
        subject: str,
        template: str,
        context: dict[str, Any],
        text_content: str,
        html_content: str,
    ) -> bool:
        sent_record = SentEmail(
            to=to_email,
            subject=subject,
            template=template,
            context=context,
            sent_at=datetime.now(UTC),
        )
        self.outbox.append(sent_record)
        _dev_provider.outbox.append(sent_record)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((self.from_name, self.from_email))
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as server:
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as server:
                    if self.use_tls:
                        server.starttls()
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.send_message(msg)
            logger.info("Successfully dispatched email via SMTP to %s (subject: %s)", to_email, subject)
            return True
        except Exception as exc:
            logger.error("Failed to deliver email via SMTP to %s: %s", to_email, exc, exc_info=True)
            raise RuntimeError(f"SMTP email delivery failure: {exc}") from exc

    def send_verification_email(self, email: str, token: str, user_name: str) -> bool:
        link = f"{self.frontend_url}/verify-email?token={token}"
        subject = "Verify your Mizan account"
        text = (
            f"Hello {user_name},\n\n"
            "Welcome to Mizan! Please verify your email address to activate your account:\n"
            f"{link}\n\n"
            f"Or enter this verification token directly into Mizan: {token}\n\n"
            "This link will expire in 24 hours.\n"
        )
        content_html = f"""
        <p style="font-size: 15px; line-height: 1.6; color: #334155;">Hello <strong>{user_name}</strong>,</p>
        <p style="font-size: 15px; line-height: 1.6; color: #334155;">
            Welcome to Mizan! Please verify your email address to activate your enterprise AI account.
        </p>
        <p style="font-size: 13px; color: #64748b;">Verification code: <code style="background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-weight: 600;">{token}</code></p>
        """
        html = _render_base_html(
            title=subject,
            content_html=content_html,
            action_url=link,
            action_label="Verify My Email",
        )
        return self._deliver(
            to_email=email,
            subject=subject,
            template="verify_email",
            context={"user_name": user_name, "token": token, "action_url": link},
            text_content=text,
            html_content=html,
        )

    def send_password_reset_email(self, email: str, token: str, user_name: str) -> bool:
        link = f"{self.frontend_url}/reset-password?token={token}"
        subject = "Reset your Mizan password"
        text = (
            f"Hello {user_name},\n\n"
            "We received a request to reset the password for your Mizan account.\n"
            f"Click the link below to set a new password:\n{link}\n\n"
            f"Or enter this reset token: {token}\n\n"
            "This link will expire in 15 minutes. If you did not request this, you can safely ignore this email.\n"
        )
        content_html = f"""
        <p style="font-size: 15px; line-height: 1.6; color: #334155;">Hello <strong>{user_name}</strong>,</p>
        <p style="font-size: 15px; line-height: 1.6; color: #334155;">
            We received a request to reset your password. Click the button below to choose a new password. This link is valid for 15 minutes.
        </p>
        <p style="font-size: 13px; color: #64748b;">Reset token: <code style="background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-weight: 600;">{token}</code></p>
        """
        html = _render_base_html(
            title=subject,
            content_html=content_html,
            action_url=link,
            action_label="Reset Password",
        )
        return self._deliver(
            to_email=email,
            subject=subject,
            template="password_reset",
            context={"user_name": user_name, "token": token, "action_url": link},
            text_content=text,
            html_content=html,
        )

    def send_invitation_email(
        self,
        email: str,
        token: str,
        organization_name: str,
        inviter_name: str,
        role: str,
    ) -> bool:
        link = f"{self.frontend_url}/onboarding?token={token}"
        subject = f"Invitation to join {organization_name} on Mizan"
        text = (
            f"Hello,\n\n"
            f"{inviter_name} has invited you to collaborate on {organization_name} with role {role}.\n\n"
            f"Click the link below to accept the invitation:\n{link}\n\n"
            f"Or enter token: {token}\n"
        )
        content_html = f"""
        <p style="font-size: 15px; line-height: 1.6; color: #334155;">
            <strong>{inviter_name}</strong> has invited you to collaborate on <strong>{organization_name}</strong> with role <span style="font-weight: 600; color: #2563eb;">{role}</span>.
        </p>
        <p style="font-size: 15px; line-height: 1.6; color: #334155;">
            Join your organization to access shared datasets, benchmark experiments, and governed model deployments.
        </p>
        """
        html = _render_base_html(
            title=subject,
            content_html=content_html,
            action_url=link,
            action_label="Accept Invitation",
        )
        return self._deliver(
            to_email=email,
            subject=subject,
            template="invitation",
            context={
                "organization_name": organization_name,
                "inviter_name": inviter_name,
                "role": role,
                "token": token,
                "action_url": link,
            },
            text_content=text,
            html_content=html,
        )

    def get_latest_for(self, email: str) -> SentEmail | None:
        for mail in reversed(self.outbox):
            if mail.to.lower() == email.lower():
                return mail
        return None

    def clear(self) -> None:
        self.outbox.clear()


class ProductionEmailProvider(EmailProvider):
    """Production provider that delegates to SMTPEmailProvider when configured."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.smtp_host:
            self._delegate: EmailProvider = SMTPEmailProvider(settings)
        else:
            self._delegate = None

    def _ensure_delegate(self) -> EmailProvider:
        if self._delegate is None:
            raise RuntimeError(
                "Production email delivery is not configured. "
                "Please configure SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD in your .env file."
            )
        return self._delegate

    def send_verification_email(self, email: str, token: str, user_name: str) -> bool:
        return self._ensure_delegate().send_verification_email(email, token, user_name)

    def send_password_reset_email(self, email: str, token: str, user_name: str) -> bool:
        return self._ensure_delegate().send_password_reset_email(email, token, user_name)

    def send_invitation_email(
        self,
        email: str,
        token: str,
        organization_name: str,
        inviter_name: str,
        role: str,
    ) -> bool:
        return self._ensure_delegate().send_invitation_email(
            email, token, organization_name, inviter_name, role
        )

    def get_latest_for(self, email: str) -> SentEmail | None:
        if self._delegate:
            return self._delegate.get_latest_for(email)
        return None

    def clear(self) -> None:
        if self._delegate:
            self._delegate.clear()


_dev_provider = DevelopmentEmailProvider()


def get_email_provider(settings: Settings | None = None) -> EmailProvider:
    settings = settings or get_settings()
    # Update dev provider frontend URL if settings are provided
    if hasattr(settings, "frontend_url") and settings.frontend_url:
        _dev_provider.frontend_url = settings.frontend_url.rstrip("/")

    # If SMTP is explicitly configured, use SMTPEmailProvider
    if settings.smtp_enabled or (settings.smtp_host and settings.smtp_host.strip()):
        return SMTPEmailProvider(settings)

    if settings.app_env == "production":
        return ProductionEmailProvider(settings)

    return _dev_provider
