# Milestone 2 Block 2 Implementation Plan
## Complete Authentication, Organization Management, Workspace Management, Multi-Tenancy & RBAC

**Author:** Principal Software Architect & Engineering Team  
**Date:** 2026-11-08  
**Scope:** Milestone 2, Block 2 — Multi-tenant organization and workspace infrastructure, full authentication API suite, email notification engine, invitation lifecycle, centralized RBAC engine, frontend authentication and workspace management flows.

---

## 1. Baseline Architecture & Audit

### 1.1 Existing Implementations (Verified Baseline)
- **FastAPI Core (`backend/app/core/`):** Centralized Pydantic `Settings`, CORS middleware, structured JSON exception handling for validation, SQLAlchemy, Starlette HTTP errors, and unhandled exceptions.
- **Identity Foundation (`backend/app/models/identity.py`):** `User`, `AuthSession`, `AuthToken`, and `AuditEvent` models with strict secret rejection validators on audit metadata.
- **Security Services (`backend/app/modules/auth/services/`):**
  - `password_service.py`: Argon2id password hashing, verification, length (12–128) and UTF-8 size policies, rehash detection.
  - `session_service.py`: Opaque token generation, SHA-256 digest persistence, idle (30m) and absolute (12h) expiration, atomic rotation with rollback savepoints, user-wide revocation.
  - `token_service.py`: Opaque one-time verification and password reset tokens, SHA-256 digests, atomic single-use conditional updates (`UPDATE ... WHERE consumed_at IS NULL AND revoked_at IS NULL`), purpose scoping.
  - `cookie_service.py`: Setting and clearing HttpOnly session cookies.
- **Dependencies & Audit (`backend/app/modules/auth/dependencies.py`, `backend/app/modules/audit/services/`):**
  - `extract_session_token`, `get_current_principal`, `get_current_active_user`, `require_csrf`.
  - `record_audit_event` with recursive secret scrubbing (`sanitize_metadata`).
- **Database Migrations:** Baseline `0001`, identity `0002`, and session CSRF `0003` applied.
- **Frontend Foundation (`frontend/src/`):** React 19, Vite, TypeScript, React Router, TanStack Query, Tailwind CSS, responsive shell, and base API client.
- **Test Baseline:** 37 backend tests passing; Vitest, ESLint, and Vite build passing.

