# Session management

Sessions use `secrets.token_urlsafe(32)` (at least 256 bits) and persist only SHA-256 digests. The default absolute lifetime is 12 hours, idle timeout 30 minutes, activity-write interval 5 minutes, and expired-record retention 30 days. Rotation uses a nested transaction: a conditional `UPDATE` requiring `revoked_at IS NULL` is the concurrency gate, replacement persistence occurs in the same savepoint, and the service commits before returning the new credential. A replacement-insertion failure rolls back the revocation.

SQLite concurrency cannot fully model production concurrent rotation. `MIZAN_TEST_MYSQL_URL` was not configured, so a MySQL/MariaDB integration test remains required. Raw credentials have `repr=False` and are not logged.
