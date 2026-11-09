"""Gate 2 Financial Approval Service and Invariant Enforcement."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gate2 import Gate2ApprovalEvent, Gate2ApprovalRequest, Gate2ApprovalStatus
from app.modules.cost.cost_estimator import CostEstimatorService
from app.modules.cost.schemas.cost import CostEstimateRequest
from app.modules.gate2.approval_signing import create_and_sign_attestation
from app.modules.gate2.proposal_digest import compute_proposal_digest
from app.modules.gate2.schemas.gate2 import (
    Gate2ApprovalRequestCreate,
    Gate2DecisionRequest,
    Gate2RevokeRequest,
)


class Gate2ApprovalError(Exception):
    """Raised when Gate 2 approval business invariants are violated."""


class Gate2ApprovalService:
    """Manages the full lifecycle of Gate 2 financial approvals."""

    def __init__(self, cost_estimator: CostEstimatorService | None = None) -> None:
        self.cost_estimator = cost_estimator or CostEstimatorService()

    def create_request(
        self,
        db: Session,
        organization_id: str,
        workspace_id: str,
        requester_id: str,
        data: Gate2ApprovalRequestCreate,
    ) -> Gate2ApprovalRequest:
        """Create a new Gate 2 financial approval request."""
        # 1. Calculate or retrieve cost estimate
        cost_req = CostEstimateRequest(
            provider_name=data.provider_name,
            instance_type=data.instance_type,
            region=data.region,
            duration_hours=data.estimated_duration_hours,
            currency=data.currency,
        )
        cost_resp = self.cost_estimator.calculate_cost(db, cost_req)

        if cost_resp.status == "PRICE_UNAVAILABLE" and data.provider_name.lower() != "local":
            raise Gate2ApprovalError(
                f"Cannot create approval request: pricing record unavailable for {data.provider_name}/{data.instance_type} in region {data.region}."
            )

        if data.provider_name.lower() == "local":
            estimated_compute_cost = "0.00"
            estimated_storage_cost = "0.00"
            estimated_total_cost = "0.00"
            catalog_version = "LOCAL"
            pricing_snapshot = {
                "provider_name": "local",
                "instance_type": data.instance_type,
                "region": "local",
                "hourly_rate": "0.00",
                "catalog_version": "LOCAL",
            }
        else:
            estimated_compute_cost = cost_resp.total_estimated_cost
            estimated_storage_cost = "0.00"
            estimated_total_cost = cost_resp.total_estimated_cost
            catalog_version = cost_resp.pricing_catalog_version
            pricing_snapshot = {
                "provider_name": data.provider_name,
                "instance_type": data.instance_type,
                "region": data.region,
                "hourly_rate": cost_resp.total_estimated_cost,
                "catalog_version": catalog_version,
                "provenance": cost_resp.pricing_provenance,
            }

        # 2. Canonical proposal representation for cryptographic digest
        proposal_dict: dict[str, Any] = {
            "organization_id": organization_id,
            "workspace_id": workspace_id,
            "title": data.title,
            "purpose": data.purpose,
            "workload_type": data.workload_type,
            "hardware_profile_key": data.hardware_profile_key,
            "provider_name": data.provider_name,
            "instance_type": data.instance_type,
            "region": data.region,
            "estimated_duration_hours": float(data.estimated_duration_hours),
            "max_duration_hours": float(data.max_duration_hours),
            "estimated_compute_cost": str(estimated_compute_cost),
            "estimated_storage_cost": str(estimated_storage_cost),
            "estimated_total_cost": str(estimated_total_cost),
            "max_authorized_budget": str(Decimal(data.max_authorized_budget)),
            "currency": data.currency,
            "pricing_catalog_version": catalog_version,
            "dataset_id": data.dataset_id,
            "dataset_version_id": data.dataset_version_id,
            "gate1_approval_id": data.gate1_approval_id,
            "experiment_id": data.experiment_id,
        }

        canonical_payload_json, proposal_digest = compute_proposal_digest(proposal_dict)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=7)

        req = Gate2ApprovalRequest(
            organization_id=organization_id,
            workspace_id=workspace_id,
            requester_id=requester_id,
            title=data.title,
            purpose=data.purpose,
            workload_type=data.workload_type,
            dataset_id=data.dataset_id,
            dataset_version_id=data.dataset_version_id,
            gate1_approval_id=data.gate1_approval_id,
            experiment_id=data.experiment_id,
            hardware_profile_key=data.hardware_profile_key,
            provider_name=data.provider_name,
            instance_type=data.instance_type,
            region=data.region,
            estimated_duration_hours=data.estimated_duration_hours,
            max_duration_hours=data.max_duration_hours,
            estimated_compute_cost=str(estimated_compute_cost),
            estimated_storage_cost=str(estimated_storage_cost),
            estimated_total_cost=str(estimated_total_cost),
            max_authorized_budget=str(Decimal(data.max_authorized_budget)),
            currency=data.currency,
            proposal_digest=proposal_digest,
            proposal_payload_json=canonical_payload_json,
            pricing_snapshot_json=json.dumps(pricing_snapshot, sort_keys=True),
            pricing_catalog_version=catalog_version,
            status=Gate2ApprovalStatus.PENDING_APPROVAL,
            expires_at=expires_at,
        )
        db.add(req)
        db.flush()

        # Audit event
        event = Gate2ApprovalEvent(
            approval_request_id=req.id,
            actor_id=requester_id,
            event_type="REQUEST_CREATED",
            previous_status=None,
            new_status=Gate2ApprovalStatus.PENDING_APPROVAL.value,
            message="Gate 2 financial approval request submitted.",
            metadata_json=json.dumps({"proposal_digest": proposal_digest}),
        )
        db.add(event)
        db.commit()
        db.refresh(req)
        return req

    def get_request(
        self,
        db: Session,
        request_id: str,
        workspace_id: str | None = None,
    ) -> Gate2ApprovalRequest | None:
        """Fetch request and automatically transition to EXPIRED if deadline passed."""
        query = select(Gate2ApprovalRequest).where(Gate2ApprovalRequest.id == request_id)
        if workspace_id:
            query = query.where(Gate2ApprovalRequest.workspace_id == workspace_id)
        req = db.execute(query).scalar_one_or_none()
        if not req:
            return None

        # Check expiration
        now = datetime.now(UTC)
        # Note: SQLite may return naive datetimes; normalize if needed
        req_expires_at = req.expires_at
        if req_expires_at.tzinfo is None:
            req_expires_at = req_expires_at.replace(tzinfo=UTC)

        if now > req_expires_at and req.status in (
            Gate2ApprovalStatus.PENDING_APPROVAL,
            Gate2ApprovalStatus.APPROVED,
        ):
            old_status = req.status.value
            req.status = Gate2ApprovalStatus.EXPIRED
            event = Gate2ApprovalEvent(
                approval_request_id=req.id,
                actor_id=req.requester_id,
                event_type="EXPIRED",
                previous_status=old_status,
                new_status=Gate2ApprovalStatus.EXPIRED.value,
                message="Approval validity window expired.",
            )
            db.add(event)
            db.commit()
            db.refresh(req)

        return req

    def list_requests(
        self,
        db: Session,
        workspace_id: str,
        status: Gate2ApprovalStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Gate2ApprovalRequest]:
        """List requests in workspace with pagination and status filter."""
        query = select(Gate2ApprovalRequest).where(
            Gate2ApprovalRequest.workspace_id == workspace_id
        )
        if status:
            query = query.where(Gate2ApprovalRequest.status == status)
        query = query.order_by(Gate2ApprovalRequest.created_at.desc()).limit(limit).offset(offset)
        return list(db.execute(query).scalars().all())

    def decide_request(
        self,
        db: Session,
        request_id: str,
        workspace_id: str,
        actor_id: str,
        actor_role: str,
        data: Gate2DecisionRequest,
    ) -> Gate2ApprovalRequest:
        """Approve or reject a Gate 2 financial request."""
        req = self.get_request(db, request_id, workspace_id=workspace_id)
        if not req:
            raise Gate2ApprovalError(f"Gate 2 approval request {request_id} not found.")

        if req.status != Gate2ApprovalStatus.PENDING_APPROVAL:
            raise Gate2ApprovalError(
                f"Cannot decide request: status is '{req.status.value}', expected 'PENDING_APPROVAL'."
            )

        if data.decision == "REJECT":
            req.status = Gate2ApprovalStatus.REJECTED
            req.approver_id = actor_id
            req.approver_role_snapshot = actor_role
            req.rejection_reason = data.decision_reason
            req.decision_reason = data.decision_reason

            event = Gate2ApprovalEvent(
                approval_request_id=req.id,
                actor_id=actor_id,
                event_type="REJECTED",
                previous_status=Gate2ApprovalStatus.PENDING_APPROVAL.value,
                new_status=Gate2ApprovalStatus.REJECTED.value,
                message=f"Request rejected: {data.decision_reason}",
            )
            db.add(event)
            db.commit()
            db.refresh(req)
            return req

        # Digital signing for APPROVE
        canonical_signed_json, sig_hex, signing_key_id, signed_at = create_and_sign_attestation(
            approval_id=req.id,
            proposal_id=req.id,
            proposal_digest=req.proposal_digest,
            organization_id=req.organization_id,
            workspace_id=req.workspace_id,
            approver_id=actor_id,
            approver_role=actor_role,
            max_authorized_budget=req.max_authorized_budget,
            currency=req.currency,
            decision_reason=data.decision_reason,
            key_id=data.signing_key_id,
        )

        req.status = Gate2ApprovalStatus.APPROVED
        req.approver_id = actor_id
        req.approver_role_snapshot = actor_role
        req.approval_signature = sig_hex
        req.signing_key_id = signing_key_id
        req.signed_payload = canonical_signed_json
        req.signed_at = signed_at
        req.decision_reason = data.decision_reason

        event = Gate2ApprovalEvent(
            approval_request_id=req.id,
            actor_id=actor_id,
            event_type="APPROVED",
            previous_status=Gate2ApprovalStatus.PENDING_APPROVAL.value,
            new_status=Gate2ApprovalStatus.APPROVED.value,
            message=f"Request approved and digitally signed. Reason: {data.decision_reason}",
            metadata_json=json.dumps({"signing_key_id": signing_key_id, "signature": sig_hex}),
        )
        db.add(event)
        db.commit()
        db.refresh(req)
        return req

    def revoke_request(
        self,
        db: Session,
        request_id: str,
        workspace_id: str,
        actor_id: str,
        data: Gate2RevokeRequest,
    ) -> Gate2ApprovalRequest:
        """Revoke a previously approved Gate 2 request."""
        req = self.get_request(db, request_id, workspace_id=workspace_id)
        if not req:
            raise Gate2ApprovalError(f"Gate 2 approval request {request_id} not found.")

        if req.status != Gate2ApprovalStatus.APPROVED:
            raise Gate2ApprovalError(
                f"Cannot revoke request: status is '{req.status.value}', expected 'APPROVED'."
            )

        now = datetime.now(UTC)
        req.status = Gate2ApprovalStatus.REVOKED
        req.revoked_by_id = actor_id
        req.revoked_at = now
        req.revocation_reason = data.revocation_reason

        event = Gate2ApprovalEvent(
            approval_request_id=req.id,
            actor_id=actor_id,
            event_type="REVOKED",
            previous_status=Gate2ApprovalStatus.APPROVED.value,
            new_status=Gate2ApprovalStatus.REVOKED.value,
            message=f"Approval revoked: {data.revocation_reason}",
        )
        db.add(event)
        db.commit()
        db.refresh(req)
        return req
