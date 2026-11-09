# Role-Based Access Control (RBAC) Security Specification

**Author:** Application Security Engineer  
**Date:** 2026-11-08  

---

## 1. Role Hierarchy and Permissions

Mizan's authorization engine evaluates fine-grained, declarative permissions rather than hardcoded role strings in handlers.

### Organization Roles
- **`OWNER`:** Full administrative control over organization settings, members, ownership transfers, and child workspaces.
- **`ADMIN`:** Operational management of members (invite, assign roles up to Admin) and workspaces. Cannot remove or demote the Owner, and cannot transfer ownership.
- **`MEMBER`:** Standard business user. Can read organization metadata and view member rosters. Operational access to datasets and experiments is governed by workspace roles.
- **`VIEWER`:** Read-only access to authorized resources.

### Workspace Roles
- **`WORKSPACE_OWNER`:** Full control over workspace configuration, members, and all future assets (datasets, experiments, trials, approvals).
- **`WORKSPACE_ADMIN`:** Operational control over workspace members and assets. Cannot archive the workspace.
- **`WORKSPACE_MEMBER`:** Can create and execute experiments and datasets.
- **`WORKSPACE_VIEWER`:** Read-only access to workspace results and reports.

### Security Invariants
1. **Org Owner Inheritance:** An organization `OWNER` automatically inherits `WORKSPACE_OWNER` authority over all child workspaces within their organization.
2. **No Self-Demotion of Last Owner:** The authorization service validates that the active owner count is strictly $> 1$ before allowing an owner demotion or removal.
3. **Controlled Ownership Transfer:** Ownership transfer is an atomic operation (`transfer_organization_ownership`) that demotes the caller to `ADMIN` while promoting the target member to `OWNER` in a single transaction.
