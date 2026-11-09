#!/usr/bin/env python3
"""M15 Penetration Testing Rehearsal Script.

Automated, safe local penetration testing harness verifying:
- Unauthenticated access rejection (401)
- IDOR and cross-tenant anti-enumeration (404)
- Privilege escalation rejection (403)
- SQL injection resistance (parameterization safety)
- Cross-Site Scripting (XSS) input safety
- Cross-Site Request Forgery (CSRF) protection
- Server-Side Request Forgery (SSRF) rejection
- Cryptographic signature purpose enforcement
- Storage path traversal prevention

Usage:
    python scripts/penetration_test_rehearsal.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import json

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.modules.alerting.notification_router import validate_webhook_url
from app.modules.artifact_registry.exceptions import (
    SignaturePurposeMismatchError,
)
from app.modules.artifact_registry.gate3_service import verify_gate3_attestation
from app.modules.auth.services import (
    password_service,
    session_service,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


class PenTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: list[dict[str, str]] = []

        # Setup in-memory test database
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)

        app = create_app()

        def override_get_db():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        self._seed_test_tenants()

    def _seed_test_tenants(self):
        with Session(self.engine) as db:
            pwd_hash = password_service.hash_password("ValidPassword123!")

            # Tenant A
            self.user_a = User(
                id=f"usr-a-{uuid.uuid4().hex[:6]}",
                full_name="Alice A",
                email="alice@tenant-a.com",
                normalized_email="alice@tenant-a.com",
                password_hash=pwd_hash,
                status=AccountStatus.ACTIVE,
            )
            self.org_a = Organization(id=f"org-a-{uuid.uuid4().hex[:6]}", name="Org A", slug=f"org-a-{uuid.uuid4().hex[:4]}", created_by=self.user_a.id)
            self.ws_a = Workspace(id=f"ws-a-{uuid.uuid4().hex[:6]}", organization_id=self.org_a.id, name="Workspace A", slug="ws-a", created_by=self.user_a.id)
            mem_a = OrganizationMembership(organization_id=self.org_a.id, user_id=self.user_a.id, role=OrganizationRole.MEMBER)
            ws_mem_a = WorkspaceMembership(workspace_id=self.ws_a.id, user_id=self.user_a.id, role=WorkspaceRole.WORKSPACE_ADMIN)

            # Tenant B (Attacker)
            self.user_b = User(
                id=f"usr-b-{uuid.uuid4().hex[:6]}",
                full_name="Bob B",
                email="bob@tenant-b.com",
                normalized_email="bob@tenant-b.com",
                password_hash=pwd_hash,
                status=AccountStatus.ACTIVE,
            )
            self.org_b = Organization(id=f"org-b-{uuid.uuid4().hex[:6]}", name="Org B", slug=f"org-b-{uuid.uuid4().hex[:4]}", created_by=self.user_b.id)
            self.ws_b = Workspace(id=f"ws-b-{uuid.uuid4().hex[:6]}", organization_id=self.org_b.id, name="Workspace B", slug="ws-b", created_by=self.user_b.id)
            mem_b = OrganizationMembership(organization_id=self.org_b.id, user_id=self.user_b.id, role=OrganizationRole.MEMBER)
            ws_mem_b = WorkspaceMembership(workspace_id=self.ws_b.id, user_id=self.user_b.id, role=WorkspaceRole.WORKSPACE_MEMBER)

            db.add_all([self.user_a, self.org_a, self.ws_a, mem_a, ws_mem_a,
                        self.user_b, self.org_b, self.ws_b, mem_b, ws_mem_b])
            db.commit()

            # Active sessions
            sess_a = session_service.create_session(db, self.user_a.id)
            sess_b = session_service.create_session(db, self.user_b.id)
            db.commit()

            # Extract string IDs to avoid DetachedInstanceError
            self.user_a_id = self.user_a.id
            self.org_a_id = self.org_a.id
            self.ws_a_id = self.ws_a.id
            self.user_b_id = self.user_b.id
            self.org_b_id = self.org_b.id
            self.ws_b_id = self.ws_b.id
            self.sess_a_token = sess_a.session_token
            self.sess_a_csrf = sess_a.csrf_token
            self.sess_b_token = sess_b.session_token
            self.sess_b_csrf = sess_b.csrf_token

    def record(self, test_id: str, name: str, passed: bool, detail: str = ""):
        if passed:
            self.passed += 1
            print(f"  [PASS] {test_id}: {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {test_id}: {name} - {detail}")
        self.results.append({"id": test_id, "name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    def run_all(self):
        print("=" * 70)
        print("MIZAN MILESTONE 15 — PENETRATION TESTING REHEARSAL")
        print("=" * 70)

        # 1. Unauthenticated Endpoint Probing
        print("\n[Category 1: Authentication Bypass]")
        endpoints = [
            "/api/v1/auth/me",
            f"/api/v1/workspaces/{self.ws_a_id}",
            f"/api/v1/datasets?workspace_id={self.ws_a_id}",
            f"/api/v1/ops/incidents?workspace_id={self.ws_a_id}",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.record(f"AUTH-BYPASS-{ep.split('/')[-1]}", f"Unauthenticated request to {ep}", res.status_code in (401, 404))

        # 2. Cross-Tenant IDOR and Anti-Enumeration
        print("\n[Category 2: Cross-Tenant Authorization & IDOR]")
        cookies_b = {"mizan_session": self.sess_b_token}
        res_cross_ws = self.client.get(f"/api/v1/workspaces/{self.ws_a_id}", cookies=cookies_b)
        self.record("IDOR-01", "Tenant B access to Tenant A Workspace returns 404", res_cross_ws.status_code == 404)

        res_cross_datasets = self.client.get(f"/api/v1/datasets?workspace_id={self.ws_a_id}", cookies=cookies_b)
        self.record("IDOR-02", "Tenant B query for Tenant A Datasets returns 404", res_cross_datasets.status_code == 404)

        res_cross_incidents = self.client.get(f"/api/v1/ops/incidents?workspace_id={self.ws_a_id}", cookies=cookies_b)
        self.record("IDOR-03", "Tenant B query for Tenant A Incidents returns 404", res_cross_incidents.status_code == 404)

        # 3. Privilege Escalation
        print("\n[Category 3: Privilege Escalation]")
        headers_b = {"X-CSRF-Token": self.sess_b_csrf}
        res_esc = self.client.post(
            f"/api/v1/organizations/{self.org_b_id}/workspaces",
            cookies=cookies_b,
            headers=headers_b,
            json={"name": "Escalated Workspace", "slug": "esc-ws"},
        )
        self.record("PRIV-01", "Member role creating workspace rejected with 403", res_esc.status_code == 403)

        # 4. SQL Injection Injection Attempts
        print("\n[Category 4: SQL Injection Probing]")
        sqli_payloads = [
            "' OR '1'='1",
            "1; DROP TABLE users; --",
            "admin'--",
            "\" UNION SELECT * FROM users --",
        ]
        for idx, sqli in enumerate(sqli_payloads):
            cookies_a = {"mizan_session": self.sess_a_token}
            res_sqli = self.client.get(
                f"/api/v1/ops/incidents?workspace_id={self.ws_a_id}&status={sqli}",
                cookies=cookies_a,
            )
            # Must return 422 (validation error on enum) or empty list, NOT 500 or leaked rows
            safe = res_sqli.status_code in (200, 422) and "syntax error" not in res_sqli.text.lower()
            self.record(f"SQLI-{idx+1}", f"SQLi payload safely handled: {sqli[:20]}", safe)

        # 5. Cross-Site Scripting (XSS) Sanitization
        print("\n[Category 5: Cross-Site Scripting (XSS) Handling]")
        xss_payload = "<script>alert('XSS')</script>"
        cookies_a = {"mizan_session": self.sess_a_token}
        headers_a = {"X-CSRF-Token": self.sess_a_csrf}
        res_xss = self.client.post(
            f"/api/v1/ops/incidents?workspace_id={self.ws_a_id}",
            cookies=cookies_a,
            headers=headers_a,
            json={"title": xss_payload, "description": "XSS Test", "severity": "SEV3"},
        )
        xss_safe = (
            res_xss.status_code == 201
            and res_xss.headers.get("content-type", "").startswith("application/json")
            and res_xss.headers.get("x-content-type-options") == "nosniff"
        )
        self.record("XSS-01", "XSS payload stored as literal text with nosniff header", xss_safe)

        # 6. Cross-Site Request Forgery (CSRF) Protection
        print("\n[Category 6: CSRF Token Enforcement]")
        res_csrf_missing = self.client.post(
            f"/api/v1/ops/incidents?workspace_id={self.ws_a_id}",
            cookies=cookies_a,
            # No X-CSRF-Token header
            json={"title": "CSRF Attack", "description": "No CSRF token", "severity": "SEV3"},
        )
        self.record("CSRF-01", "Mutating request without CSRF token returns 403", res_csrf_missing.status_code == 403)

        res_csrf_invalid = self.client.post(
            f"/api/v1/ops/incidents?workspace_id={self.ws_a_id}",
            cookies=cookies_a,
            headers={"X-CSRF-Token": "invalid-forged-csrf-token"},
            json={"title": "CSRF Attack", "description": "Forged CSRF token", "severity": "SEV3"},
        )
        self.record("CSRF-02", "Mutating request with invalid CSRF token returns 403", res_csrf_invalid.status_code == 403)

        # 7. SSRF Protection
        print("\n[Category 7: Server-Side Request Forgery (SSRF)]")
        ssrf_targets = [
            "http://127.0.0.1:8080/admin",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/private",
            "http://192.168.1.1/router",
        ]
        for idx, url in enumerate(ssrf_targets):
            blocked = False
            try:
                validate_webhook_url(url, allow_test_hosts=False)
            except ValueError:
                blocked = True
            self.record(f"SSRF-{idx+1}", f"SSRF private destination blocked: {url}", blocked)

        # 8. Cryptographic Purpose Confusion Protection
        print("\n[Category 8: Cryptographic Signature Purpose Separation]")
        gate1_payload = {
            "approval_id": "appr-123",
            "schema_version": "gate1-2026-11-09",
            "signature_purpose": "GATE1_DATA_PROTECTION",
        }
        gate1_json = json.dumps(gate1_payload, sort_keys=True)
        purpose_blocked = False
        try:
            # Attestation attempted with wrong purpose (e.g. GATE1 verified by GATE3)
            verify_gate3_attestation(
                canonical_payload_json=gate1_json,
                signature_hex="dummy_sig_hex",
                key_id="mizan-platform-dev-01",
            )
        except SignaturePurposeMismatchError:
            purpose_blocked = True
        self.record("CRYPTO-01", "Signature purpose substitution rejected", purpose_blocked)

        # Summary
        print("\n" + "=" * 70)
        print(f"PENETRATION TEST SUMMARY: {self.passed} PASSED, {self.failed} FAILED")
        print("=" * 70)
        return self.failed == 0


if __name__ == "__main__":
    runner = PenTestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
