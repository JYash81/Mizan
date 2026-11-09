# M2 Block 1 — Step 1 report

## Implemented

- Identity models registered through `app.models` before Alembic reads `Base.metadata`.
- Incremental migration `20261108_0002_identity_foundation` creates identity tables, constraints, indexes, and foreign keys; downgrade removes only those new tables.
- Disposable SQLite migration test upgrades, downgrades to the baseline, then upgrades again.
- Tests cover metadata registration, unique email/session/token hashes, foreign-key enforcement, enum representation, audit metadata secret-key rejection, and existing API checks.

## Verification

`pytest -q`: 7 passed (one existing upstream FastAPI/Starlette deprecation warning). SQLite migration round-trip passed. Ruff is run after final formatting. MySQL/MariaDB compatibility is designed for portable SQLAlchemy types but remains unverified without an integration database.

## Deferred

Password/session/token service behavior, authentication dependency, and audit service are later Block 1 steps. No Block 2 functionality was added.
