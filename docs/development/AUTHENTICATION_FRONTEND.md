# Frontend Authentication & Multi-Tenancy Architecture

**Scope:** React 19, TypeScript, React Router v7, TanStack Query, Tailwind CSS.  
**Date:** 2026-11-08  

---

## 1. Authentication Lifecycle & State Management

All authentication state is managed centrally via `AuthProvider` in `frontend/src/features/auth/AuthContext.tsx`.

### State Elements
- `user`: Authenticated user entity (ID, full name, email, verification status).
- `organizations`: List of accessible organizations for the user.
- `activeOrganization`: Currently selected organization.
- `workspaces`: Workspaces available under the active organization.
- `activeWorkspace`: Currently active workspace context.

### Route Protection
- `ProtectedRoute`:
  - If `isLoading`: displays loading state.
  - If `!user`: redirects to `/login`.
  - If `organizations.length === 0`: automatically redirects to `/onboarding`.
  - Otherwise renders the requested protected view inside `Shell`.

### Pages Implemented
1. `/login`: Form with email, password, show/hide toggle, link to registration and forgot password.
2. `/register`: Name, email, password policy (min 12 chars), confirmation, terms acceptance, success state.
3. `/verify-email`: Auto-consumes token from `?token=...` or accepts manual entry; includes resend verification link.
4. `/forgot-password`: Email entry with anti-enumeration response and link back to login.
5. `/reset-password`: Token and password entry with policy checks and auto-redirect to login.
6. `/onboarding`: 2-step wizard creating user's first Organization and first Workspace.
7. `/team`: Table of organization members, role badges, action buttons, pending invitations list, and "Invite Member" modal.
8. `/settings`: Active sessions list with "Current Device" badge and session revocation capability.
9. Workspace Selector: Interactive dropdown in top navigation to switch active organization or workspace, or create new ones.
