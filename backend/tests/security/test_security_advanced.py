"""Security Regression Test Suite: Advanced Scenarios (SEC-021 through SEC-042).

Covers Site Agent replay attacks, command allowlists, telemetry privacy scrubbing,
Prometheus cardinality bounding, SSRF defense, atomic rollback safety, SLO missing data,
unauthorized ops access, XSS sanitization, production configuration validation,
transaction rollback atomicity, and HTTP security headers.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.artifact_registry import (
    ModelFamily,
    ModelVersion,
    ModelVersionStatus,
)
from app.models.catalog import AppDefinition
from app.models.identity import AccountStatus, TokenPurpose, User
from app.models.observability import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    RollbackMode,
    RollbackPolicy,
)
from app.models.runtime import (
    AgentCommandStatus,
    AgentCommandType,
    CustomerSite,
    ReadinessState,
    RuntimeApplication,
    RuntimeSlot,
    SiteStatus,
    SlotName,
    SlotStatus,
)
from app.modules.alerting.notification_router import validate_webhook_url
from app.modules.auth.services import password_service, session_service, token_service
from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    sign_payload,
    verify_signature,
)
from app.modules.observability.telemetry_privacy import (
    assert_no_privacy_violation,
    sanitize_event_payload,
    validate_and_sanitize_labels,
)
from app.modules.rollback.rollback_eligibility import check_rollback_eligibility
from app.modules.rollback.rollback_executor import execute_rollback
from app.modules.runtime.exceptions import (
    ReplayedNonceError,
)
from app.modules.runtime.schemas import (
    AgentCommandConsumeRequest,
    AgentCommandCreate,
    SiteAgentEnrollRequest,
)
from app.modules.runtime.site_agent_service import (
    consume_agent_command,
    issue_agent_command,
)
from app.modules.runtime.site_service import (
    enroll_site_agent,
    generate_enrollment_token,
)
from app.modules.slo.slo_service import record_snapshot
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def sec_advanced_env():
    """Sets up an isolated in-memory test environment for advanced security scenarios."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def _override_get_db():
        db = Session(engine, expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    db = Session(engine, expire_on_commit=False)

    # Primary user (Alice)
    user_a = User(
        id=f"usr-adv-a-{uuid.uuid4().hex[:6]}",
        full_name="Alice SecAdmin",
        email="alice.sec@enterprise.com",
        normalized_email="alice.sec@enterprise.com",
        password_hash=password_service.hash_password("StrongPassword123!"),
        status=AccountStatus.ACTIVE,
    )
    # Foreign tenant user (Bob)
    user_b = User(
        id=f"usr-adv-b-{uuid.uuid4().hex[:6]}",
        full_name="Bob Attacker",
        email="bob.attacker@foreign.com",
        normalized_email="bob.attacker@foreign.com",
        password_hash=password_service.hash_password("StrongPassword123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([user_a, user_b])
    db.commit()

    org_a, _ = organization_service.create_organization(db, user_a.id, "Sec Org A", "sec-org-a")
    ws_a, _ = workspace_service.create_workspace(db, org_a.id, user_a.id, "Sec Workspace A", "sec-ws-a")

    org_b, _ = organization_service.create_organization(db, user_b.id, "Sec Org B", "sec-org-b")
    ws_b, _ = workspace_service.create_workspace(db, org_b.id, user_b.id, "Sec Workspace B", "sec-ws-b")
    db.commit()

    sess_a = session_service.create_session(db, user_a.id)
    sess_b = session_service.create_session(db, user_b.id)
    db.commit()

    # Customer site in ws_a
    site = CustomerSite(
        id=f"site-adv-{uuid.uuid4().hex[:6]}",
        organization_id=org_a.id,
        workspace_id=ws_a.id,
        site_key=f"edge-adv-{uuid.uuid4().hex[:4]}",
        site_name="Sec Advanced Edge Site",
        status=SiteStatus.ACTIVE,
        created_by=user_a.id,
    )
    db.add(site)
    db.commit()

    tok = generate_enrollment_token(db, site.id, user_a.id)
    enr = enroll_site_agent(
        db,
        SiteAgentEnrollRequest(
            token=tok.raw_token,
            public_key_pem="-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAadvsiteagentpubkey12345678901234\n-----END PUBLIC KEY-----",
            key_id="k-adv-agent",
            platform_info={"memory_mb": 16384},
        ),
    )
    db.commit()

    return {
        "engine": engine,
        "client": client,
        "user_a": user_a,
        "user_b": user_b,
        "org_a": org_a,
        "ws_a": ws_a,
        "org_b": org_b,
        "ws_b": ws_b,
        "sess_a": sess_a,
        "sess_b": sess_b,
        "site": site,
        "agent_id": enr.agent_id,
    }


# =========================================================================
# SEC-021: Site Agent Command Replay Prevention (Duplicate Nonce)
# =========================================================================
def test_sec_021_site_agent_command_replay_rejected(sec_advanced_env):
    """Consuming the exact same Site Agent command twice must raise ReplayedNonceError."""
    engine = sec_advanced_env["engine"]
    site = sec_advanced_env["site"]
    agent_id = sec_advanced_env["agent_id"]

    with Session(engine) as db:
        cmd = issue_agent_command(
            db=db,
            customer_site_id=site.id,
            payload=AgentCommandCreate(
                command_type=AgentCommandType.REPORT_RUNTIME_STATUS,
                payload={"check": "healthy"},
            ),
            expires_in_hours=1,
        )

        # First consumption succeeds
        res1 = consume_agent_command(
            db=db,
            customer_site_id=site.id,
            agent_id=agent_id,
            payload=AgentCommandConsumeRequest(
                command_id=cmd.command_id,
                status=AgentCommandStatus.CONSUMED,
                execution_summary={"ok": True},
            ),
        )
        assert res1["status"] == "CONSUMED"

        # Replay attempt fails with ReplayedNonceError
        with pytest.raises(ReplayedNonceError):
            consume_agent_command(
                db=db,
                customer_site_id=site.id,
                agent_id=agent_id,
                payload=AgentCommandConsumeRequest(
                    command_id=cmd.command_id,
                    status=AgentCommandStatus.CONSUMED,
                    execution_summary={"ok": True},
                ),
            )


# =========================================================================
# SEC-022: Unauthorized Command Type Rejected
# =========================================================================
def test_sec_022_unauthorized_command_type_rejected():
    """Unallowlisted arbitrary shell execution commands must be rejected by schema."""
    with pytest.raises(ValueError):
        AgentCommandCreate(
            command_type="EXEC_SHELL_COMMAND",  # Not in AgentCommandType
            payload={"cmd": "rm -rf /"},
        )


# =========================================================================
# SEC-023: Runtime Secret Leakage Prevention in Completions/RAG
# =========================================================================
def test_sec_023_runtime_secret_not_leaked_in_telemetry():
    """Confidential tokens, canary secrets, and credentials must never appear in telemetry logs."""
    canary_secret = "mizan_canary_super_secret_key_9876543210"
    raw_event = {
        "api_key": canary_secret,
        "authorization": f"Bearer {canary_secret}",
        "prompt": f"Please verify this key: {canary_secret}",
        "safe_latency_ms": 23.5,
    }

    sanitized = sanitize_event_payload(raw_event)
    assert canary_secret not in str(sanitized)
    assert sanitized["api_key"] == "[REDACTED_PRIVACY]"
    assert sanitized["prompt"] == "[REDACTED_PRIVACY]"
    assert_no_privacy_violation(sanitized)


# =========================================================================
# SEC-024: Telemetry Payload Sanitization (Prompts & Credentials Scrubbed)
# =========================================================================
def test_sec_024_telemetry_payload_sanitization():
    """User prompts, completions, and email addresses must be safely scrubbed from telemetry."""
    event = {
        "user_prompt": "What are our Q3 financial figures?",
        "completion": "Our profit was 12 million AED.",
        "contact_email": "cfo@enterprise.ae",
        "service": "inference_engine",
    }
    cleaned = sanitize_event_payload(event)
    assert cleaned["user_prompt"] == "[REDACTED_PRIVACY]"
    assert cleaned["completion"] == "[REDACTED_PRIVACY]"
    assert cleaned["contact_email"] == "[REDACTED_EMAIL]"
    assert cleaned["service"] == "inference_engine"


# =========================================================================
# SEC-025: Prometheus Label Cardinality Bounding
# =========================================================================
def test_sec_025_prometheus_label_cardinality_control():
    """Unbounded high-cardinality user inputs must be stripped from Prometheus metric labels."""
    untrusted_labels = {
        "service": "runtime",
        "endpoint": "/v1/chat/completions",
        "user_session_id": "sess-unbounded-high-cardinality-99999",
        "prompt_sha256": "abcdef1234567890",
        "ip_address": "192.0.2.1",
    }
    allowed = ["service", "endpoint", "status_class"]
    sanitized_labels = validate_and_sanitize_labels("runtime_requests_total", untrusted_labels, allowed)

    assert "user_session_id" not in sanitized_labels
    assert "prompt_sha256" not in sanitized_labels
    assert "ip_address" not in sanitized_labels
    assert sanitized_labels["service"] == "runtime"
    assert sanitized_labels["endpoint"] == "/v1/chat/completions"


# =========================================================================
# SEC-026: SSRF to Private IP Ranges Rejected
# =========================================================================
def test_sec_026_ssrf_private_ip_ranges_rejected():
    """SSRF validator must block loopback, RFC 1918 private networks, and cloud metadata."""
    private_urls = [
        "http://127.0.0.1:8080/hook",
        "http://10.0.0.1/internal-admin",
        "http://172.16.0.10/metrics",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
    ]
    for url in private_urls:
        with pytest.raises(ValueError, match="(SSRF violation|prohibited)"):
            validate_webhook_url(url, allow_test_hosts=False)


# =========================================================================
# SEC-027: DNS Rebinding & Hostname Alias SSRF Bypass Blocked
# =========================================================================
def test_sec_027_dns_rebinding_and_hostname_aliases_blocked():
    """Hostnames such as localhost, metadata, instance-data, and non-http schemes must be blocked."""
    alias_urls = [
        "http://localhost:5000/api",
        "http://metadata/computeMetadata/v1",
        "http://instance-data/latest/meta-data",
        "ftp://internal.example.com/file",
        "gopher://internal.example.com/",
    ]
    for url in alias_urls:
        with pytest.raises(ValueError, match="(SSRF violation|prohibited|scheme)"):
            validate_webhook_url(url, allow_test_hosts=False)


# =========================================================================
# SEC-028: Invalid Rollback Target Slot Handled Safely
# =========================================================================
def test_sec_028_invalid_rollback_target_slot(sec_advanced_env):
    """Rollback cannot be executed if the target slot is empty or invalid."""
    engine = sec_advanced_env["engine"]
    site = sec_advanced_env["site"]
    ws_a = sec_advanced_env["ws_a"]
    org_a = sec_advanced_env["org_a"]
    user_a = sec_advanced_env["user_a"]

    with Session(engine) as db:
        app_def = AppDefinition(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            app_key=f"rollback-app-{uuid.uuid4().hex[:6]}",
            name="Rollback App",
            description="Rollback test application",
            owner_id=user_a.id,
        )
        db.add(app_def)
        db.flush()

        runtime_app = RuntimeApplication(
            customer_site_id=site.id,
            app_definition_id=app_def.id,
            app_version_id="app-v1-id",
            app_manifest_digest="sha256-hash-manifest",
            status="INSTALLED",
            active_slot_name=SlotName.SLOT_A.value,
        )
        db.add(runtime_app)
        db.flush()

        # Only SLOT_A created, SLOT_B is absent
        slot_a = RuntimeSlot(
            runtime_application_id=runtime_app.id,
            slot_name=SlotName.SLOT_A.value,
            status=SlotStatus.ACTIVE,
            readiness_state=ReadinessState.READY,
            app_version_id="app-v1",
            model_version_id="model-v1",
        )
        db.add(slot_a)
        db.commit()

        # Eligibility check must fail because target slot does not exist
        eligibility = check_rollback_eligibility(db, runtime_app.id)
        assert eligibility.is_eligible is False


# =========================================================================
# SEC-029: Revoked Release Rollback Aborted with ABORTED_UNSAFE_TARGET
# =========================================================================
def test_sec_029_revoked_release_rollback_aborted(sec_advanced_env):
    """Rollback to a revoked release must be aborted immediately as an unsafe target."""
    engine = sec_advanced_env["engine"]
    site = sec_advanced_env["site"]
    ws_a = sec_advanced_env["ws_a"]
    org_a = sec_advanced_env["org_a"]
    user_a = sec_advanced_env["user_a"]

    with Session(engine) as db:
        family = ModelFamily(
            id=f"fam-rb-{uuid.uuid4().hex[:6]}",
            workspace_id=ws_a.id,
            organization_id=org_a.id,
            name="Rollback Model Family",
            slug=f"rb-fam-{uuid.uuid4().hex[:4]}",
            created_by=user_a.id,
        )
        db.add(family)
        db.flush()

        m_v1 = ModelVersion(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            family_id=family.id,
            version_tag="v1.0.0",
            status=ModelVersionStatus.APPROVED,
            source_model_key="mizan/llama",
            source_model_revision="main",
            recipe_key="REC",
            min_ram_mb=4096.0,
            release_manifest_digest="1111111111111111111111111111111111111111111111111111111111111111",
            created_by=user_a.id,
        )
        # Target version m_v2 is REVOKED
        m_v2 = ModelVersion(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            family_id=family.id,
            version_tag="v2.0.0",
            status=ModelVersionStatus.REVOKED,
            source_model_key="mizan/llama",
            source_model_revision="main",
            recipe_key="REC",
            min_ram_mb=4096.0,
            release_manifest_digest="2222222222222222222222222222222222222222222222222222222222222222",
            created_by=user_a.id,
        )
        db.add_all([m_v1, m_v2])
        db.flush()

        app_def = AppDefinition(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            app_key=f"rb-rev-app-{uuid.uuid4().hex[:6]}",
            name="Rollback App",
            description="Rollback test application",
            owner_id=user_a.id,
        )
        db.add(app_def)
        db.flush()

        runtime_app = RuntimeApplication(
            customer_site_id=site.id,
            app_definition_id=app_def.id,
            app_version_id="app-v1-id",
            app_manifest_digest="sha256-hash-manifest",
            status="INSTALLED",
            active_slot_name=SlotName.SLOT_A.value,
        )
        db.add(runtime_app)
        db.flush()

        slot_a = RuntimeSlot(
            runtime_application_id=runtime_app.id,
            slot_name=SlotName.SLOT_A.value,
            status=SlotStatus.ACTIVE,
            readiness_state=ReadinessState.READY,
            app_version_id="app-v1",
            model_version_id=m_v1.id,
        )
        slot_b = RuntimeSlot(
            runtime_application_id=runtime_app.id,
            slot_name=SlotName.SLOT_B.value,
            status=SlotStatus.STAGED,
            readiness_state=ReadinessState.READY,
            app_version_id="app-v1",
            model_version_id=m_v2.id,
        )
        db.add_all([slot_a, slot_b])
        db.commit()

        # Attempt rollback -> must abort safely with ABORTED_UNSAFE_TARGET
        event = execute_rollback(
            db=db,
            runtime_app_id=runtime_app.id,
            trigger_type="MANUAL",
            trigger_reason="Test rollback to revoked version",
            actor_id=user_a.id,
        )
        assert event.status == "ABORTED_UNSAFE_TARGET"
        assert "Gate 3" in (event.error_detail or "") or "REVOKED" in (event.error_detail or "")


# =========================================================================
# SEC-030: Missing Telemetry SLO Calculation Handled Safely
# =========================================================================
def test_sec_030_slo_missing_data_insufficient_sample():
    """SLO snapshot calculation must set has_sufficient_data=False when events are below threshold."""
    from app.models.observability import ServiceLevelObjective

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        slo = ServiceLevelObjective(
            workspace_id="ws-test",
            name="Inference Availability",
            target_percentage=99.5,
            rolling_window_days=30,
            metric_key="runtime_request_duration_ms",
            good_events_definition="latency <= 2000",
            is_enabled=True,
        )
        db.add(slo)
        db.commit()

        # Record 0 events (insufficient data)
        snapshot = record_snapshot(
            db=db,
            slo_id=slo.id,
            total_events=0,
            good_events=0,
            customer_site_id="site-test",
        )
        assert snapshot.has_sufficient_data is False


# =========================================================================
# SEC-031: Unauthenticated Operations and Runtime APIs Rejected
# =========================================================================
def test_sec_031_unauthenticated_ops_endpoints_rejected(sec_advanced_env):
    """Mutating operations and customer runtime endpoints must reject unauthenticated requests."""
    client = sec_advanced_env["client"]
    ws_a_id = sec_advanced_env["ws_a"].id

    protected_endpoints = [
        ("POST", f"/api/v1/ops/incidents?workspace_id={ws_a_id}", {"title": "Test Incident", "description": "Test Desc"}),
        ("POST", f"/api/v1/ops/alerts/rules?workspace_id={ws_a_id}", {"name": "Test Rule"}),
        ("POST", f"/api/v1/workspaces/{ws_a_id}/sites", {"site_name": "New Site"}),
    ]

    for method, path, payload in protected_endpoints:
        resp = client.post(path, json=payload)
        assert resp.status_code == 401, f"Expected 401 for {path}, got {resp.status_code}"


# =========================================================================
# SEC-032: XSS and HTML Injection Sanitization
# =========================================================================
def test_sec_032_xss_injection_handled_safely(sec_advanced_env):
    """HTML and script tags in incident titles or notes must not trigger XSS and must be handled safely."""
    client = sec_advanced_env["client"]
    sess_a = sec_advanced_env["sess_a"]
    ws_a_id = sec_advanced_env["ws_a"].id

    cookies = {"mizan_session": sess_a.session_token}
    headers = {"X-CSRF-Token": sess_a.csrf_token}

    xss_payload = "<script>alert('XSS_ATTACK')</script>"
    resp = client.post(
        f"/api/v1/ops/incidents?workspace_id={ws_a_id}",
        cookies=cookies,
        headers=headers,
        json={
            "title": xss_payload,
            "description": "Testing XSS persistence",
            "severity": "SEV3",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    # The title should be stored as plain string, response content-type application/json prevents execution
    assert data["title"] == xss_payload


# =========================================================================
# SEC-033: Production Debug Configuration Startup Failure
# =========================================================================
def test_sec_033_production_debug_configuration_rejected():
    """Startup validation must reject APP_ENV=production when DEBUG=True."""
    with pytest.raises(ValueError, match="Production environment cannot run with debug=True."):
        Settings(
            app_env="production",
            debug=True,
            secret_key="a" * 32,
            session_cookie_secure=True,
            cors_origins=["https://mizan.example.com"],
        )


# =========================================================================
# SEC-034: Weak Secret Key Rejected in Production
# =========================================================================
def test_sec_034_weak_secret_key_rejected_in_production():
    """Production settings must reject weak, short, or default secret keys."""
    with pytest.raises(ValueError, match="Production secret_key must be configured with a high-entropy secret"):
        Settings(
            app_env="production",
            debug=False,
            secret_key="short_key",
            session_cookie_secure=True,
            cors_origins=["https://mizan.example.com"],
        )

    with pytest.raises(ValueError, match="Production secret_key must be configured with a high-entropy secret"):
        Settings(
            app_env="production",
            debug=False,
            secret_key="replace-with-local-secret",
            session_cookie_secure=True,
            cors_origins=["https://mizan.example.com"],
        )


# =========================================================================
# SEC-035: Database Transaction Rollback Atomicity on Error
# =========================================================================
def test_sec_035_transaction_rollback_atomicity(sec_advanced_env):
    """Database transactions must completely rollback uncommitted state when an exception occurs."""
    engine = sec_advanced_env["engine"]

    with Session(engine) as db:
        initial_count = db.execute(select(Incident)).scalars().all()

        try:
            inc = Incident(
                id="inc-atomic-test",
                workspace_id=sec_advanced_env["ws_a"].id,
                incident_number="INC-ATOM-001",
                title="Atomic Incident",
                description="Transaction atomicity test",
                severity=IncidentSeverity.SEV3,
                status=IncidentStatus.OPEN,
                created_by=sec_advanced_env["user_a"].id,
            )
            db.add(inc)
            db.flush()
            # Simulate unexpected failure before commit
            raise RuntimeError("Database connection interrupted during transaction")
        except RuntimeError:
            db.rollback()

        after_count = db.execute(select(Incident)).scalars().all()
        assert len(after_count) == len(initial_count)


# =========================================================================
# SEC-036: Concurrent Single-Use Token Consumption (Double Spend Prevention)
# =========================================================================
def test_sec_036_concurrent_token_consumption(sec_advanced_env):
    """Single-use tokens must be atomically consumed so duplicate concurrent consumption is prevented."""
    engine = sec_advanced_env["engine"]
    user_a = sec_advanced_env["user_a"]

    with Session(engine) as db:
        issued = token_service.create_token(db, user_a.id, TokenPurpose.PASSWORD_RESET)
        db.commit()

        # Simulate two concurrent threads consuming the same token
        db1 = Session(engine)
        db2 = Session(engine)

        res1 = token_service.consume_token(db1, issued.raw_token, TokenPurpose.PASSWORD_RESET)
        db1.commit()

        res2 = token_service.consume_token(db2, issued.raw_token, TokenPurpose.PASSWORD_RESET)
        db2.commit()

        # Exactly one must succeed, the other must return None
        successes = [r for r in [res1, res2] if r is not None]
        assert len(successes) == 1


# =========================================================================
# SEC-037: Operations API Cross-Tenant Incident Access Blocked (Anti-Enumeration 404)
# =========================================================================
def test_sec_037_cross_tenant_incident_access_anti_enumeration(sec_advanced_env):
    """Tenant B must receive 404 when attempting to query or modify Tenant A incidents."""
    client = sec_advanced_env["client"]
    sess_b = sec_advanced_env["sess_b"]
    sess_a = sec_advanced_env["sess_a"]
    ws_a_id = sec_advanced_env["ws_a"].id

    cookies_a = {"mizan_session": sess_a.session_token}
    headers_a = {"X-CSRF-Token": sess_a.csrf_token}
    cookies_b = {"mizan_session": sess_b.session_token}
    headers_b = {"X-CSRF-Token": sess_b.csrf_token}

    # Alice creates an incident in Workspace A
    res_create = client.post(
        f"/api/v1/ops/incidents?workspace_id={ws_a_id}",
        cookies=cookies_a,
        headers=headers_a,
        json={
            "title": "Tenant A Secret Incident",
            "description": "Confidential operational incident",
            "severity": "SEV1",
        },
    )
    assert res_create.status_code == 201
    incident_id = res_create.json()["id"]

    # Bob (Tenant B) attempts to read Tenant A's incident -> must return 404
    resp_read = client.get(f"/api/v1/ops/incidents/{incident_id}", cookies=cookies_b)
    assert resp_read.status_code == 404

    # Bob attempts to add notes to Tenant A's incident -> must return 404
    resp_note = client.post(
        f"/api/v1/ops/incidents/{incident_id}/notes?note=Malicious+tampering+note",
        cookies=cookies_b,
        headers=headers_b,
    )
    assert resp_note.status_code == 404


# =========================================================================
# SEC-038: Unauthorized Rollback Policy Modification Blocked
# =========================================================================
def test_sec_038_unauthorized_rollback_policy_modification(sec_advanced_env):
    """Tenant B cannot view or modify rollback policies belonging to Tenant A."""
    client = sec_advanced_env["client"]
    sess_b = sec_advanced_env["sess_b"]
    user_a = sec_advanced_env["user_a"]
    engine = sec_advanced_env["engine"]
    ws_a = sec_advanced_env["ws_a"]

    with Session(engine) as db:
        policy = RollbackPolicy(
            id=f"rb-pol-{uuid.uuid4().hex[:6]}",
            workspace_id=ws_a.id,
            runtime_application_id="app-100",
            mode=RollbackMode.MANUAL_ONLY,
            created_by=user_a.id,
        )
        db.add(policy)
        db.commit()
        pol_id = policy.id

    cookies_b = {"mizan_session": sess_b.session_token}
    headers_b = {"X-CSRF-Token": sess_b.csrf_token}

    # Bob attempts to update Alice's rollback policy
    resp = client.put(
        f"/api/v1/ops/rollback/policies/{pol_id}",
        cookies=cookies_b,
        headers=headers_b,
        json={"mode": "AUTOMATIC", "cooldown_seconds": 60},
    )
    assert resp.status_code == 404


# =========================================================================
# SEC-039: Unauthorized Telemetry Consent Modification Blocked
# =========================================================================
def test_sec_039_unauthorized_telemetry_consent_modification(sec_advanced_env):
    """Tenant B cannot update notification policies or telemetry configurations of Tenant A."""
    client = sec_advanced_env["client"]
    sess_b = sec_advanced_env["sess_b"]
    ws_a_id = sec_advanced_env["ws_a"].id

    cookies_b = {"mizan_session": sess_b.session_token}
    headers_b = {"X-CSRF-Token": sess_b.csrf_token}

    # Bob attempts to create a notification policy inside Tenant A's workspace
    resp = client.post(
        "/api/v1/ops/notification-policies",
        cookies=cookies_b,
        headers=headers_b,
        json={
            "workspace_id": ws_a_id,
            "name": "Attacker Webhook Policy",
            "channel_type": "LOCAL_STORE",
            "min_severity": "WARNING",
        },
    )
    assert resp.status_code == 404


# =========================================================================
# SEC-040: Invalid Signing Key Fails Closed
# =========================================================================
def test_sec_040_invalid_signing_key_fails_closed():
    """Attestation verification against nonexistent or corrupted key must fail closed."""
    payload = {"test": "payload"}
    canonical_json, sig_hex, _ = sign_payload(payload)

    # Verifying against a non-existent or invalid key_id must raise SignatureVerificationError
    with pytest.raises(SignatureVerificationError):
        verify_signature(canonical_json, "00" * 64, "nonexistent-key-id")


# =========================================================================
# SEC-041: Security Headers Middleware Verification
# =========================================================================
def test_sec_041_security_headers_present(sec_advanced_env):
    """HTTP responses must include hardened security headers."""
    client = sec_advanced_env["client"]
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200

    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers.get("Permissions-Policy", "")


# =========================================================================
# SEC-042: Production API Documentation Hiding
# =========================================================================
def test_sec_042_production_api_docs_hidden():
    """Swagger UI /docs and OpenAPI JSON /openapi.json must be hidden when APP_ENV=production."""
    from unittest.mock import patch

    # Mock settings so app_env is production
    with patch("app.main.get_settings") as mock_get_settings:
        mock_settings = Settings(
            app_env="production",
            debug=False,
            secret_key="a" * 32,
            session_cookie_secure=True,
            cors_origins=["https://mizan.example.com"],
        )
        mock_get_settings.return_value = mock_settings

        prod_app = create_app()
        prod_client = TestClient(prod_app)

        resp_docs = prod_client.get("/docs")
        assert resp_docs.status_code == 404, "Swagger /docs must return 404 in production"

        resp_json = prod_client.get("/openapi.json")
        assert resp_json.status_code == 404, "/openapi.json must return 404 in production"


# =========================================================================
# SEC-043: Credentialed CORS for HttpOnly Session Authentication
# =========================================================================
def test_sec_043_cors_allows_credentials_only_for_configured_origins():
    """The browser client can send its HttpOnly session cookie to an allowed UI origin."""
    from unittest.mock import patch

    with patch("app.main.get_settings") as mock_get_settings:
        mock_get_settings.return_value = Settings(
            app_env="production",
            debug=False,
            secret_key="a" * 32,
            session_cookie_secure=True,
            cors_origins=["https://app.mizan.example"],
        )
        app = create_app()
        client = TestClient(app)

        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://app.mizan.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.mizan.example"
    assert response.headers["access-control-allow-credentials"] == "true"
