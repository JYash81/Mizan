# M15 Post-Audit: MySQL Concurrency & Multi-Client Verification Status

## 1. Executive Summary

- **Component:** M2.B1 Step 3 — Database Concurrency & Multi-Client Verification
- **Target DBMS:** MySQL 8.0+ (Production Target Engine)
- **Current Operational Status:** **`BLOCKED`** (Preserved without modification)
- **Verification Rule:** SQLite concurrency behavior (including WAL mode or in-memory locking) must **never** be used as evidence of MySQL multi-client concurrency correctness.

---

## 2. Workstation Infrastructure Inspection & Blocker Evidence

A systematic inspection of the local development environment was conducted on 2026-11-09:

```powershell
# Command Executed:
Get-Command mysql, docker, docker-compose, helm, kubectl -ErrorAction SilentlyContinue
Get-Service *mysql*, *maria* -ErrorAction SilentlyContinue
Test-NetConnection -ComputerName 127.0.0.1 -Port 3306 -InformationLevel Quiet
```

### Direct Inspection Results:
1. **Local MySQL Server:** Neither MySQL Server nor MariaDB is installed as a Windows service on the development workstation.
2. **Local MySQL Client:** The `mysql` CLI is not present on the system `PATH`.
3. **Port 3306 Status:** TCP connection to `127.0.0.1:3306` failed (Port closed / Not listening).
4. **Containerization Engine:** Docker and Docker Compose are not installed on this host (`docker : The term 'docker' is not recognized`). Therefore, a local ephemeral MySQL 8 Docker container cannot be spun up without installing external tooling.
5. **Remote Hostinger MySQL:** Hostinger Business Shared Hosting does not permit external direct TCP connections to port 3306 from external IP addresses (restricted by hosting firewall / bind-address `127.0.0.1`).
6. **Spending Constraint:** Adhering strictly to the **$0.00 additional spend policy**, no remote cloud database instances (AWS RDS, GCP Cloud SQL, or DigitalOcean Managed Databases) were purchased or provisioned.

**Conclusion:** Genuinely live MySQL multi-client concurrent execution cannot be executed on this host without a real MySQL 8 daemon or container runtime.

---

## 3. Code-Level Architectural Audit of Concurrency Controls

While live concurrency on MySQL remains blocked, the SQL statements, repository methods, and transaction boundaries in Mizan were audited for MySQL 8 InnoDB compatibility:

### 3.1 Atomic Single-Use Token Consumption
In `backend/app/modules/auth/services/token_service.py`:
```python
stmt = (
    update(AuthToken)
    .where(
        AuthToken.id == record.id,
        AuthToken.consumed_at.is_(None),
        AuthToken.revoked_at.is_(None),
    )
    .values(consumed_at=now)
    .execution_options(synchronize_session="fetch")
)
result = db.execute(stmt)
if result.rowcount != 1:
    return None
```
- **InnoDB Semantics:** Under MySQL InnoDB (`READ-COMMITTED` or `REPEATABLE-READ`), this conditional update acquires an exclusive row-level lock (`X-lock`) on the `auth_tokens` row. The first transaction to acquire the lock updates the row and receives `rowcount = 1`. Concurrent competing transactions will block until the first commits, after which their `WHERE consumed_at IS NULL` condition evaluates to false, returning `rowcount = 0` and safely failing.

### 3.2 Unique Constraints
- `users.email` and `users.normalized_email` are indexed with `unique=True`.
- `organizations.slug` and `workspaces.slug` enforce unique constraints per tenant.
- Concurrent insertion attempts with identical keys raise `IntegrityError` in SQLAlchemy, which is caught and converted to HTTP 409 Conflict.

### 3.3 Transaction Rollback Atomicity
- All database write operations occur within scoped sessions (`Session(engine)`).
- On any exception, `db.rollback()` is invoked, rolling back uncommitted changes completely before session closure.
- **Evidence:** Tested in `backend/tests/security/test_security_advanced.py::test_sec_035_transaction_rollback_atomicity`.

---

## 4. Test Harness Specification for Future MySQL Unblocking

To formally unblock `M2.B1 Step 3` once an authorized MySQL 8 environment is available, the following test suite must be executed:

```
+-------------------------------------------------------------------------+
|                  MySQL 8.0 Concurrency Verification Plan                |
+-------------------------------------------------------------------------+
| Test Case       | Concurrency Load  | Expected Outcome                  |
+-----------------+-------------------+-----------------------------------+
| CONCUR-01       | 10 threads        | Exactly 1 succeeds, 9 fail with   |
| (Reset Token)   | simultaneous      | rowcount == 0                     |
+-----------------+-------------------+-----------------------------------+
| CONCUR-02       | 5 threads         | Exactly 1 succeeds, 4 fail with   |
| (Invitation)    | simultaneous      | 409 Conflict / already accepted   |
+-----------------+-------------------+-----------------------------------+
| CONCUR-03       | 20 threads        | Zero deadlocks; unique constraint |
| (Org Creation)  | identical slug    | rejects duplicates with 409       |
+-----------------+-------------------+-----------------------------------+
| CONCUR-04       | 10 threads        | Zero cross-tenant data leaks      |
| (Multi-Tenant)  | intermingled      | under concurrent transactions     |
+-----------------+-------------------+-----------------------------------+
| CONCUR-05       | Single client     | Upgrade to head -> Downgrade 0014 |
| (Alembic)       |                   | -> Upgrade head without error     |
+-----------------+-------------------+-----------------------------------+
```

---

## 5. Formal Status Verdict

- **M2.B1 Step 3 — Remote MySQL Concurrency Verification:** **`BLOCKED`**
- **Action Required:** Preserve status as `BLOCKED` in `docs/PROJECT_STATUS.md`. Do not falsify or claim verification on SQLite. Run the concurrency test suite immediately upon provisioning an authorized MySQL 8 server or Docker host.
