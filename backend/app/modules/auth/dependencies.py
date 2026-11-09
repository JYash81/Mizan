"""FastAPI authentication, principal resolution, and CSRF guard dependencies."""

import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.identity import AccountStatus, User
from app.modules.auth.services import session_service
from app.modules.auth.services.session_service import AuthenticatedPrincipal


def get_correlation_id(request: Request) -> str:
    """Extract or generate a request correlation ID for audit and error tracking."""
    return (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )


def extract_session_token(
    request: Request, settings: Settings | None = None
) -> tuple[str | None, str]:
    """Extract raw session token and indicate its source ('cookie' or 'bearer')."""
    settings = settings or get_settings()

    # 1. Primary browser transport: HttpOnly session cookie
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token, "cookie"

    # 2. Programmatic API/CLI transport: Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header.removeprefix("Bearer ").strip()
        if bearer_token:
            return bearer_token, "bearer"

    return None, "none"


def get_optional_principal(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedPrincipal | None:
    """Resolve the active principal from session credentials if present, returning None if unauthenticated."""
    token, _ = extract_session_token(request, settings)
    if not token:
        return None
    return session_service.validate_session(db, token, settings)


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedPrincipal:
    """Require an authenticated, valid, unexpired, and unrevoked session."""
    principal = get_optional_principal(request, db, settings)
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return principal


def get_current_active_user(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> User:
    """Require an active user entity corresponding to the validated principal."""
    user = db.get(User, principal.user_id)
    if user is None or user.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account is not active.")
    return user


def require_csrf(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforce CSRF token validation on state-changing requests using cookie authentication."""
    state_changing_methods = {"POST", "PUT", "PATCH", "DELETE"}
    if request.method.upper() not in state_changing_methods:
        return

    token, source = extract_session_token(request, settings)
    if source == "cookie":
        csrf_token = request.headers.get("X-CSRF-Token") or request.headers.get("X-XSRF-Token")
        if (
            not csrf_token
            or not token
            or not session_service.validate_csrf(db, token, csrf_token, settings)
        ):
            raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")
