"""Pydantic schemas for Masking and Gate 1 Human Approval."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.masking import (
    DecisionType,
    ExtractionCoverage,
    FindingStatus,
    Gate1Decision,
    MaskingRunStatus,
    MaskingStrategy,
)


class MaskingProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    language: str = Field("en", max_length=10)
    enabled_entities: list[str] = Field(
        default=[
            "UAE_EMIRATES_ID",
            "UAE_IBAN",
            "UAE_PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "PERSON",
            "LOCATION",
            "CREDIT_CARD",
            "IBAN_CODE",
        ]
    )
    replacement_strategy: MaskingStrategy = MaskingStrategy.REPLACE_WITH_ENTITY_LABEL
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)


class MaskingProfileUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    language: str | None = Field(None, max_length=10)
    enabled_entities: list[str] | None = None
    replacement_strategy: MaskingStrategy | None = None
    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)
    is_active: bool | None = None


class MaskingProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str | None
    name: str
    description: str | None
    language: str
    enabled_entities_json: str
    replacement_strategy: MaskingStrategy
    confidence_threshold: float
    version: int
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class MaskingRunCreateRequest(BaseModel):
    dataset_id: str
    dataset_version_id: str
    masking_profile_id: str | None = None


class MaskingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    dataset_id: str
    dataset_version_id: str
    source_dataset_digest: str
    masking_profile_id: str | None
    status: MaskingRunStatus
    extraction_coverage: ExtractionCoverage
    documents_processed: int
    documents_failed: int
    findings_count: int
    unresolved_findings_count: int
    masked_output_digest: str | None
    error_message: str | None
    created_by: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PiiFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    masking_run_id: str
    document_id: str
    entity_type: str
    recognizer_name: str
    recognizer_version: str
    detection_score: float
    start_offset: int
    end_offset: int
    offset_unit: str
    page_number: int | None
    overlap_group_id: str | None
    status: FindingStatus
    is_manual: bool
    created_at: datetime
    updated_at: datetime


class ManualFindingCreateRequest(BaseModel):
    document_id: str
    entity_type: str = Field(..., min_length=2, max_length=64)
    start_offset: int = Field(..., ge=0)
    end_offset: int = Field(..., gt=0)
    page_number: int | None = None


class MaskingDecisionCreateRequest(BaseModel):
    decision_type: DecisionType
    reason: str | None = None
    custom_replacement: str | None = Field(None, max_length=120)


class MaskingDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    masking_run_id: str
    finding_id: str
    reviewer_user_id: str
    decision_type: DecisionType
    reason: str | None
    custom_replacement: str | None
    created_at: datetime


class DocumentReviewResponse(BaseModel):
    document_id: str
    document_name: str
    file_type: str
    original_text: str
    masked_preview: str
    findings: list[PiiFindingResponse]
    extraction_status: str
    requires_ocr: bool


class Gate1ApprovalRequest(BaseModel):
    decision_reason: str | None = None
    override_coverage_reason: str | None = None


class Gate1RejectionRequest(BaseModel):
    decision_reason: str = Field(..., min_length=3)


class Gate1ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    dataset_id: str
    dataset_version_id: str
    masking_run_id: str
    source_dataset_digest: str
    masked_output_digest: str
    findings_digest: str
    reviewer_user_id: str
    reviewer_role_snapshot: str
    decision: Gate1Decision
    decision_reason: str | None
    signature_algorithm: str
    signing_key_id: str
    approval_signature: str
    canonical_payload: str
    reviewed_at: datetime
    created_at: datetime


class Gate1VerificationResponse(BaseModel):
    approval_id: str
    is_valid: bool
    decision: str
    reviewer_user_id: str
    reviewer_role: str
    signature_algorithm: str
    signing_key_id: str
    source_dataset_digest: str
    masked_output_digest: str
    verification_message: str
    verified_at: datetime
