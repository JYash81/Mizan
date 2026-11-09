# M2 Block 1 — Step 3 report

## Implemented

Migration `20261108_0003_session_csrf` adds the nullable, unique CSRF digest needed to preserve existing session rows. The session service creates hashed opaque credentials, validates absolute/idle expiration, supports revocation, user-wide revocation, rotation, cleanup, and CSRF validation. Cookie helpers consistently set/clear HttpOnly cookies.

## Verification

`alembic upgrade head` passed. `ruff check .` passed. `pytest -q` passed: **21 tests**, with one existing upstream FastAPI/Starlette deprecation warning.

## Limitations

MySQL/MariaDB and true concurrent rotation behavior have not been integration-tested. A dedicated test-connection attempt using `localhost` was refused because no MySQL service is listening on the local development machine; Hostinger's local hostname is not reachable from this machine. Rotation was hardened with an atomic conditional revoke plus replacement insert in a nested transaction, but production-concurrency verification remains pending. No routes, authentication dependency, login/logout, token service, or Block 2 capability was added.
