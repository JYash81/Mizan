# Authentication & Identity API Reference

**Base Path:** `/api/v1/auth`  
**Authentication:** HttpOnly Cookie (`mizan_session`) or `Authorization: Bearer <token>`  
**CSRF Protection:** State-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`) require `X-CSRF-Token` header when using cookie authentication.

---

## Endpoints

### 1. Register User
- **Method / Path:** `POST /api/v1/auth/register`
- **Request Body:**
  ```json
  {
    "full_name": "Alice Smith",
    "email": "alice@company.com",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!",
    "terms_accepted": true
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "data": {
      "message": "Registration successful. Please verify your email to activate your account."
    }
  }
  ```

### 2. Verify Email
- **Method / Path:** `POST /api/v1/auth/verify-email`
- **Request Body:** `{"token": "<raw_verification_token>"}`
- **Response (200 OK):** `{"data": {"message": "Email verified successfully. You may now log in."}}`

### 3. Resend Verification Link
- **Method / Path:** `POST /api/v1/auth/resend-verification`
- **Request Body:** `{"email": "alice@company.com"}`
- **Response (200 OK):** `{"data": {"message": "If an unverified account exists, a new verification link has been sent."}}`

### 4. Login
- **Method / Path:** `POST /api/v1/auth/login`
- **Request Body:** `{"email": "alice@company.com", "password": "SecurePassword123!"}`
- **Response (200 OK):**
  Sets `Set-Cookie: mizan_session=...; HttpOnly; SameSite=Lax; Path=/`
  ```json
  {
    "data": {
      "user": {
        "id": "uuid-...",
        "full_name": "Alice Smith",
        "email": "alice@company.com",
        "status": "ACTIVE",
        "email_verified_at": "2026-11-08T15:00:00Z",
        "created_at": "2026-11-08T14:00:00Z"
      },
      "csrf_token": "random-csrf-token-..."
    }
  }
  ```

### 5. Logout
- **Method / Path:** `POST /api/v1/auth/logout`
- **Response (200 OK):** Clears cookie. `{"data": {"message": "Logged out successfully."}}`

### 6. Get Current User Profile (`/me`)
- **Method / Path:** `GET /api/v1/auth/me`
- **Response (200 OK):**
  ```json
  {
    "data": {
      "user": { ... },
      "organizations": [
        { "id": "...", "name": "Acme Corp", "slug": "acme", "role": "OWNER" }
      ]
    }
  }
  ```

### 7. Forgot Password & Reset Password
- `POST /api/v1/auth/forgot-password` `{"email": "alice@company.com"}`
- `POST /api/v1/auth/reset-password` `{"token": "...", "new_password": "...", "new_password_confirm": "..."}`

### 8. Session Inspection & Revocation
- `GET /api/v1/auth/sessions` (lists active sessions)
- `DELETE /api/v1/auth/sessions/{session_id}` (revokes target session)
- `POST /api/v1/auth/rotate-session` (rotates current session credential)
