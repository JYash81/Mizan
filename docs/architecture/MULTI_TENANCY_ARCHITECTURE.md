# Multi-Tenancy Architecture & Access Enforcement

**Author:** Principal Software Architect & Security Engineer  
**Date:** 2026-11-08  

---

## 1. Multi-Tenancy Model: Row-Level Scoped Monolith

Mizan implements a row-level multi-tenancy model within a portable relational database (SQLite in development, Hostinger MySQL/MariaDB in production).

### Enforcement Principles
1. **No Relying on Client Selectors:** Identifiers (`organization_id`, `workspace_id`) provided in URL paths or request bodies are treated purely as selectors, **never as proof of authorization**.
2. **Server-Side Context Resolution:**
   Every tenant-scoped endpoint invokes centralized FastAPI dependencies:
   - `get_current_organization`: Validates the authenticated user has an active membership record in the target organization.
   - `get_current_workspace`: Validates the workspace belongs to the parent organization and the user holds permitted workspace rights.
3. **Anti-Enumeration Responses:**
   If a user requests an organization or workspace belonging to another tenant, the API returns `404 Not Found` rather than `403 Forbidden`. This completely prevents attackers from enumerating valid organization or workspace IDs across tenants.
4. **Suspension Circuit-Breakers:**
   If an organization's status is `SUSPENDED`, all operations halt immediately with `403 Forbidden` ("Organization is suspended. Contact support.").
5. **Database-Level Isolation Constraints:**
   - Workspaces enforce `UniqueConstraint("organization_id", "slug")`.
   - Memberships enforce `UniqueConstraint("organization_id", "user_id")` and `UniqueConstraint("workspace_id", "user_id")`.
   - Invitations enforce `UniqueConstraint("token_hash")`.
