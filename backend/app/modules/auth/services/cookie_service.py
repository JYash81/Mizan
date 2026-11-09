"""Cookie helpers; credentials are intentionally never returned in JSON."""

from fastapi import Response

from app.core.config import Settings, get_settings


def set_session_cookie(
    response: Response, credential: str, settings: Settings | None = None
) -> None:
    settings = settings or get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=credential,
        max_age=settings.session_absolute_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path=settings.session_cookie_path,
        domain=settings.session_cookie_domain,
    )


def clear_session_cookie(response: Response, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path=settings.session_cookie_path,
        domain=settings.session_cookie_domain,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
