from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mizan"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "replace-with-local-secret"
    database_url: str = "sqlite:///./storage/development/mizan.db"
    cors_origins: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://llmguru.hennt.in",
        "http://llmguru.hennt.in",
        "https://hennt.in",
        "http://hennt.in",
    ]
    cors_origin_regex: str | None = r"^https?://(localhost|127\.0\.0\.1|.*\.hennt\.in|hennt\.in)(:[0-9]+)?$"
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 19456
    argon2_parallelism: int = 1
    argon2_hash_length: int = 32
    argon2_salt_length: int = 16
    session_absolute_minutes: int = 720
    session_idle_minutes: int = 30
    session_activity_update_minutes: int = 5
    session_retention_days: int = 30
    email_verification_token_hours: int = 24
    password_reset_token_minutes: int = 15
    token_retention_days: int = 30
    session_cookie_name: str = "mizan_session"
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    session_cookie_path: str = "/"
    session_cookie_domain: str | None = None
    storage_backend: str = "local"
    storage_local_root: str = "./storage/data_plane"
    storage_max_upload_size_bytes: int = 25 * 1024 * 1024
    storage_s3_endpoint_url: str | None = None
    storage_s3_bucket: str | None = None
    storage_s3_access_key: str | None = None
    storage_s3_secret_key: str | None = None
    storage_s3_region: str = "auto"
    signing_keys_dir: str = "./storage/keys"
    default_signing_key_id: str = "mizan-platform-dev-01"
    # Mandatory Free-Only Cost Policy Configuration
    allow_paid_providers: bool = False
    allow_billable_external_compute: bool = False
    allow_paid_storage: bool = False
    allow_paid_embedding_apis: bool = False
    allow_automatic_billing: bool = False
    allow_paid_compute: bool = False
    allow_paid_gpu: bool = False
    allow_automatic_cloud_provisioning: bool = False
    # Vector Database & Embeddings Configuration
    qdrant_path: str = "./storage/development/qdrant"
    fastembed_cache_dir: str = "./storage/models/fastembed"
    fastembed_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # AI Providers Configuration
    default_llm_provider: str = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    # Email & SMTP Configuration
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@mizan.ai"
    smtp_from_name: str = "Mizan Platform"
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    frontend_url: str = "http://localhost:5173"
    # HTTPS Mail Relay Configuration (for cloud environments where outbound SMTP ports are blocked)
    mail_relay_url: str | None = None
    mail_relay_secret: str = "mizan-secure-mail-relay-key-2026-safe"
    # Dedicated Prometheus Scrape Token for authenticated monitoring scrapers
    prometheus_scrape_token: str | None = None
    # Platform Operator / Super-admin allowlist for cross-tenant operations access
    platform_operator_emails: list[str] | str = []
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("platform_operator_emails", mode="before")
    @classmethod
    def split_operator_emails(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(e).strip().lower() for e in parsed if str(e).strip()]
            except Exception:
                pass
            return [x.strip().lower() for x in value.split(",") if x.strip()]
        if isinstance(value, list):
            return [str(x).strip().lower() for x in value if str(x).strip()]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except Exception:
                pass
            return [x.strip() for x in value.split(",") if x.strip()]
        return value

    @property
    def database_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @model_validator(mode="after")
    def validate_argon2_settings(self) -> Settings:
        minimums = {
            "argon2_time_cost": 2,
            "argon2_memory_cost": 19456,
            "argon2_parallelism": 1,
            "argon2_hash_length": 32,
            "argon2_salt_length": 16,
        }
        for name, minimum in minimums.items():
            if getattr(self, name) < minimum:
                raise ValueError(f"{name} cannot be less than {minimum}.")
        if not self.session_cookie_httponly:
            raise ValueError("Session cookies must be HttpOnly.")
        if self.session_cookie_samesite.lower() == "none" and not self.session_cookie_secure:
            raise ValueError("SameSite=None requires Secure cookies.")

        # Production Hardening Validations (Phase 10 / Phase 15 / Post-Deployment Remediation)
        # Note: Minimum length (>= 32 characters) is a necessary syntactic baseline but is NOT
        # equivalent to true cryptographic entropy. A repetitive 32-character string (e.g. 32 'a's)
        # has negligible Shannon entropy. Production secrets MUST be independently generated using
        # a cryptographically secure pseudorandom number generator (CSPRNG), e.g. `openssl rand -hex 32`
        # or `python -c "import secrets; print(secrets.token_hex(32))"`, providing at least 256 bits of entropy.
        if self.app_env.lower() == "production":
            if not self.session_cookie_secure:
                raise ValueError("Production session cookies must be Secure.")
            if self.debug:
                raise ValueError("Production environment cannot run with debug=True.")
            insecure_defaults = {
                "replace-with-local-secret",
                "",
                "secret",
                "changeme",
                "development-secret-key-32-chars-long",
                "mizan-dev-secret-key-do-not-use-in-prod",
            }
            if self.secret_key.strip() in insecure_defaults or len(self.secret_key.strip()) < 32:
                raise ValueError(
                    "Production secret_key must be configured with a high-entropy secret (at least 32 characters)."
                )
            if "*" in self.cors_origins:
                raise ValueError("Production environment cannot allow wildcard CORS origins ('*').")
        return self


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_argon2_settings()
    if settings.database_is_sqlite:
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(
            parents=True, exist_ok=True
        )
    return settings
