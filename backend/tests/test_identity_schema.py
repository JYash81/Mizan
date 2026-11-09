import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.identity import AuditEvent, AuthSession, AuthToken, TokenPurpose, User


def user() -> User:
    return User(
        full_name="Mizan User",
        email="user@example.test",
        normalized_email="user@example.test",
        password_hash="not-a-password",
    )


def test_identity_models_are_registered() -> None:
    assert {"users", "auth_sessions", "auth_tokens", "audit_events"} <= set(Base.metadata.tables)


def test_constraints_and_audit_safety() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = user()
        db.add(first)
        db.commit()
        db.add(user())
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(
            AuthSession(user_id=first.id, session_token_hash="a" * 64, expires_at=first.created_at)
        )
        db.commit()
        db.add(
            AuthSession(user_id=first.id, session_token_hash="a" * 64, expires_at=first.created_at)
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(
            AuthToken(
                user_id=first.id,
                token_hash="b" * 64,
                purpose=TokenPurpose.EMAIL_VERIFICATION,
                expires_at=first.created_at,
            )
        )
        db.commit()
        with pytest.raises(ValueError):
            AuditEvent(event_type="LOGIN", resource_type="user", safe_metadata={"token": "never"})
        with pytest.raises(ValueError):
            AuditEvent(
                event_type="LOGIN",
                resource_type="user",
                safe_metadata={"context": {"access_token": "never"}},
            )
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        with pytest.raises(Exception):
            connection.exec_driver_sql(
                "INSERT INTO auth_sessions (id, user_id, session_token_hash, last_activity_at, expires_at) VALUES ('bad', 'missing', 'c', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )


def test_disposable_migration_round_trip(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    env = {**__import__("os").environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}"}
    root = Path(__file__).parents[1]
    for command in ("upgrade", "downgrade", "upgrade"):
        target = "head" if command == "upgrade" else "20261108_0001"
        subprocess.run(
            [sys.executable, "-m", "alembic", command, target], cwd=root, env=env, check=True
        )
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type='table'")
        }
        indexes = {
            row[1]
            for table in ("users", "auth_sessions", "auth_tokens", "audit_events")
            for row in connection.execute(f"PRAGMA index_list({table})")
        }
    assert {"users", "auth_sessions", "auth_tokens", "audit_events"} <= tables
    assert {
        "ix_users_normalized_email",
        "ix_auth_sessions_session_token_hash",
        "ix_auth_tokens_token_hash",
    } <= indexes
