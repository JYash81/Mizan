"""Authentication and identity endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.identity import AccountStatus, AuthSession, TokenPurpose, User
from app.modules.audit.services.audit_service import record_audit_event
from app.modules.auth.dependencies import (
    extract_session_token,
    get_correlation_id,
    get_current_active_user,
    get_current_principal,
    require_csrf,
)
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionInfoResponse,
    UserProfileResponse,
    VerifyEmailRequest,
)
from app.modules.auth.services import (
    cookie_service,
    password_service,
    session_service,
    token_service,
)
from app.modules.auth.services.session_service import AuthenticatedPrincipal
from app.modules.email.provider import get_email_provider
from app.modules.workspaces.services.organization_service import list_user_organizations

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    normalized = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.normalized_email == normalized))
    if existing is not None:
        # Preserve the neutral response for account-enumeration resistance, but
        # honor it for a user who is genuinely waiting for verification. This
        # makes a repeated registration attempt a safe resend path rather than
        # falsely claiming that an email was sent.
        if existing.status == AccountStatus.PENDING_VERIFICATION:
            issued_tok = token_service.create_token(
                db=db,
                user_id=existing.id,
                purpose=TokenPurpose.EMAIL_VERIFICATION,
                settings=settings,
            )
            get_email_provider(settings).send_verification_email(
                email=existing.email,
                token=issued_tok.raw_token,
                user_name=existing.full_name,
            )
            record_audit_event(
                db=db,
                event_type="AUTH_VERIFICATION_RESENT",
                resource_type="user",
                resource_id=existing.id,
                correlation_id=get_correlation_id(request),
            )
            db.commit()
        # Prevent user enumeration with neutral response
        return {
            "data": {
                "message": "If your email is eligible, a verification link has been sent to your inbox."
            }
        }

    pwd_hash = password_service.hash_password(payload.password, settings=settings)
    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.strip(),
        normalized_email=normalized,
        password_hash=pwd_hash,
        status=AccountStatus.PENDING_VERIFICATION,
    )
    db.add(user)
    db.flush()

    # Generate one-time email verification token
    issued_tok = token_service.create_token(
        db=db,
        user_id=user.id,
        purpose=TokenPurpose.EMAIL_VERIFICATION,
        settings=settings,
    )

    # Dispatch email
    email_provider = get_email_provider(settings)
    email_provider.send_verification_email(
        email=user.email,
        token=issued_tok.raw_token,
        user_name=user.full_name,
    )

    correlation_id = get_correlation_id(request)
    record_audit_event(
        db=db,
        event_type="AUTH_REGISTER_SUCCESS",
        resource_type="user",
        resource_id=user.id,
        correlation_id=correlation_id,
        safe_metadata={"email": user.email},
    )
    db.commit()

    return {
        "data": {
            "message": "Registration successful. Please verify your email to activate your account."
        }
    }


@router.post("/verify-email")
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    consumed = token_service.consume_token(
        db=db, raw_token=payload.token, purpose=TokenPurpose.EMAIL_VERIFICATION
    )
    if consumed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    user = db.get(User, consumed.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User associated with token not found.",
        )

    now = datetime.now(UTC)
    user.status = AccountStatus.ACTIVE
    user.email_verified_at = now
    db.flush()

    record_audit_event(
        db=db,
        event_type="AUTH_EMAIL_VERIFIED",
        resource_type="user",
        resource_id=user.id,
        correlation_id=get_correlation_id(request),
    )
    db.commit()

    return {"data": {"message": "Email verified successfully. You may now log in."}}


@router.post("/resend-verification")
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    normalized = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.normalized_email == normalized))
    if user is not None and user.status == AccountStatus.PENDING_VERIFICATION:
        issued = token_service.create_token(
            db=db,
            user_id=user.id,
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            settings=settings,
        )
        email_provider = get_email_provider(settings)
        email_provider.send_verification_email(
            email=user.email,
            token=issued.raw_token,
            user_name=user.full_name,
        )
        record_audit_event(
            db=db,
            event_type="AUTH_VERIFICATION_RESENT",
            resource_type="user",
            resource_id=user.id,
            correlation_id=get_correlation_id(request),
        )
        db.commit()

    return {
        "data": {
            "message": "If an unverified account exists, a new verification link has been sent."
        }
    }


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    correlation_id = get_correlation_id(request)
    normalized = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.normalized_email == normalized))

    invalid_msg = "Invalid email or password."
    if user is None or not password_service.verify_password(
        payload.password, user.password_hash, settings
    ):
        record_audit_event(
            db=db,
            event_type="AUTH_LOGIN_FAILED",
            resource_type="user",
            actor_user_id=user.id if user else None,
            correlation_id=correlation_id,
            safe_metadata={"attempted_email": normalized},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_msg)

    if user.status == AccountStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in.",
        )

    if user.status in (AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Please contact support.",
        )

    # Rehash check
    if password_service.needs_rehash(user.password_hash, settings):
        user.password_hash = password_service.hash_password(payload.password, settings)

    now = datetime.now(UTC)
    user.last_login_at = now

    # Issue opaque session & CSRF credentials
    issued = session_service.create_session(db, user.id, settings)
    db.flush()

    # Set secure HttpOnly session cookie
    cookie_service.set_session_cookie(response, issued.session_token, settings)

    record_audit_event(
        db=db,
        event_type="AUTH_LOGIN_SUCCESS",
        resource_type="auth_session",
        resource_id=issued.session_id,
        actor_user_id=user.id,
        correlation_id=correlation_id,
    )
    db.commit()

    return {
        "data": {
            "user": UserProfileResponse.model_validate(user),
            "csrf_token": issued.csrf_token,
            "session_token": issued.session_token,
        }
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    session_service.revoke_session(db, principal.session_id, reason="logout")
    cookie_service.clear_session_cookie(response, settings)

    record_audit_event(
        db=db,
        event_type="AUTH_LOGOUT",
        resource_type="auth_session",
        resource_id=principal.session_id,
        actor_user_id=principal.user_id,
        correlation_id=get_correlation_id(request),
    )
    db.commit()

    return {"data": {"message": "Logged out successfully."}}


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user_orgs = list_user_organizations(db, current_user.id)
    org_summaries = [
        {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "role": membership.role.value,
        }
        for org, membership in user_orgs
    ]

    return {
        "data": {
            "user": UserProfileResponse.model_validate(current_user),
            "organizations": org_summaries,
        }
    }


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    normalized = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.normalized_email == normalized))
    if user is not None and user.status == AccountStatus.ACTIVE:
        issued = token_service.create_token(
            db=db,
            user_id=user.id,
            purpose=TokenPurpose.PASSWORD_RESET,
            settings=settings,
        )
        email_provider = get_email_provider(settings)
        email_provider.send_password_reset_email(
            email=user.email,
            token=issued.raw_token,
            user_name=user.full_name,
        )
        record_audit_event(
            db=db,
            event_type="AUTH_PASSWORD_RESET_REQUESTED",
            resource_type="user",
            resource_id=user.id,
            correlation_id=get_correlation_id(request),
        )
        db.commit()

    return {
        "data": {
            "message": "If your email is registered, instructions to reset your password have been sent."
        }
    }


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    consumed = token_service.consume_token(
        db=db, raw_token=payload.token, purpose=TokenPurpose.PASSWORD_RESET
    )
    if consumed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    user = db.get(User, consumed.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

    # Update password and revoke all existing sessions
    user.password_hash = password_service.hash_password(payload.new_password, settings)
    session_service.revoke_all_user_sessions(db, user.id, reason="password-reset")
    db.flush()

    record_audit_event(
        db=db,
        event_type="AUTH_PASSWORD_RESET_COMPLETED",
        resource_type="user",
        resource_id=user.id,
        correlation_id=get_correlation_id(request),
    )
    db.commit()

    return {
        "data": {
            "message": "Password has been successfully reset. Please log in with your new credentials."
        }
    }


@router.get("/sessions")
def get_user_sessions(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.now(UTC)
    stmt = (
        select(AuthSession)
        .where(
            AuthSession.user_id == principal.user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_activity_at.desc())
    )
    sessions = db.scalars(stmt).all()

    results = [
        SessionInfoResponse(
            id=s.id,
            created_at=s.created_at,
            last_activity_at=s.last_activity_at,
            expires_at=s.expires_at,
            is_current=(s.id == principal.session_id),
        )
        for s in sessions
    ]

    return {"data": results}


@router.delete("/sessions/{session_id}", dependencies=[Depends(require_csrf)])
def revoke_session(
    session_id: str,
    response: Response,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    target = db.get(AuthSession, session_id)
    if target is None or target.user_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    session_service.revoke_session(db, target.id, reason="user_revoked")
    if target.id == principal.session_id:
        cookie_service.clear_session_cookie(response, settings)

    record_audit_event(
        db=db,
        event_type="AUTH_SESSION_REVOKED",
        resource_type="auth_session",
        resource_id=target.id,
        actor_user_id=principal.user_id,
        correlation_id=get_correlation_id(request),
    )
    db.commit()

    return {"data": {"message": "Session revoked."}}


@router.post("/rotate-session", dependencies=[Depends(require_csrf)])
def rotate_session(
    request: Request,
    response: Response,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    raw_token, _ = extract_session_token(request, settings)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Session token required.")

    rotated = session_service.rotate_session(db, raw_token, settings)
    if rotated is None:
        raise HTTPException(status_code=401, detail="Session could not be rotated.")

    cookie_service.set_session_cookie(response, rotated.session_token, settings)
    return {"data": {"csrf_token": rotated.csrf_token}}
