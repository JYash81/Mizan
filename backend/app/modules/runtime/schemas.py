"""Pydantic schemas for Milestone 13: Customer Runtime & Site Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.runtime import (
    AgentCommandStatus,
    AgentCommandType,
    AgentIdentityStatus,
    GoldenTestOutcome,
    ReadinessState,
    RuntimeAppStatus,
    SiteStatus,
    SlotName,
    SlotStatus,
)

# =========================================================================
# 1. Customer Site Schemas
# =========================================================================


class CustomerSiteCreate(BaseModel):
    """Request schema for creating a customer site."""

    site_key: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9\-_]+$")
    site_name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)


class CustomerSiteRead(BaseModel):
    """Response schema for a customer site."""

    id: str
    organization_id: str
    workspace_id: str
    site_key: str
    site_name: str
    description: str | None
    status: SiteStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    agent_enrolled: bool = False
    active_runtime_version: str | None = None
    last_heartbeat_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentTokenCreateResponse(BaseModel):
    """Response containing single-use high-entropy enrollment token."""

    token_id: str
    raw_token: str
    expires_at: datetime
    site_id: str
    site_key: str


# =========================================================================
# 2. Site Agent Schemas
# =========================================================================


class SiteAgentEnrollRequest(BaseModel):
    """Request by Site Agent during initial enrollment."""

    token: str = Field(..., min_length=16)
    public_key_pem: str = Field(..., min_length=32)
    key_id: str = Field(..., min_length=3, max_length=100)
    protocol_version: str = Field(default="1.0.0", max_length=32)
    agent_version: str = Field(default="1.0.0", max_length=64)
    runtime_version: str = Field(default="1.0.0", max_length=64)
    platform_info: dict[str, Any] = Field(default_factory=dict)


class SiteAgentEnrollResponse(BaseModel):
    """Response from control plane completing agent enrollment."""

    agent_id: str
    site_id: str
    public_key_fingerprint: str
    enrolled_at: datetime
    status: AgentIdentityStatus


class SiteAgentHeartbeatRequest(BaseModel):
    """Periodic outbound heartbeat from Site Agent."""

    agent_id: str
    agent_version: str = "1.0.0"
    runtime_version: str = "1.0.0"
    platform_info: dict[str, Any] = Field(default_factory=dict)
    active_slot_name: str | None = None
    readiness_state: ReadinessState | None = None


class SiteAgentHeartbeatResponse(BaseModel):
    """Response acknowledging agent heartbeat."""

    status: str = "OK"
    last_heartbeat_at: datetime
    pending_commands_count: int = 0


# =========================================================================
# 3. Signed Commands Schemas
# =========================================================================


class AgentCommandCreate(BaseModel):
    """Dispatch a signed, allowlisted command to a site agent."""

    command_type: AgentCommandType
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentCommandRead(BaseModel):
    """Signed command polled by the Site Agent."""

    id: str
    command_id: str
    customer_site_id: str
    command_type: AgentCommandType
    payload: dict[str, Any]
    payload_digest: str
    nonce: str
    issued_at: datetime
    expires_at: datetime
    signature: str
    status: AgentCommandStatus

    model_config = ConfigDict(from_attributes=True)


class AgentCommandConsumeRequest(BaseModel):
    """Site agent acknowledging execution of a command."""

    command_id: str
    status: AgentCommandStatus = AgentCommandStatus.CONSUMED
    execution_summary: dict[str, Any] = Field(default_factory=dict)


# =========================================================================
# 4. Runtime Application & Blue/Green Slots Schemas
# =========================================================================


class RuntimeApplicationRead(BaseModel):
    """Installed application package on a site."""

    id: str
    customer_site_id: str
    app_definition_id: str
    app_version_id: str
    app_manifest_digest: str
    active_slot_name: str
    status: RuntimeAppStatus
    installed_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuntimeSlotRead(BaseModel):
    """Blue/Green slot representation."""

    id: str
    runtime_application_id: str
    slot_name: SlotName
    app_version_id: str | None
    model_version_id: str | None
    release_manifest_digest: str | None
    status: SlotStatus
    readiness_state: ReadinessState
    golden_test_status: GoldenTestOutcome
    last_golden_test_run_id: str | None
    engine_adapter_key: str
    configuration_snapshot: dict[str, Any]
    staged_at: datetime | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlotStageRequest(BaseModel):
    """Request to stage a verified application and model into an inactive slot."""

    app_version_id: str
    model_version_id: str
    target_slot_name: SlotName | None = None  # None = auto-select inactive slot
    engine_adapter_key: str = "MOCK_ENGINE"
    configuration: dict[str, Any] = Field(default_factory=dict)


class SlotActivateRequest(BaseModel):
    """Request to promote candidate slot to active traffic serving."""

    slot_name: SlotName
    reason: str = Field(..., min_length=3, max_length=255)


class SlotRollbackRequest(BaseModel):
    """Request to rollback active slot to the previous slot."""

    reason: str = Field(..., min_length=3, max_length=255)


class RuntimeActivationEventRead(BaseModel):
    """Audit record of slot activation / manual switch."""

    id: str
    customer_site_id: str
    runtime_application_id: str
    previous_slot_name: str
    new_slot_name: str
    model_version_id: str
    app_version_id: str
    release_manifest_digest: str
    golden_test_run_id: str | None
    actor_id: str
    switch_reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# 5. Golden Test Runner Schemas
# =========================================================================


class GoldenTestCase(BaseModel):
    """Single test case within a golden test suite."""

    case_id: str
    category: str  # startup, model_loading, inference_smoke, output_schema, rag_retrieval_citations, safety_abstention, offline_path, resource_limits
    name: str
    description: str
    mandatory: bool = True
    input_data: dict[str, Any] = Field(default_factory=dict)
    expected_criteria: dict[str, Any] = Field(default_factory=dict)


class GoldenTestSuiteCreate(BaseModel):
    """Create a golden test suite bound to an application version."""

    app_version_id: str
    suite_version: str = "1.0.0"
    cases: list[GoldenTestCase] = Field(default_factory=list)


class GoldenTestSuiteRead(BaseModel):
    """Golden test suite definition."""

    id: str
    app_version_id: str
    suite_version: str
    suite_digest: str
    cases: list[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoldenTestRunExecuteRequest(BaseModel):
    """Execute golden tests against a candidate slot."""

    slot_id: str
    suite_id: str | None = None


class GoldenTestRunRead(BaseModel):
    """Results of a golden test execution."""

    id: str
    runtime_slot_id: str
    suite_id: str
    suite_digest: str
    runtime_version: str
    outcome: GoldenTestOutcome
    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_ms: float
    results_summary: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# 6. Customer Runtime API (Inference, RAG, Probes)
# =========================================================================


class RuntimeLiveResponse(BaseModel):
    """Response for /live probe."""

    status: str = "alive"
    timestamp: datetime


class RuntimeReadyResponse(BaseModel):
    """Response for /ready probe."""

    status: str  # "ready" or "unready"
    active_slot: SlotName
    readiness_state: ReadinessState
    golden_test_status: GoldenTestOutcome
    model_version_id: str | None


class RuntimeHealthResponse(BaseModel):
    """Response for /health diagnostic endpoint."""

    status: str
    uptime_seconds: float
    active_slot: str
    readiness: str
    engine: str
    offline_mode: bool = True
    memory_allocated_mb: float = 0.0


class RuntimeModelInfo(BaseModel):
    """Model information returned by /v1/models."""

    id: str
    object: str = "model"
    owned_by: str = "mizan-customer-runtime"
    ready: bool = True


class RuntimeModelsResponse(BaseModel):
    """Response for /v1/models."""

    object: str = "list"
    data: list[RuntimeModelInfo]


class RuntimeChatMessage(BaseModel):
    """Chat completion message."""

    role: str
    content: str


class RuntimeChatCompletionRequest(BaseModel):
    """Request for /v1/chat/completions."""

    model: str
    messages: list[RuntimeChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512
    stream: bool = False


class RuntimeChatChoice(BaseModel):
    """Single completion choice."""

    index: int
    message: RuntimeChatMessage
    finish_reason: str = "stop"


class RuntimeChatUsage(BaseModel):
    """Usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class RuntimeChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[RuntimeChatChoice]
    usage: RuntimeChatUsage
    offline_executed: bool = True


class RuntimeRagCitation(BaseModel):
    """Citation metadata for a RAG answer."""

    document_id: str
    chunk_id: str
    snippet: str
    score: float


class RuntimeRagQueryRequest(BaseModel):
    """Local RAG search and answer query."""

    query: str
    collection_name: str = "default"
    top_k: int = 3


class RuntimeRagQueryResponse(BaseModel):
    """Local RAG answer with grounded citations."""

    answer: str
    citations: list[RuntimeRagCitation]
    model_version_id: str
    latency_ms: float
    offline_executed: bool = True
