# API conventions

All API routes are versioned below `/api/v1`. Successful responses use `{ "data": ... }`; safe errors use `{ "error": { "code": "...", "message": "..." } }`.

Available foundation routes: `GET /health`, `GET /ready`, `GET /version`, and `GET /system/info`. The readiness route verifies a real database connection. No response includes secrets, paths, or environment values beyond safe deployment metadata.
