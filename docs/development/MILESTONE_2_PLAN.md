# Milestone 2 implementation plan

1. Add a migration-safe identity schema: users, sessions, one-time tokens, and append-only audit events. **Step 1 complete and verified on SQLite.** Organizations, memberships, workspaces, and invitations remain later work.
2. Add Argon2id password hashing, verification, policy validation, and rehash detection. **Step 2 complete and verified.**
3. Add opaque server-side session and CSRF foundations. **Step 3 implemented and SQLite-tested; production concurrency remains unverified.**
2. Add Argon2id credentials, hashed opaque sessions, CSRF protection, development-only email sink, and one-time verification/reset/invitation tokens.
3. Add centralized tenant and permission dependencies before exposing organization or workspace routes.
4. Add registration/login/recovery/onboarding and workspace-management screens, then expand tests with isolation and revocation cases.

Milestone 1 verification completed before this plan: backend tests/migration/Ruff and frontend lint/typecheck/Vitest/build passed.
