"""REST API endpoints for Customer Site Management and Administration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import Workspace
from app.models.runtime import RuntimeApplication
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.runtime.exceptions import (
    DuplicateSiteKeyError,
    HardwarePreflightFailedError,
    PackageNotApprovedError,
    PackageVerificationError,
    SiteNotFoundError,
    SiteSuspendedOrRevokedError,
    UnallowlistedCommandError,
)
from app.modules.runtime.package_installer_service import verify_and_install_package
from app.modules.runtime.schemas import (
    AgentCommandCreate,
    AgentCommandRead,
    CustomerSiteCreate,
    CustomerSiteRead,
    EnrollmentTokenCreateResponse,
    RuntimeApplicationRead,
)
from app.modules.runtime.site_agent_service import issue_agent_command
from app.modules.runtime.site_service import (
    create_customer_site,
    generate_enrollment_token,
    get_customer_site_read,
    list_customer_sites,
    revoke_customer_site,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/sites", tags=["Customer Sites"])


class InstallPackageRequest(BaseModel):
    """Request schema to install an approved model and application into a customer site."""

    app_version_id: str = Field(..., min_length=1)
    model_version_id: str = Field(..., min_length=1)


def _verify_workspace(db: Session, workspace_id: str) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws


@router.post(
    "",
    response_model=CustomerSiteRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf), Depends(require_ws_permission(WorkspacePermission.SITES_MANAGE))],
)
def register_customer_site_endpoint(
    workspace_id: str,
    payload: CustomerSiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CustomerSiteRead:
    """Register a new customer deployment site."""
    ws = _verify_workspace(db, workspace_id)
    try:
        return create_customer_site(
            db=db,
            organization_id=ws.organization_id,
            workspace_id=workspace_id,
            payload=payload,
            user_id=current_user.id,
        )
    except DuplicateSiteKeyError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.get(
    "",
    response_model=list[CustomerSiteRead],
    dependencies=[Depends(require_ws_permission(WorkspacePermission.SITES_READ))],
)
def list_customer_sites_endpoint(
    workspace_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> list[CustomerSiteRead]:
    """List customer deployment sites in a workspace."""
    _verify_workspace(db, workspace_id)
    return list_customer_sites(db, workspace_id)


@router.get(
    "/{site_id}",
    response_model=CustomerSiteRead,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.SITES_READ))],
)
def get_customer_site_endpoint(
    workspace_id: str,
    site_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> CustomerSiteRead:
    """Get customer deployment site details."""
    _verify_workspace(db, workspace_id)
    try:
        return get_customer_site_read(db, site_id, workspace_id)
    except SiteNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post(
    "/{site_id}/enrollment-token",
    response_model=EnrollmentTokenCreateResponse,
    dependencies=[Depends(require_csrf), Depends(require_ws_permission(WorkspacePermission.SITES_MANAGE))],
)
def generate_enrollment_token_endpoint(
    workspace_id: str,
    site_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EnrollmentTokenCreateResponse:
    """Generate a single-use, high-entropy token for enrolling a site agent."""
    _verify_workspace(db, workspace_id)
    try:
        return generate_enrollment_token(
            db=db,
            site_id=site_id,
            user_id=current_user.id,
            workspace_id=workspace_id,
        )
    except SiteNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except SiteSuspendedOrRevokedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.post(
    "/{site_id}/revoke",
    response_model=CustomerSiteRead,
    dependencies=[Depends(require_csrf), Depends(require_ws_permission(WorkspacePermission.SITES_MANAGE))],
)
def revoke_customer_site_endpoint(
    workspace_id: str,
    site_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CustomerSiteRead:
    """Revoke customer site and terminate all agent credentials."""
    _verify_workspace(db, workspace_id)
    try:
        return revoke_customer_site(db, site_id, workspace_id)
    except SiteNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post(
    "/{site_id}/commands",
    response_model=AgentCommandRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf), Depends(require_ws_permission(WorkspacePermission.SITES_MANAGE))],
)
def issue_agent_command_endpoint(
    workspace_id: str,
    site_id: str,
    payload: AgentCommandCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> AgentCommandRead:
    """Dispatch an allowlisted, cryptographically signed command to a site agent."""
    _verify_workspace(db, workspace_id)
    try:
        return issue_agent_command(db=db, customer_site_id=site_id, payload=payload)
    except SiteNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except SiteSuspendedOrRevokedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    except UnallowlistedCommandError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get(
    "/{site_id}/applications",
    response_model=list[RuntimeApplicationRead],
    dependencies=[Depends(require_ws_permission(WorkspacePermission.SITES_READ))],
)
def list_site_applications_endpoint(
    workspace_id: str,
    site_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> list[RuntimeApplicationRead]:
    """List applications installed at a customer site."""
    _verify_workspace(db, workspace_id)
    apps = (
        db.execute(
            select(RuntimeApplication)
            .where(RuntimeApplication.customer_site_id == site_id)
            .order_by(RuntimeApplication.installed_at.desc())
        )
        .scalars()
        .all()
    )
    return [RuntimeApplicationRead.model_validate(app) for app in apps]


@router.post(
    "/{site_id}/install-package",
    response_model=RuntimeApplicationRead,
    dependencies=[Depends(require_csrf), Depends(require_ws_permission(WorkspacePermission.SITES_MANAGE))],
)
def install_package_endpoint(
    workspace_id: str,
    site_id: str,
    payload: InstallPackageRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> RuntimeApplicationRead:
    """Verify Gate 3 attestation and install application package into site."""
    _verify_workspace(db, workspace_id)
    try:
        app = verify_and_install_package(
            db=db,
            customer_site_id=site_id,
            app_version_id=payload.app_version_id,
            model_version_id=payload.model_version_id,
        )
        return RuntimeApplicationRead.model_validate(app)
    except SiteNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except PackageNotApprovedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    except PackageVerificationError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    except HardwarePreflightFailedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
