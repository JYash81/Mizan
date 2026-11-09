"""REST API endpoints for Site Agent protocol communication."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.runtime.exceptions import (
    AgentIdentityRevokedError,
    AgentNotEnrolledError,
    EnrollmentTokenAlreadyConsumedError,
    EnrollmentTokenExpiredError,
    ExpiredCommandError,
    InvalidEnrollmentTokenError,
    InvalidSignatureError,
    ReplayedNonceError,
    SiteNotFoundError,
    SiteSuspendedOrRevokedError,
)
from app.modules.runtime.schemas import (
    AgentCommandConsumeRequest,
    AgentCommandRead,
    SiteAgentEnrollRequest,
    SiteAgentEnrollResponse,
    SiteAgentHeartbeatRequest,
    SiteAgentHeartbeatResponse,
)
from app.modules.runtime.site_agent_service import (
    consume_agent_command,
    poll_pending_commands,
)
from app.modules.runtime.site_service import (
    enroll_site_agent,
    report_agent_heartbeat,
)

router = APIRouter(prefix="/site-agent", tags=["Site Agent Protocol"])


@router.post(
    "/enroll",
    response_model=SiteAgentEnrollResponse,
    status_code=status.HTTP_201_CREATED,
)
def enroll_agent_endpoint(
    payload: SiteAgentEnrollRequest,
    db: Session = Depends(get_db),
) -> SiteAgentEnrollResponse:
    """Agent enrollment endpoint presenting single-use token and public key."""
    try:
        return enroll_site_agent(db, payload)
    except InvalidEnrollmentTokenError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)) from err
    except (EnrollmentTokenAlreadyConsumedError, EnrollmentTokenExpiredError) as err:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(err)) from err
    except SiteNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except SiteSuspendedOrRevokedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


@router.post(
    "/heartbeat",
    response_model=SiteAgentHeartbeatResponse,
)
def heartbeat_endpoint(
    payload: SiteAgentHeartbeatRequest,
    db: Session = Depends(get_db),
) -> SiteAgentHeartbeatResponse:
    """Outbound periodic agent heartbeat sending status and receiving pending command counter."""
    try:
        return report_agent_heartbeat(db, payload)
    except AgentNotEnrolledError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)) from err
    except AgentIdentityRevokedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
    except SiteSuspendedOrRevokedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


@router.get(
    "/{site_id}/commands",
    response_model=list[AgentCommandRead],
)
def poll_commands_endpoint(
    site_id: str,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    db: Session = Depends(get_db),
) -> list[AgentCommandRead]:
    """Outbound poll endpoint for Site Agent to retrieve pending signed commands."""
    try:
        return poll_pending_commands(db=db, customer_site_id=site_id, agent_id=x_agent_id)
    except AgentNotEnrolledError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)) from err
    except AgentIdentityRevokedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


@router.post(
    "/{site_id}/commands/{command_id}/consume",
    response_model=dict[str, Any],
)
def consume_command_endpoint(
    site_id: str,
    command_id: str,
    payload: AgentCommandConsumeRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Acknowledge execution and consume signed agent command."""
    if payload.command_id != command_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload command_id does not match route path command_id.",
        )
    try:
        return consume_agent_command(
            db=db,
            customer_site_id=site_id,
            agent_id=x_agent_id,
            payload=payload,
        )
    except AgentNotEnrolledError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)) from err
    except ReplayedNonceError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except ExpiredCommandError as err:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(err)) from err
    except InvalidSignatureError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)) from err
