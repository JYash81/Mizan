# CSRF protection

Each session receives a separate synchronizer token generated with `secrets.token_urlsafe(32)`. Only its SHA-256 digest is stored. Future unsafe API routes must call `validate_csrf`; safe reads do not require it. Origin and Referer checks remain additional future route-level defences.
