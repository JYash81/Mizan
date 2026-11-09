from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.db.session import check_database_connection

router = APIRouter(tags=["System"])


def success(data: dict) -> dict:
    return {"data": data}


@router.get("/health")
def health() -> dict:
    return success({"status": "ok", "timestamp": datetime.now(UTC).isoformat()})


@router.get("/ready")
def ready() -> dict:
    try:
        check_database_connection()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Database is unavailable.") from error
    return success({"status": "ready", "database": "connected"})


@router.get("/version")
def version() -> dict:
    settings = get_settings()
    return success(
        {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        }
    )


@router.get("/system/info")
def system_info() -> dict:
    settings = get_settings()
    return success(
        {"api_version": "v1", "environment": settings.app_env, "capabilities": ["foundation"]}
    )
