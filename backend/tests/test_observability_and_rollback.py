"""Comprehensive test suite for Milestone 14: Production Telemetry, Monitoring, Metrics,
SLOs, Alerting, Incident Management & Automated Rollback.

Covers Scenarios A through I:
- Scenario A: Standard Metrics Collection, Cardinaility Budgeting & Prometheus Exposition.
- Scenario B: Privacy Filter, Prompt Scrubbing, PII Masking & Assertion Verification.
- Scenario C: Alert Evaluation, Consecutive Breaches, State Machine & Operator Ack.
- Scenario D: Alert Silence Windows and Primary Outage Alert Inhibition.
- Scenario E: Notification Routing and Webhook SSRF Attack Prevention.
- Scenario F: SLI Calculation, Error Budget Burn Down, and Missing Data Handling.
- Scenario G: Post-Activation Regression Detection on Newly Activated Slots.
- Scenario H: Automated Rollback, Gate 3 Verification, Golden Tests, and Anti-Flapping.
- Scenario I: Revoked Release Rollback Blocking and Target Release Safety.
- Offline Local Monitoring and Zero Cost Spend Policy Verification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import create_app
from app.models.artifact_registry import (
    Gate3Approval,
    Gate3Decision,
    Gate3Revocation,
    ModelFamily,
    ModelFamilyStatus,
    ModelVersion,
    ModelVersionStatus,
)
from app.models.catalog import AppDefinition, AppVersion
from app.models.identity import AccountStatus, User
from app.models.observability import (
    AlertSeverity,
    AlertStatus,
    IncidentSeverity,
    IncidentStatus,
    RollbackMode,
)
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.models.runtime import (
    CustomerSite,
    GoldenTestOutcome,
    ReadinessState,
    RuntimeApplication,
    RuntimeSlot,
    SiteStatus,
    SlotName,
    SlotStatus,
)
from app.modules.alerting.alert_evaluator import (
    acknowledge_alert,
    evaluate_rule,
    list_alert_instances,
)
from app.modules.alerting.alert_inhibition import apply_alert_inhibition
from app.modules.alerting.alert_rule_registry import (
    create_alert_rule,
)
from app.modules.alerting.alert_silence_service import (
    create_alert_silence,
    is_alert_silenced,
)
from app.modules.alerting.notification_router import (
    create_notification_policy,
    dispatch_alert_notification,
    validate_webhook_url,
)
from app.modules.alerting.schemas import (
    AlertRuleCreate,
    AlertSilenceCreate,
    NotificationPolicyCreate,
)
from app.modules.auth.services import session_service
from app.modules.incidents.incident_service import (
    add_incident_note,
    create_incident,
    get_incident_detail,
    update_incident,
)
from app.modules.incidents.schemas import IncidentCreate, IncidentUpdate
from app.modules.observability.event_journal import (
    list_operational_events,
    record_operational_event,
)
from app.modules.observability.instrumentation import (
    record_hardware_snapshot,
    record_inference_tokens,
    record_runtime_request,
    record_site_agent_heartbeat,
    record_slot_state,
)
from app.modules.observability.metric_registry import metric_registry
from app.modules.observability.prometheus_exporter import export_prometheus_metrics
from app.modules.observability.schemas import (
    OperationalEventCreate,
    TelemetryConsentUpdateRequest,
)
from app.modules.observability.telemetry_config_service import (
    get_or_create_telemetry_config,
    update_telemetry_consent,
)
from app.modules.observability.telemetry_privacy import (
    assert_no_privacy_violation,
    sanitize_event_payload,
    validate_and_sanitize_labels,
)
from app.modules.rollback.regression_detector import detect_post_activation_regression
from app.modules.rollback.rollback_eligibility import check_rollback_eligibility
from app.modules.rollback.rollback_executor import execute_rollback, list_rollback_history
from app.modules.rollback.rollback_policy_service import (
    get_or_create_rollback_policy,
    update_rollback_policy,
)
from app.modules.rollback.schemas import RollbackPolicyUpdate
from app.modules.slo.schemas import SloCreate
from app.modules.slo.sli_calculator import compute_sli_and_budget
from app.modules.slo.slo_service import create_slo, record_snapshot


@pytest.fixture
def db() -> Session:
    """Provide a clean SQLAlchemy session."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db: Session) -> TestClient:
    """FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def test_setup(db: Session) -> dict:
    """Seed base organization, workspace, operator user, application, and model versions."""
    now = datetime.now(UTC)
    uid = uuid.uuid4().hex[:8]

    user = User(
        id=f"user-ops-{uid}",
        email=f"ops_{uid}@test.mizan.ai",
        normalized_email=f"ops_{uid}@test.mizan.ai",
        full_name="Operations Engineer",
        password_hash="test_hash_safe",
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()

    org = Organization(
        id=f"org-{uid}",
        name=f"Ops Org {uid}",
        slug=f"ops-org-{uid}",
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    db.flush()

    db.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=OrganizationRole.OWNER,
            created_at=now,
            updated_at=now,
        )
    )

    ws = Workspace(
        id=f"ws-{uid}",
        organization_id=org.id,
        name=f"Ops Workspace {uid}",
        slug=f"ops-ws-{uid}",
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(ws)
    db.flush()

    db.add(
        WorkspaceMembership(
            workspace_id=ws.id,
            user_id=user.id,
            role=WorkspaceRole.WORKSPACE_OWNER,
            created_at=now,
            updated_at=now,
        )
    )

    site = CustomerSite(
        organization_id=org.id,
        workspace_id=ws.id,
        site_key=f"site-{uid}",
        site_name="Production Customer Site",
        status=SiteStatus.ACTIVE,
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(site)
    db.flush()

    app_def = AppDefinition(
        organization_id=org.id,
        workspace_id=ws.id,
        app_key=f"app-{uid}",
        name="Production Copilot",
        description="Production enterprise copilot application",
        owner_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(app_def)
    db.flush()

    app_v1 = AppVersion(
        app_definition_id=app_def.id,
        version_tag="v1.0.0",
        description="Production app v1",
        manifest_digest="app_digest_v1",
        created_by=user.id,
        created_at=now,
    )
    db.add(app_v1)
    db.flush()

    family = ModelFamily(
        organization_id=org.id,
        workspace_id=ws.id,
        name=f"Llama-Ops-{uid}",
        slug=f"llama-ops-{uid}",
        task_type="TEXT_GENERATION",
        created_by=user.id,
        status=ModelFamilyStatus.ACTIVE,
        created_at=now,
    )
    db.add(family)
    db.flush()

    # V1: Last-Known-Good Release
    m_v1 = ModelVersion(
        organization_id=org.id,
        workspace_id=ws.id,
        family_id=family.id,
        version_tag="v1.0.0",
        description="Gate 3 Approved Release",
        status=ModelVersionStatus.APPROVED,
        source_model_key="meta-llama/Llama-3-8B-Instruct",
        source_model_revision="main",
        recipe_key="LORA_FINETUNE_SFT_V1",
        min_ram_mb=4096.0,
        min_vram_mb=0.0,
        release_manifest_digest="1111111111111111111111111111111111111111111111111111111111111111",
        created_by=user.id,
        created_at=now,
    )
    db.add(m_v1)
    db.flush()

    g3_v1 = Gate3Approval(
        organization_id=org.id,
        workspace_id=ws.id,
        model_version_id=m_v1.id,
        release_manifest_digest=m_v1.release_manifest_digest,
        decision=Gate3Decision.APPROVED,
        decision_reason="Gate 3 signed off for v1 production",
        reviewer_user_id=user.id,
        reviewer_role_snapshot="WORKSPACE_OWNER",
        signing_key_id="mock_key_v1",
        approval_signature="mock_sig_v1",
        canonical_payload="{}",
        reviewed_at=now,
    )
    db.add(g3_v1)

    # V2: Candidate / Regression Release
    m_v2 = ModelVersion(
        organization_id=org.id,
        workspace_id=ws.id,
        family_id=family.id,
        version_tag="v2.0.0",
        description="Gate 3 Staged Release",
        status=ModelVersionStatus.APPROVED,
        source_model_key="meta-llama/Llama-3-8B-Instruct",
        source_model_revision="main",
        recipe_key="LORA_FINETUNE_SFT_V1",
        min_ram_mb=4096.0,
        min_vram_mb=0.0,
        release_manifest_digest="2222222222222222222222222222222222222222222222222222222222222222",
        created_by=user.id,
        created_at=now,
    )
    db.add(m_v2)
    db.flush()

    g3_v2 = Gate3Approval(
        organization_id=org.id,
        workspace_id=ws.id,
        model_version_id=m_v2.id,
        release_manifest_digest=m_v2.release_manifest_digest,
        decision=Gate3Decision.APPROVED,
        decision_reason="Gate 3 signed off for v2 staging",
        reviewer_user_id=user.id,
        reviewer_role_snapshot="WORKSPACE_OWNER",
        signing_key_id="mock_key_v2",
        approval_signature="mock_sig_v2",
        canonical_payload="{}",
        reviewed_at=now,
    )
    db.add(g3_v2)

    runtime_app = RuntimeApplication(
        customer_site_id=site.id,
        app_definition_id=app_def.id,
        app_version_id=app_v1.id,
        app_manifest_digest="app_digest_v1",
        active_slot_name=SlotName.SLOT_A.value,
        installed_at=now,
        updated_at=now,
    )
    db.add(runtime_app)
    db.flush()

    slot_a = RuntimeSlot(
        runtime_application_id=runtime_app.id,
        slot_name=SlotName.SLOT_A,
        app_version_id=app_v1.id,
        model_version_id=m_v1.id,
        release_manifest_digest=m_v1.release_manifest_digest,
        status=SlotStatus.ACTIVE,
        readiness_state=ReadinessState.READY,
        golden_test_status=GoldenTestOutcome.PASSED,
        engine_adapter_key="MOCK_ENGINE",
        activated_at=now,
        created_at=now,
        updated_at=now,
    )
    slot_b = RuntimeSlot(
        runtime_application_id=runtime_app.id,
        slot_name=SlotName.SLOT_B,
        app_version_id=app_v1.id,
        model_version_id=m_v2.id,
        release_manifest_digest=m_v2.release_manifest_digest,
        status=SlotStatus.STAGED,
        readiness_state=ReadinessState.LOADING,
        golden_test_status=GoldenTestOutcome.PASSED,
        engine_adapter_key="MOCK_ENGINE",
        staged_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add_all([slot_a, slot_b])
    db.commit()

    # Authenticate session
    auth_session = session_service.create_session(db, user_id=user.id)
    token = auth_session.session_token

    return {
        "user": user,
        "org": org,
        "workspace": ws,
        "site": site,
        "app_def": app_def,
        "runtime_app": runtime_app,
        "slot_a": slot_a,
        "slot_b": slot_b,
        "m_v1": m_v1,
        "m_v2": m_v2,
        "token": token,
    }


# =========================================================================
# Scenario A: Standard Metrics Collection, Cardinality & Prometheus Format
# =========================================================================


def test_scenario_a_metrics_collection_and_prometheus_export(client: TestClient, test_setup: dict) -> None:
    """Verify in-memory metric recording, cardinality budgeting, and standard Prometheus text exposition."""
    metric_registry.reset()

    # Record operational telemetry
    record_runtime_request(
        endpoint="/v1/chat/completions",
        status_code=200,
        duration_ms=45.2,
        slot_name="SLOT_A",
        engine="MOCK_ENGINE",
    )
    record_runtime_request(
        endpoint="/v1/chat/completions",
        status_code=500,
        duration_ms=120.0,
        slot_name="SLOT_A",
        engine="MOCK_ENGINE",
    )
    record_inference_tokens(prompt_tokens=150, completion_tokens=85, slot_name="SLOT_A")
    record_hardware_snapshot(
        site_id="site-001",
        cpu_pct=34.5,
        memory_bytes=2147483648,
        disk_bytes=10737418240,
        vram_bytes=8589934592,
    )
    record_slot_state(
        site_id="site-001",
        slot_name="SLOT_A",
        readiness="READY",
        model_version_id="mv-123",
        engine="MOCK_ENGINE",
        golden_status="PASSED",
    )
    record_site_agent_heartbeat(site_id="site-001", is_alive=True)

    # 1. Assert registry values
    total_reqs = metric_registry.get_counter_value("runtime_requests_total")
    assert total_reqs == 2.0

    prompt_toks = metric_registry.get_counter_value("runtime_inference_tokens_total", {"type": "prompt", "slot_name": "SLOT_A"})
    assert prompt_toks == 150.0

    cpu_val = metric_registry.get_gauge_value("runtime_cpu_usage_percent", {"site_id": "site-001"})
    assert cpu_val == 34.5

    # 2. Assert Prometheus text exposition format
    prom_text = export_prometheus_metrics()
    assert "# HELP runtime_requests_total" in prom_text
    assert "# TYPE runtime_requests_total counter" in prom_text
    assert 'runtime_requests_total{endpoint="/v1/chat/completions"' in prom_text
    assert "# HELP runtime_request_duration_ms" in prom_text
    assert "# TYPE runtime_request_duration_ms histogram" in prom_text
    assert "runtime_request_duration_ms_bucket{" in prom_text
    assert "runtime_request_duration_ms_sum" in prom_text
    assert "runtime_request_duration_ms_count" in prom_text
    assert "runtime_cpu_usage_percent" in prom_text

    # 3. Test HTTP Prometheus scraper endpoint
    resp = client.get("/api/v1/ops/metrics/prometheus")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "runtime_requests_total" in resp.text

    # 4. Test HTTP Metrics Summary endpoint
    summary_resp = client.get("/api/v1/ops/metrics/summary")
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    assert data["requests_total"] == 2
    assert data["cpu_usage_percent"] == 34.5
    assert data["readiness_state"] == "READY"


# =========================================================================
# Scenario B: Privacy Filter, Prompt Scrubbing & Assertion Verification
# =========================================================================


def test_scenario_b_privacy_filter_and_redaction(db: Session, test_setup: dict) -> None:
    """Verify strict redaction of prompts, documents, credentials, and PII."""
    raw_payload = {
        "prompt": "SELECT * FROM users WHERE ssn = '123-45-6789';",
        "user_prompt": "What is our internal corporate strategy for Q4?",
        "messages": [{"role": "user", "content": "Sensitive question"}],
        "completion": "Our confidential revenue was $50M.",
        "document_text": "Private proprietary patent details...",
        "api_key": "sk-live-secret-test-key-12345",
        "secret": "top-secret-token",
        "normal_metric_name": "batch_processor",
        "nested_details": {
            "token": "bearer-token-val",
            "contact": "operator@mizan.ai",
            "safe_counter": 42,
        },
    }

    # 1. Sanitize payload
    sanitized = sanitize_event_payload(raw_payload)

    assert sanitized["prompt"] == "[REDACTED_PRIVACY]"
    assert sanitized["user_prompt"] == "[REDACTED_PRIVACY]"
    assert sanitized["messages"] == "[REDACTED_PRIVACY]"
    assert sanitized["completion"] == "[REDACTED_PRIVACY]"
    assert sanitized["document_text"] == "[REDACTED_PRIVACY]"
    assert sanitized["api_key"] == "[REDACTED_PRIVACY]"
    assert sanitized["secret"] == "[REDACTED_PRIVACY]"
    assert sanitized["nested_details"]["token"] == "[REDACTED_PRIVACY]"
    assert sanitized["nested_details"]["contact"] == "[REDACTED_EMAIL]"
    assert sanitized["nested_details"]["safe_counter"] == 42
    assert sanitized["normal_metric_name"] == "batch_processor"

    # 2. Privacy invariant assertion
    assert_no_privacy_violation(sanitized)  # Should not raise

    with pytest.raises(ValueError, match="Privacy invariant violation"):
        assert_no_privacy_violation({"user_prompt": "cleartext unscrubbed prompt"})

    # 3. Label cardinality control: verify unknown or high-cardinality keys are stripped
    labels = {
        "service": "runtime",
        "endpoint": "/v1/chat/completions",
        "user_id": "user-12345-high-cardinality",
        "prompt_hash": "hash-abcd",
        "customer_email": "ceo@customer.com",
    }
    allowed = ["service", "endpoint", "status_class"]
    clean_labels = validate_and_sanitize_labels("runtime_requests_total", labels, allowed)
    assert "user_id" not in clean_labels
    assert "prompt_hash" not in clean_labels
    assert "customer_email" not in clean_labels
    assert clean_labels["service"] == "runtime"
    assert clean_labels["endpoint"] == "/v1/chat/completions"

    # 4. Test recording into Operational Event Journal
    event_read = record_operational_event(
        db=db,
        payload=OperationalEventCreate(
            workspace_id=test_setup["workspace"].id,
            customer_site_id=test_setup["site"].id,
            event_type="RUNTIME_START",
            severity="INFO",
            summary="Runtime process initialized",
            payload=raw_payload,
        ),
    )
    assert event_read.payload["prompt"] == "[REDACTED_PRIVACY]"

    # Query events
    events = list_operational_events(db, workspace_id=test_setup["workspace"].id)
    assert len(events) >= 1
    assert events[0].event_type == "RUNTIME_START"


# =========================================================================
# Scenario C: Alert Evaluation, Consecutive Breaches, State Machine & Ack
# =========================================================================


def test_scenario_c_alert_evaluation_and_lifecycle(db: Session, test_setup: dict) -> None:
    """Verify alert rule evaluation, consecutive breach detection, FIRING, ACK, and RESOLUTION."""
    ws_id = test_setup["workspace"].id
    user_id = test_setup["user"].id

    # Create alert rule requiring 2 consecutive breaches
    rule_read = create_alert_rule(
        db=db,
        workspace_id=ws_id,
        payload=AlertRuleCreate(
            name="ErrorRateBreachTest",
            metric_key="runtime_requests_total",
            condition_operator="GT",
            threshold=5.0,
            duration_seconds=60,
            consecutive_breaches=2,
            severity=AlertSeverity.CRITICAL,
        ),
        actor_id=user_id,
    )

    from app.models.observability import AlertRule
    rule_obj = db.execute(select(AlertRule).where(AlertRule.id == rule_read.id)).scalar_one()

    # Breach 1: Value 8.0 > 5.0 (First breach -> PENDING)
    inst_1 = evaluate_rule(db, rule_obj, current_value=8.0, customer_site_id=test_setup["site"].id)
    assert inst_1.status == AlertStatus.PENDING
    assert inst_1.breach_count == 1

    # Breach 2: Value 9.5 > 5.0 (Second breach -> FIRING)
    inst_2 = evaluate_rule(db, rule_obj, current_value=9.5, customer_site_id=test_setup["site"].id)
    assert inst_2.status == AlertStatus.FIRING
    assert inst_2.breach_count == 2
    assert inst_2.fired_at is not None

    # Operator Acknowledgement
    inst_ack = acknowledge_alert(db, inst_2.id, actor_id=user_id, comment="Investigating high error rate")
    assert inst_ack.status == AlertStatus.ACKNOWLEDGED
    assert inst_ack.acknowledged_by == user_id

    # Recovery: Value drops to 2.0 <= 5.0 -> RESOLVED
    inst_res = evaluate_rule(db, rule_obj, current_value=2.0, customer_site_id=test_setup["site"].id)
    assert inst_res.status == AlertStatus.RESOLVED
    assert inst_res.resolved_at is not None
    assert inst_res.breach_count == 0


# =========================================================================
# Scenario D: Alert Silence Windows and Primary Outage Alert Inhibition
# =========================================================================


def test_scenario_d_alert_silence_and_inhibition(db: Session, test_setup: dict) -> None:
    """Verify alert silencing windows and primary outage alert inhibition."""
    from app.models.observability import AlertRule

    ws_id = test_setup["workspace"].id
    user_id = test_setup["user"].id
    site_id = test_setup["site"].id
    now = datetime.now(UTC)

    # 1. Test Alert Silence
    rule_read = create_alert_rule(
        db=db,
        workspace_id=ws_id,
        payload=AlertRuleCreate(
            name="LatencyWarningSilenceTest",
            metric_key="runtime_request_duration_ms",
            condition_operator="GT",
            threshold=100.0,
            consecutive_breaches=1,
            severity=AlertSeverity.WARNING,
        ),
        actor_id=user_id,
    )
    rule_obj = db.execute(db.query(AlertRule).filter_by(id=rule_read.id).statement).scalar_one()

    # Active silence covering current time
    create_alert_silence(
        db=db,
        workspace_id=ws_id,
        payload=AlertSilenceCreate(
            rule_id=rule_read.id,
            customer_site_id=site_id,
            starts_at=now - timedelta(minutes=10),
            ends_at=now + timedelta(minutes=50),
            reason="Scheduled maintenance window",
        ),
        actor_id=user_id,
    )

    assert is_alert_silenced(db, rule_read.id, site_id) is True

    # Evaluate breaching metric: status must become SILENCED, NOT FIRING
    inst_silenced = evaluate_rule(db, rule_obj, current_value=250.0, customer_site_id=site_id)
    assert inst_silenced.status == AlertStatus.SILENCED

    # 2. Test Alert Inhibition (Primary Outage suppresses Secondary Symptom)
    # Primary outage: SlotUnhealthyOrUnready
    primary_rule = create_alert_rule(
        db=db,
        workspace_id=ws_id,
        payload=AlertRuleCreate(
            name="SlotUnhealthyOrUnready",
            metric_key="runtime_readiness_state",
            condition_operator="LT",
            threshold=1.0,
            consecutive_breaches=1,
            severity=AlertSeverity.CRITICAL,
        ),
        actor_id=user_id,
    )
    # Secondary symptom: HighInferenceLatencyP95
    sec_rule = create_alert_rule(
        db=db,
        workspace_id=ws_id,
        payload=AlertRuleCreate(
            name="HighInferenceLatencyP95",
            metric_key="runtime_request_duration_ms",
            condition_operator="GT",
            threshold=500.0,
            consecutive_breaches=1,
            severity=AlertSeverity.WARNING,
        ),
        actor_id=user_id,
    )
    primary_obj = db.execute(db.query(AlertRule).filter_by(id=primary_rule.id).statement).scalar_one()
    sec_obj = db.execute(db.query(AlertRule).filter_by(id=sec_rule.id).statement).scalar_one()

    # Both breach
    evaluate_rule(db, primary_obj, current_value=0.0, customer_site_id=site_id)
    evaluate_rule(db, sec_obj, current_value=1500.0, customer_site_id=site_id)

    # Apply inhibition
    suppressed_ids = apply_alert_inhibition(db, site_id)
    assert len(suppressed_ids) >= 1

    instances = list_alert_instances(db, customer_site_id=site_id)
    sec_inst = next(i for i in instances if i.rule_id == sec_rule.id)
    assert sec_inst.status == AlertStatus.SUPPRESSED


# =========================================================================
# Scenario E: Notification Routing and Webhook SSRF Attack Prevention
# =========================================================================


def test_scenario_e_notification_routing_and_ssrf_protection(db: Session, test_setup: dict) -> None:
    """Verify local notification dispatch and strict SSRF rejection of internal/private targets."""
    ws_id = test_setup["workspace"].id

    # 1. Local store notification policy
    policy = create_notification_policy(
        db=db,
        workspace_id=ws_id,
        payload=NotificationPolicyCreate(
            name="Local Store Delivery",
            channel_type="LOCAL_STORE",
            min_severity=AlertSeverity.WARNING,
        ),
    )
    from app.models.observability import AlertInstance
    inst = db.execute(select(AlertInstance)).scalars().first()
    if not inst:
        # Create a mock instance
        from app.models.observability import AlertRule
        rule = db.execute(select(AlertRule)).scalars().first()
        inst = evaluate_rule(db, rule, current_value=999.0)

    from app.models.observability import NotificationPolicy
    policy_obj = db.execute(select(NotificationPolicy).where(NotificationPolicy.id == policy.id)).scalar_one()
    delivery = dispatch_alert_notification(db, inst, policy_obj)
    assert delivery.status == "DELIVERED"
    assert "Alert Notification [LOCAL_STORE]" in delivery.payload_summary

    # 2. SSRF Protection: Loopback and metadata rejection
    ssrf_malicious_urls = [
        "http://127.0.0.1:8080/hook",
        "http://localhost:8000/webhook",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/api/v1",
        "http://192.168.1.100/admin",
        "http://172.16.0.1/internal",
        "ftp://example.com/bad_scheme",
    ]

    for bad_url in ssrf_malicious_urls:
        with pytest.raises(ValueError, match="(SSRF violation|Invalid webhook URL)"):
            validate_webhook_url(bad_url, allow_test_hosts=False)


# =========================================================================
# Scenario F: SLI Calculation, Error Budget Burn Down, and Missing Data Handling
# =========================================================================


def test_scenario_f_sli_calculation_and_error_budget(db: Session, test_setup: dict) -> None:
    """Verify SLI calculation, error budget tracking, and missing data detection."""
    ws_id = test_setup["workspace"].id

    # 1. Mathematical calculation tests
    # 10,000 requests, 9,990 good, 10 errors -> 99.9% SLI vs 99.5% target
    sli, budget_rem, has_data, burn_rate = compute_sli_and_budget(
        target_percentage=99.5,
        total_events=10000,
        good_events=9990,
    )
    assert has_data is True
    assert sli == 99.9
    assert budget_rem == 80.0  # 10 bad out of 50 allowed = 20% consumed, 80% remaining
    assert burn_rate == 0.2

    # Missing Telemetry Handling: 0 events must NOT be reported as 100% healthy
    sli_empty, budget_empty, has_data_empty, _ = compute_sli_and_budget(
        target_percentage=99.5,
        total_events=0,
        good_events=0,
    )
    assert has_data_empty is False  # Marked as insufficient data

    # 100% budget consumption: 100 errors out of 50 allowed
    _, budget_exhausted, _, burn_rate_high = compute_sli_and_budget(
        target_percentage=99.5,
        total_events=10000,
        good_events=9900,
    )
    assert budget_exhausted == 0.0
    assert burn_rate_high == 2.0  # 2x allowed consumption rate

    # 2. Database SLO and Snapshot persistence
    slo = create_slo(
        db=db,
        workspace_id=ws_id,
        payload=SloCreate(
            name="ApiAvailability995",
            target_percentage=99.5,
            rolling_window_days=30,
            metric_key="runtime_requests_total",
            good_events_definition="status_code < 500",
        ),
    )

    snapshot = record_snapshot(
        db=db,
        slo_id=slo.id,
        total_events=5000,
        good_events=4995,
        customer_site_id=test_setup["site"].id,
    )
    assert snapshot.current_sli_percentage == 99.9
    assert snapshot.error_budget_remaining_percentage == 80.0
    assert snapshot.has_sufficient_data is True


# =========================================================================
# Scenario G: Post-Activation Regression Detection
# =========================================================================


def test_scenario_g_post_activation_regression_detection(db: Session, test_setup: dict) -> None:
    """Verify regression detector flags sustained post-activation error or latency breaches."""
    runtime_app = test_setup["runtime_app"]
    ws_id = test_setup["workspace"].id

    policy_read = get_or_create_rollback_policy(db, ws_id, runtime_app.id)
    from app.models.observability import RollbackPolicy
    policy = db.execute(select(RollbackPolicy).where(RollbackPolicy.id == policy_read.id)).scalar_one()

    # 1. Normal state: no regression
    has_reg_0, _ = detect_post_activation_regression(db, runtime_app.id, policy)
    assert has_reg_0 is False

    # 2. Simulate latency spike: record high latency in metric histogram
    metric_registry.record_histogram("runtime_request_duration_ms", 3500.0)
    metric_registry.record_counter("runtime_requests_total", 10.0)

    has_reg_lat, reason_lat = detect_post_activation_regression(db, runtime_app.id, policy)
    assert has_reg_lat is True
    assert "latency" in reason_lat.lower()

    # 3. Simulate critical alert firing
    from app.models.observability import AlertRule
    crit_rule = create_alert_rule(
        db=db,
        workspace_id=ws_id,
        payload=AlertRuleCreate(
            name="CriticalHardwareFault",
            metric_key="runtime_cpu_usage_percent",
            threshold=95.0,
            consecutive_breaches=1,
            severity=AlertSeverity.CRITICAL,
        ),
        actor_id=test_setup["user"].id,
    )
    crit_obj = db.execute(select(AlertRule).where(AlertRule.id == crit_rule.id)).scalar_one()
    evaluate_rule(db, crit_obj, current_value=99.0, customer_site_id=test_setup["site"].id)

    has_reg_crit, reason_crit = detect_post_activation_regression(db, runtime_app.id, policy)
    assert has_reg_crit is True
    assert "critical alert" in reason_crit.lower()


# =========================================================================
# Scenario H: Automated Rollback, Gate 3 Verification, Golden Tests, Anti-Flapping
# =========================================================================


def test_scenario_h_automated_rollback_and_anti_flapping(db: Session, test_setup: dict) -> None:
    """Verify atomic rollback to verified release, post-rollback golden tests, and anti-flapping abort."""
    runtime_app = test_setup["runtime_app"]
    ws_id = test_setup["workspace"].id
    user_id = test_setup["user"].id

    # Configure policy to AUTOMATIC
    policy_read = get_or_create_rollback_policy(db, ws_id, runtime_app.id)
    update_rollback_policy(
        db,
        policy_read.id,
        RollbackPolicyUpdate(mode=RollbackMode.AUTOMATIC, cooldown_seconds=600),
    )

    # 1. Eligibility Check
    eligibility = check_rollback_eligibility(db, runtime_app.id)
    assert eligibility.is_eligible is True
    assert eligibility.current_slot_name == "SLOT_A"
    assert eligibility.target_slot_name == "SLOT_B"
    assert eligibility.target_is_gate3_approved is True
    assert eligibility.target_is_revoked is False
    assert eligibility.flapping_detected is False

    # 2. Execute Rollback (from SLOT_A to SLOT_B)
    exec_event = execute_rollback(
        db=db,
        runtime_app_id=runtime_app.id,
        trigger_type="AUTOMATIC_REGRESSION",
        trigger_reason="Post-activation latency regression sustained",
        actor_id=user_id,
    )
    assert exec_event.status == "SUCCESS"
    assert exec_event.from_slot_name == "SLOT_A"
    assert exec_event.to_slot_name == "SLOT_B"
    assert exec_event.verification_passed is True

    # Check slot state
    db.refresh(runtime_app)
    assert runtime_app.active_slot_name == "SLOT_B"

    # Check audit history
    history = list_rollback_history(db, runtime_app.id)
    assert len(history) >= 1
    assert history[0].status == "SUCCESS"

    # 3. Anti-Flapping: Immediate subsequent rollback attempt is blocked by cooldown
    exec_flapping = execute_rollback(
        db=db,
        runtime_app_id=runtime_app.id,
        trigger_type="AUTOMATIC_REGRESSION",
        trigger_reason="Repeated trigger attempt within cooldown",
        actor_id=user_id,
    )
    assert exec_flapping.status == "ABORTED_FLAPPING"
    assert "Cooldown in effect" in (exec_flapping.error_detail or "")


# =========================================================================
# Scenario I: Revoked Release Rollback Prevention
# =========================================================================


def test_scenario_i_revoked_release_rollback_prevention(db: Session, test_setup: dict) -> None:
    """Verify that an attempt to rollback to a revoked release is strictly blocked."""
    runtime_app = test_setup["runtime_app"]
    user_id = test_setup["user"].id

    # The target slot (SLOT_B) has model version m_v2
    # Simulate emergency Gate 3 Revocation of m_v2
    g3_app = db.execute(select(Gate3Approval).where(Gate3Approval.model_version_id == test_setup["m_v2"].id)).scalar_one()
    revocation = Gate3Revocation(
        organization_id=test_setup["org"].id,
        workspace_id=test_setup["workspace"].id,
        model_version_id=test_setup["m_v2"].id,
        gate3_approval_id=g3_app.id,
        revoked_by_user_id=user_id,
        revoked_by_role_snapshot="WORKSPACE_OWNER",
        revocation_reason="Security vulnerability discovered in model weights",
        revoked_at=datetime.now(UTC),
    )
    db.add(revocation)
    db.commit()

    # 1. Check eligibility: must fail due to revocation
    eligibility = check_rollback_eligibility(db, runtime_app.id)
    assert eligibility.is_eligible is False
    assert eligibility.target_is_revoked is True
    assert any("REVOKED" in r for r in eligibility.reasons)

    # 2. Attempt rollback: must abort safely with ABORTED_UNSAFE_TARGET
    exec_event = execute_rollback(
        db=db,
        runtime_app_id=runtime_app.id,
        trigger_type="MANUAL",
        trigger_reason="Attempted rollback to compromised release",
        actor_id=user_id,
    )
    assert exec_event.status == "ABORTED_UNSAFE_TARGET"
    assert "REVOKED" in (exec_event.error_detail or "")


# =========================================================================
# Incident Management & Operational Timeline
# =========================================================================


def test_incident_management_lifecycle(db: Session, test_setup: dict) -> None:
    """Verify incident creation, sequential numbering, timeline audit, and resolution."""
    ws_id = test_setup["workspace"].id
    user_id = test_setup["user"].id

    # Create incident
    inc = create_incident(
        db=db,
        workspace_id=ws_id,
        payload=IncidentCreate(
            title="Production Latency Degradation",
            description="P95 latency breached 2000ms threshold following traffic spike",
            severity=IncidentSeverity.SEV2,
            customer_site_id=test_setup["site"].id,
            runtime_application_id=test_setup["runtime_app"].id,
        ),
        actor_id=user_id,
    )
    assert inc.incident_number == 1
    assert inc.status == IncidentStatus.OPEN
    assert len(inc.events) == 1
    assert inc.events[0].event_type == "STATUS_CHANGE"

    # Add investigative note
    note_event = add_incident_note(
        db=db,
        incident_id=inc.id,
        note="Identified GPU KV-cache thrashing under high concurrency.",
        actor_id=user_id,
    )
    assert note_event.event_type == "NOTE"

    # Transition to MITIGATING and RESOLVED
    inc_mitigated = update_incident(
        db=db,
        incident_id=inc.id,
        payload=IncidentUpdate(status=IncidentStatus.MITIGATING, status_change_note="Rolled back to verified release"),
        actor_id=user_id,
    )
    assert inc_mitigated.status == IncidentStatus.MITIGATING

    inc_resolved = update_incident(
        db=db,
        incident_id=inc.id,
        payload=IncidentUpdate(status=IncidentStatus.RESOLVED, status_change_note="Latency normal; golden tests passed"),
        actor_id=user_id,
    )
    assert inc_resolved.status == IncidentStatus.RESOLVED
    assert inc_resolved.resolved_at is not None

    # Retrieve full detail and verify timeline order
    detail = get_incident_detail(db, inc.id)
    assert detail is not None
    assert len(detail.events) == 4  # OPEN -> NOTE -> MITIGATING -> RESOLVED


# =========================================================================
# Customer Site Telemetry Consent Lifecycle
# =========================================================================


def test_customer_site_telemetry_consent_lifecycle(db: Session, test_setup: dict) -> None:
    """Verify customer-local first default and explicit consent opt-in."""
    site_id = test_setup["site"].id
    user_id = test_setup["user"].id

    # Default: sync_consent is False
    config = get_or_create_telemetry_config(db, site_id)
    assert config.sync_consent is False

    # Grant consent
    updated = update_telemetry_consent(
        db=db,
        customer_site_id=site_id,
        payload=TelemetryConsentUpdateRequest(sync_consent=True, retention_days=60),
        actor_id=user_id,
    )
    assert updated.sync_consent is True
    assert updated.consent_granted_by == user_id
    assert updated.consent_expires_at is not None
    assert updated.retention_days == 60

    # Revoke consent
    revoked = update_telemetry_consent(
        db=db,
        customer_site_id=site_id,
        payload=TelemetryConsentUpdateRequest(sync_consent=False, retention_days=30),
        actor_id=user_id,
    )
    assert revoked.sync_consent is False
    assert revoked.consent_granted_by is None