### 1.2 Missing Functionality to Implement in Block 2
1. **Multi-Tenant Data Models & Migrations:** `Organization`, `OrganizationMembership`, `Workspace`, `WorkspaceMembership`, `Invitation`.
2. **Email Provider Abstraction:** Local development email sink (with non-leaking logs and inspection endpoint/queue) and production interface.
3. **Authentication Endpoints:** Registration, email verification, resend verification, login, session inspection/revocation/rotation, logout, forgot password, reset password, and user profile (`/auth/me`).
4. **Organization & Workspace Repositories and Services:** Full lifecycle (create, read, update, archive, membership assignment, role updates, member removal, and safe ownership transfer).
5. **Centralized RBAC & Tenant-Isolation Engine:** Declarative permissions, organization roles (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`), workspace roles (`WORKSPACE_OWNER`, `WORKSPACE_ADMIN`, `WORKSPACE_MEMBER`, `WORKSPACE_VIEWER`), tenant resolution dependencies, and cross-tenant access rejection.
6. **Invitation Subsystem:** High-entropy invitation tokens, SHA-256 hashing, expiration, email matching, atomic acceptance, and membership creation.
7. **Frontend User Flows:**
   - Registration, login, email verification notice/entry, forgot password, reset password.
   - Organization onboarding wizard (first organization and first workspace).
   - Global workspace switcher in the header with cache invalidation on tenant switch.
   - Team and invitation management views.
   - Profile and security session management views.

---

## 2. Database Design & Entity Architecture

We will introduce migration `20261108_0004_organizations_and_workspaces` with the following entities:

```
┌─────────────────┐       ┌──────────────────────────────┐       ┌─────────────────┐
│      User       │       │    OrganizationMembership    │       │  Organization   │
├─────────────────┤       ├──────────────────────────────┤       ├─────────────────┤
│ id (PK, UUID)   │◄──────┤ user_id (FK, Index)          │   ┌───┤ id (PK, UUID)   │
│ full_name       │       │ organization_id (FK, Index)  ├───┘   │ name            │
│ email           │       │ role (Enum: OWNER..VIEWER)   │       │ slug (Unique)   │
│ status          │       │ membership_status (Enum)     │       │ description     │
│ password_hash   │       │ created_at, updated_at       │       │ created_by (FK) │
└────────┬────────┘       └──────────────────────────────┘       │ status (Enum)   │
         │                                                       └────────┬────────┘
         │                ┌──────────────────────────────┐                │
         │                │     WorkspaceMembership      │                │
         │                ├──────────────────────────────┤                │
         ├───────────────►│ user_id (FK, Index)          │                │
         │                │ workspace_id (FK, Index)     ├───┐            │
         │                │ role (Enum: OWNER..VIEWER)   │   │            ▼
         │                │ membership_status (Enum)     │   │   ┌─────────────────┐
         │                │ created_at, updated_at       │   │   │    Workspace    │
         │                └──────────────────────────────┘   │   ├─────────────────┤
         │                                                   └──►│ id (PK, UUID)   │
         │                ┌──────────────────────────────┐       │ organization_id │
         │                │          Invitation          │       │ name            │
         │                ├──────────────────────────────┤       │ slug            │
         │                │ id (PK, UUID)                │       │ description     │
         │                │ organization_id (FK, Index)  ├──────►│ created_by (FK) │
         └───────────────►│ invited_by (FK)              │       │ status (Enum)   │
                          │ email / normalized_email     │       └─────────────────┘
                          │ token_hash (Unique, Index)   │
                          │ role / workspace_id / ws_role│
                          │ status / expires_at          │
                          └──────────────────────────────┘
```

### Table Specifications
1. **`organizations`:**
   - `id`: `String(36)`, PK (UUIDv4)
   - `name`: `String(255)`, Not Null
   - `slug`: `String(100)`, Unique, Indexed
   - `description`: `Text`, Nullable
   - `created_by`: `String(36)`, FK `users.id`, Index
   - `status`: `Enum(OrganizationStatus: ACTIVE, SUSPENDED, ARCHIVED)`, Default `ACTIVE`
   - `created_at`, `updated_at`: `DateTime(timezone=True)`
2. **`organization_memberships`:**
   - `id`: `String(36)`, PK (UUIDv4)
   - `organization_id`: `String(36)`, FK `organizations.id`, Index
   - `user_id`: `String(36)`, FK `users.id`, Index
   - `role`: `Enum(OrganizationRole: OWNER, ADMIN, MEMBER, VIEWER)`, Default `MEMBER`
   - `membership_status`: `Enum(MembershipStatus: ACTIVE, SUSPENDED)`, Default `ACTIVE`
   - `invited_by`: `String(36)`, FK `users.id`, Nullable
   - `created_at`, `updated_at`: `DateTime(timezone=True)`
   - *Constraint:* Unique `(organization_id, user_id)`
3. **`workspaces`:**
   - `id`: `String(36)`, PK (UUIDv4)
   - `organization_id`: `String(36)`, FK `organizations.id`, Index
   - `name`: `String(255)`, Not Null
   - `slug`: `String(100)`, Index
   - `description`: `Text`, Nullable
   - `created_by`: `String(36)`, FK `users.id`, Index
   - `status`: `Enum(WorkspaceStatus: ACTIVE, ARCHIVED)`, Default `ACTIVE`
   - `created_at`, `updated_at`: `DateTime(timezone=True)`
   - *Constraint:* Unique `(organization_id, slug)`
4. **`workspace_memberships`:**
   - `id`: `String(36)`, PK (UUIDv4)
   - `workspace_id`: `String(36)`, FK `workspaces.id`, Index
   - `user_id`: `String(36)`, FK `users.id`, Index
   - `role`: `Enum(WorkspaceRole: WORKSPACE_OWNER, WORKSPACE_ADMIN, WORKSPACE_MEMBER, WORKSPACE_VIEWER)`
   - `membership_status`: `Enum(MembershipStatus: ACTIVE, SUSPENDED)`, Default `ACTIVE`
   - `created_at`, `updated_at`: `DateTime(timezone=True)`
   - *Constraint:* Unique `(workspace_id, user_id)`
5. **`invitations`:**
   - `id`: `String(36)`, PK (UUIDv4)
   - `organization_id`: `String(36)`, FK `organizations.id`, Index
   - `workspace_id`: `String(36)`, FK `workspaces.id`, Nullable, Index
   - `invited_email`: `String(320)`, Not Null
   - `normalized_email`: `String(320)`, Index
   - `token_hash`: `String(64)`, Unique, Index
   - `organization_role`: `Enum(OrganizationRole)`
   - `workspace_role`: `Enum(WorkspaceRole)`, Nullable
   - `invited_by`: `String(36)`, FK `users.id`, Index
   - `status`: `Enum(InvitationStatus: PENDING, ACCEPTED, REJECTED, REVOKED, EXPIRED)`
   - `expires_at`: `DateTime(timezone=True)`
   - `accepted_at`: `DateTime(timezone=True)`, Nullable
   - `revoked_at`: `DateTime(timezone=True)`, Nullable
   - `created_at`: `DateTime(timezone=True)`

---

## 3. Authorization & Centralized RBAC Engine

### 3.1 Permission Matrix
| Role | Permissions |
| :--- | :--- |
| **Org OWNER** | `organization.read`, `organization.update`, `organization.archive`, `organization.members.read`, `organization.members.invite`, `organization.members.manage`, `organization.owner.transfer`, `organization.workspaces.create`, `organization.workspaces.manage` (Plus inherited full access to all child workspaces). |
| **Org ADMIN** | `organization.read`, `organization.update`, `organization.members.read`, `organization.members.invite`, `organization.members.manage`, `organization.workspaces.create`, `organization.workspaces.manage`. (Cannot remove or demote OWNER; cannot transfer ownership). |
| **Org MEMBER** | `organization.read`, `organization.members.read`. (Workspace operations governed by workspace role). |
| **Org VIEWER** | `organization.read`, `organization.members.read`. (Read-only access across assigned workspaces). |
| **Workspace OWNER** | `workspace.read`, `workspace.update`, `workspace.archive`, `workspace.members.read`, `workspace.members.manage`, `workspace.datasets.*`, `workspace.experiments.*`. |
| **Workspace ADMIN** | `workspace.read`, `workspace.update`, `workspace.members.read`, `workspace.members.manage`, `workspace.datasets.*`, `workspace.experiments.*`. |
| **Workspace MEMBER** | `workspace.read`, `workspace.members.read`, `workspace.datasets.read`, `workspace.datasets.create`, `workspace.experiments.read`, `workspace.experiments.create`. |
| **Workspace VIEWER** | `workspace.read`, `workspace.members.read`, `workspace.datasets.read`, `workspace.experiments.read`. |

### 3.2 Tenant Isolation Guarantees
- Every tenant resource query filters explicitly by `organization_id` (and `workspace_id`).
- Tenant resolution dependencies:
  - `get_current_organization(organization_id, user, db)`: Validates active membership; raises 404 or 403.
  - `get_current_workspace(workspace_id, organization, user, db)`: Validates workspace belongs to the organization and user has permission.
  - `require_organization_permission(permission)`: Factory checking role-to-permission mapping.
  - `require_workspace_permission(permission)`: Factory checking workspace role (with Org Owner bypass).
- Cross-tenant requests return 404 Not Found to prevent tenant data/existence enumeration.

---

## 4. API Endpoints Specification

### Authentication Routes (`/api/v1/auth`)
- `POST /register`: Accepts name, email, password, terms; creates User in `PENDING_VERIFICATION`, generates verification token, dispatches email via EmailProvider.
- `POST /verify-email`: Consumes token, activates user, returns success.
- `POST /resend-verification`: Issues replacement token with rate limiting.
- `POST /login`: Verifies Argon2id password, creates opaque session, issues HttpOnly cookie and CSRF token.
- `POST /logout`: Revokes session, clears cookie.
- `GET /me`: Returns sanitized user profile, active memberships, and organization summary.
- `POST /forgot-password`: Issues password reset token (neutral 200 response to prevent enumeration).
- `POST /reset-password`: Consumes reset token, validates new password policy, updates hash, revokes existing sessions.
- `GET /sessions`: Lists active sessions with timestamps and current-session indicator.
- `DELETE /sessions/{session_id}`: Revokes target session.
- `POST /rotate-session`: Rotates current session token.

### Organization Routes (`/api/v1/organizations`)
- `POST /`: Creates organization with unique slug; adds creator as `OWNER`.
- `GET /`: Lists organizations where current user has active membership.
- `GET /{organization_id}`: Gets organization details.
- `PATCH /{organization_id}`: Updates name/description (requires `organization.update`).
- `POST /{organization_id}/archive`: Archives organization (requires `organization.archive`).
- `GET /{organization_id}/members`: Lists organization members and roles.
- `PATCH /{organization_id}/members/{user_id}`: Updates member role (cannot modify OWNER unless transferring).
- `DELETE /{organization_id}/members/{user_id}`: Removes member (prevents removing last OWNER).
- `POST /{organization_id}/transfer-ownership`: Transfers OWNER to an existing active member.

### Workspace Routes (`/api/v1/organizations/{organization_id}/workspaces` & `/api/v1/workspaces`)
- `POST /organizations/{org_id}/workspaces`: Creates workspace under target organization; adds creator as `WORKSPACE_OWNER`.
- `GET /organizations/{org_id}/workspaces`: Lists accessible workspaces within organization.
- `GET /workspaces/{workspace_id}`: Gets workspace details.
- `PATCH /workspaces/{workspace_id}`: Updates workspace name/description.
- `POST /workspaces/{workspace_id}/archive`: Archives workspace.
- `GET /workspaces/{workspace_id}/members`: Lists workspace members.
- `POST /workspaces/{workspace_id}/members`: Adds org member to workspace with assigned role.
- `PATCH /workspaces/{workspace_id}/members/{user_id}`: Updates workspace role.
- `DELETE /workspaces/{workspace_id}/members/{user_id}`: Removes member from workspace.

### Invitation Routes (`/api/v1/organizations/{organization_id}/invitations` & `/api/v1/invitations`)
- `POST /organizations/{org_id}/invitations`: Creates invitation with secure token; sends invitation email.
- `GET /organizations/{org_id}/invitations`: Lists pending invitations for organization.
- `DELETE /invitations/{invitation_id}`: Revokes pending invitation.
- `POST /invitations/accept`: Authenticated user consumes token; verifies email matches; creates memberships.
- `POST /invitations/reject`: Marks invitation rejected.

---

## 5. Frontend User Experience & Workflows

1. **Authentication Screens:**
   - `/login`: Email + password form with show/hide password, error banners, link to forgot password and registration.
   - `/register`: Full name, email, password strength indicator, terms checkbox, success state directing to verification.
   - `/verify-email`: Direct link token consumption with auto-verification and resend option.
   - `/forgot-password`: Email entry with confirmation message.
   - `/reset-password`: Token-based new password entry with policy hints.
2. **Onboarding Wizard (`/onboarding`):**
   - Triggered when authenticated user has 0 organizations.
   - Step 1: Create Organization (name, auto-generated slug).
   - Step 2: Create First Workspace (name, slug).
   - Navigates to dashboard with newly created workspace active.
3. **Workspace Selector:**
   - Interactive dropdown in top header showing current organization and workspaces.
   - Allows instant workspace switching; updates local storage / active query context and invalidates tenant-scoped queries.
4. **Team & Membership Management:**
   - Dedicated team tab/page listing members, roles, join dates, and invitation statuses.
   - Modals for inviting new team members, changing roles, and transferring ownership.
5. **Session & Security Settings:**
   - View active login sessions (browser, created at, last active).
   - Revoke other sessions or change password.

---

## 6. Phased Implementation Roadmap

- **Phase 1:** Baseline verification (pytest 37 passed, frontend passed).
- **Phase 2:** Organization, workspace, membership, and invitation SQLAlchemy models in `backend/app/models/organization.py`.
- **Phase 3:** Alembic migration `20261108_0004_organizations_and_workspaces` and migration verification.
- **Phase 4:** Repositories and transactional services for Organizations, Workspaces, and Invitations.
- **Phase 5:** Centralized RBAC engine and declarative permission system in `backend/app/modules/authorization/`.
- **Phase 6:** Tenant-isolation dependencies (`get_current_organization`, `get_current_workspace`, permission checkers).
- **Phase 7:** EmailProvider abstraction and `DevelopmentEmailProvider` sink.
- **Phase 8:** Authentication API endpoints (`/api/v1/auth/*`) wired to existing password/session/token services.
- **Phase 9:** Organization, Workspace, and Membership endpoints (`/api/v1/organizations/*`, `/api/v1/workspaces/*`).
- **Phase 10:** Invitation API endpoints (`/api/v1/invitations/*`).
- **Phase 11:** Frontend authentication state, React Router routes, and API client enhancements (POST/PATCH/DELETE, CSRF header propagation, credentials include).
- **Phase 12:** Frontend authentication pages (Login, Register, Verify Email, Forgot Password, Reset Password).
- **Phase 13:** Frontend Onboarding Wizard, Workspace Switcher, and Team Management UI.
- **Phase 14:** Security and tenant-isolation test suites (testing cross-tenant leak prevention, role escalation blocks, and atomic token operations).
- **Phase 15:** Full regression validation across Python, TypeScript, SQLite, and production build.
- **Phase 16:** Completion documentation and technical architecture records.
