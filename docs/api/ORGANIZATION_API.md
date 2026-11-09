# Organization Management API Reference

**Base Path:** `/api/v1/organizations`  
**Authentication:** Required on all endpoints.  
**CSRF:** Required on state-changing methods.  

---

## Endpoints

### 1. Create Organization
- **Method / Path:** `POST /api/v1/organizations/`
- **Request Body:**
  ```json
  {
    "name": "Alpha Technologies",
    "slug": "alpha-tech",
    "description": "Enterprise AI Research"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "data": {
      "id": "org-uuid",
      "name": "Alpha Technologies",
      "slug": "alpha-tech",
      "status": "ACTIVE",
      "role": "OWNER"
    }
  }
  ```

### 2. List Organizations
- **Method / Path:** `GET /api/v1/organizations/`
- **Response (200 OK):** Returns all active organizations where caller holds active membership.

### 3. Get Organization Detail
- **Method / Path:** `GET /api/v1/organizations/{organization_id}`
- **Security:** Returns 404 if caller is not an active member.

### 4. Update Organization
- **Method / Path:** `PATCH /api/v1/organizations/{organization_id}`
- **Permission:** Requires `organization.update` (`OWNER` or `ADMIN`).

### 5. Archive Organization
- **Method / Path:** `POST /api/v1/organizations/{organization_id}/archive`
- **Permission:** Requires `organization.archive` (`OWNER` only).

### 6. Member Management
- `GET /api/v1/organizations/{org_id}/members` (Requires `organization.members.read`)
- `PATCH /api/v1/organizations/{org_id}/members/{user_id}` (Requires `organization.members.manage`. Demoting last owner is blocked).
- `DELETE /api/v1/organizations/{org_id}/members/{user_id}` (Requires `organization.members.manage`. Removing last owner is blocked).
- `POST /api/v1/organizations/{org_id}/transfer-ownership` `{"new_owner_id": "..."}` (Requires `organization.owner.transfer`, `OWNER` only).
