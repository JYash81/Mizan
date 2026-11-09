# Organization, Workspace, and Membership Schema

**Migration:** `20261108_0004_organizations_and_workspaces`  
**Database Engines Supported:** SQLite (Development), Hostinger MySQL / MariaDB (Production)  
**Date:** 2026-11-08  

---

## 1. Table Definitions

### `organizations`
| Column | Type | Constraints / Attributes |
| :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `name` | `VARCHAR(255)` | Not Null |
| `slug` | `VARCHAR(100)` | Unique, Indexed, Lowercase alphanumeric with hyphens |
| `description` | `TEXT` | Nullable |
| `created_by` | `VARCHAR(36)` | Foreign Key `users.id`, Indexed |
| `status` | `VARCHAR(50)` | Not Null, Default `'ACTIVE'` (`ACTIVE`, `SUSPENDED`, `ARCHIVED`) |
| `created_at` | `DATETIME` | Server default `now()` |
| `updated_at` | `DATETIME` | Server default `now()`, on update `now()` |

### `organization_memberships`
| Column | Type | Constraints / Attributes |
| :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `organization_id` | `VARCHAR(36)` | Foreign Key `organizations.id`, Indexed |
| `user_id` | `VARCHAR(36)` | Foreign Key `users.id`, Indexed |
| `role` | `VARCHAR(50)` | Not Null, Default `'MEMBER'` (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`) |
| `membership_status` | `VARCHAR(50)` | Not Null, Default `'ACTIVE'` (`ACTIVE`, `SUSPENDED`) |
| `invited_by` | `VARCHAR(36)` | Foreign Key `users.id`, Nullable |
| `created_at` | `DATETIME` | Server default `now()` |
| `updated_at` | `DATETIME` | Server default `now()` |
| **Constraint** | `UNIQUE` | `(organization_id, user_id)` (Named `uq_org_member`) |

### `workspaces`
| Column | Type | Constraints / Attributes |
| :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `organization_id` | `VARCHAR(36)` | Foreign Key `organizations.id`, Indexed |
| `name` | `VARCHAR(255)` | Not Null |
| `slug` | `VARCHAR(100)` | Indexed |
| `description` | `TEXT` | Nullable |
| `created_by` | `VARCHAR(36)` | Foreign Key `users.id`, Indexed |
| `status` | `VARCHAR(50)` | Not Null, Default `'ACTIVE'` (`ACTIVE`, `ARCHIVED`) |
| `created_at` | `DATETIME` | Server default `now()` |
| `updated_at` | `DATETIME` | Server default `now()` |
| **Constraint** | `UNIQUE` | `(organization_id, slug)` (Named `uq_workspace_org_slug`) |

### `workspace_memberships`
| Column | Type | Constraints / Attributes |
| :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `workspace_id` | `VARCHAR(36)` | Foreign Key `workspaces.id`, Indexed |
| `user_id` | `VARCHAR(36)` | Foreign Key `users.id`, Indexed |
| `role` | `VARCHAR(50)` | Not Null, Default `'WORKSPACE_MEMBER'` (`WORKSPACE_OWNER`, `WORKSPACE_ADMIN`, `WORKSPACE_MEMBER`, `WORKSPACE_VIEWER`) |
| `membership_status` | `VARCHAR(50)` | Not Null, Default `'ACTIVE'` |
| `created_at` | `DATETIME` | Server default `now()` |
| `updated_at` | `DATETIME` | Server default `now()` |
| **Constraint** | `UNIQUE` | `(workspace_id, user_id)` (Named `uq_workspace_member`) |

### `invitations`
| Column | Type | Constraints / Attributes |
| :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `organization_id` | `VARCHAR(36)` | Foreign Key `organizations.id`, Indexed |
| `workspace_id` | `VARCHAR(36)` | Foreign Key `workspaces.id`, Nullable, Indexed |
| `invited_email` | `VARCHAR(320)` | Not Null |
| `normalized_email` | `VARCHAR(320)` | Indexed |
| `token_hash` | `VARCHAR(64)` | Unique, Indexed (SHA-256 digest) |
| `organization_role` | `VARCHAR(50)` | Not Null, Default `'MEMBER'` |
| `workspace_role` | `VARCHAR(50)` | Nullable |
| `invited_by` | `VARCHAR(36)` | Foreign Key `users.id`, Indexed |
| `status` | `VARCHAR(50)` | Not Null, Default `'PENDING'` (`PENDING`, `ACCEPTED`, `REJECTED`, `REVOKED`, `EXPIRED`) |
| `expires_at` | `DATETIME` | Not Null |
| `accepted_at` | `DATETIME` | Nullable |
| `revoked_at` | `DATETIME` | Nullable |
| `created_at` | `DATETIME` | Server default `now()` |
