from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    is_prod = settings.app_env.lower() == "production"

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )

    @app.middleware("http")
    async def add_security_headers_middleware(request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if is_prod:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # The web client uses HttpOnly session cookies.  Credentialed browser
        # requests require this explicit CORS opt-in; `Settings` rejects a
        # wildcard origin in production, so the allowlist remains authoritative.
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-XSRF-Token"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"status": "ok", "service": "Mizan API", "version": settings.app_version}

    app.include_router(router)
    register_exception_handlers(app)
    return app


app = create_app()
