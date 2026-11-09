# Organization and Workspace Architecture

**Author:** Principal Software Architect  
**Scope:** Multi-tenant domain model, boundary separation, and hierarchy.  
**Date:** 2026-11-08  

---

## 1. Hierarchy and Domain Boundaries

Mizan organizes tenants into a strict two-tier operational hierarchy:
**Organizations (Tenants)** contain **Workspaces (Project Environments)**.

```
┌────────────────────────────────────────────────────────┐
│               ORGANIZATION (Business Tenant)           │
│  - Top-level legal & billing entity                    │
│  - Unique slug, verified business members, invitations  │
│  - Governed by Organization Roles (OWNER, ADMIN...)    │
└───────────────────────────┬────────────────────────────┘
                            │ 1 : N
                            ▼
┌────────────────────────────────────────────────────────┐
│            WORKSPACES (Project Environments)           │
│  - Isolated project contexts (Datasets, Models, Trials)│
│  - Unique slug scoped to parent organization           │
│  - Governed by Workspace Roles (WS_OWNER, WS_ADMIN...) │
└────────────────────────────────────────────────────────┘
```

### Architectural Guarantees
1. **Tenant Isolation:** An Organization represents an isolated business boundary. Data, documents, experiments, and memberships belonging to Organization A are completely invisible to Organization B.
2. **Workspace Scoping:** Workspaces cannot exist independently of an Organization. Every workspace has exactly one parent organization (`organization_id`).
3. **Membership Inheritance:** A user cannot be assigned a role in a workspace without first being an active member of that workspace's parent organization.
4. **Ownership Invariance:** Every organization must have at least one active `OWNER`. The sole owner cannot be removed or demoted without first transferring ownership to another active member.
5. **Archival Protection:** Archiving an organization or workspace soft-deletes its availability for new mutations, preserving the audit trail and existing data artifacts.
