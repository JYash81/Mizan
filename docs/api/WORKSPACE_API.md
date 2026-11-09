# Workspace Management API Reference

**Base Paths:**  
- Organization-Scoped: `/api/v1/organizations/{organization_id}/workspaces`  
- Direct Workspace-Scoped: `/api/v1/workspaces/{workspace_id}`  

---

## Endpoints

### 1. Create Workspace
- **Method / Path:** `POST /api/v1/organizations/{organization_id}/workspaces`
- **Permission:** Requires `organization.workspaces.create` (`OWNER` or `ADMIN`).
- **Request Body:**
  ```json
  {
    "name": "Card Triage RAG",
    "slug": "card-triage-rag",
    "description": "Experimentation workspace for credit card support triage"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "data": {
      "id": "ws-uuid",
      "organization_id": "org-uuid",
      "name": "Card Triage RAG",
      "slug": "card-triage-rag",
      "status": "ACTIVE",
      "role": "WORKSPACE_OWNER"
    }
  }
  ```

### 2. List Organization Workspaces
- **Method / Path:** `GET /api/v1/organizations/{organization_id}/workspaces`
- **Security:** Returns all workspaces for Org Owner/Admin, or only explicitly assigned workspaces for regular members.

### 3. Get Workspace Detail
- **Method / Path:** `GET /api/v1/workspaces/{workspace_id}`
- **Permission:** Requires `workspace.read`.

### 4. Update Workspace
- **Method / Path:** `PATCH /api/v1/workspaces/{workspace_id}`
- **Permission:** Requires `workspace.update` (`WORKSPACE_OWNER` or `WORKSPACE_ADMIN`).

### 5. Archive Workspace
- **Method / Path:** `POST /api/v1/workspaces/{workspace_id}/archive`
- **Permission:** Requires `workspace.archive` (`WORKSPACE_OWNER`).

### 6. Workspace Members
- `GET /api/v1/workspaces/{ws_id}/members` (Requires `workspace.members.read`)
- `POST /api/v1/workspaces/{ws_id}/members` `{"user_id": "...", "role": "WORKSPACE_MEMBER"}` (User must be an active member of the parent organization).
- `PATCH /api/v1/workspaces/{ws_id}/members/{user_id}` (Requires `workspace.members.manage`)
- `DELETE /api/v1/workspaces/{ws_id}/members/{user_id}` (Requires `workspace.members.manage`)
