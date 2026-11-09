"""Deterministic Hard Constraint Filtering Engine.

Enforces non-negotiable safety, compliance, latency, budget, and resource thresholds
before multi-objective optimization is executed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.experiment import TrialStatus
from app.models.recommendations import CandidateEligibilityStatus


class ConstraintEvaluationDetail(BaseModel):
    """Result of checking an individual constraint."""

    constraint_key: str
    passed: bool
    threshold: Any
    actual_value: Any
    reason: str


class CandidateConstraintResult(BaseModel):
    """Aggregate constraint evaluation outcome for a single candidate."""

    candidate_id: str
    eligibility_status: CandidateEligibilityStatus
    is_eligible: bool
    exclusion_reasons: list[str] = Field(default_factory=list)
    constraint_details: dict[str, ConstraintEvaluationDetail] = Field(default_factory=dict)


class ConstraintEngine:
    """Evaluates hard constraints against candidate configurations."""

    @classmethod
    def evaluate_candidate(
        cls,
        candidate_data: dict[str, Any],
        constraints: dict[str, Any],
        hardware_profiles_map: dict[str, Any] | None = None,
    ) -> CandidateConstraintResult:
        """Evaluate all configured hard constraints against a candidate.

        Args:
            candidate_data: Candidate metadata, metrics, and trial attributes.
            constraints: User or profile-configured hard constraints.
            hardware_profiles_map: Optional dictionary of registered hardware profiles.

        Returns:
            CandidateConstraintResult with eligibility and detailed failure reasons.
        """
        cid = str(candidate_data.get("id", "unknown"))
        reasons: list[str] = []
        details: dict[str, ConstraintEvaluationDetail] = {}
        has_insufficient_evidence = False

        # 1. Mandatory Trial Status check: Must be completed
        trial_status = candidate_data.get("trial_status")
        if trial_status is not None and trial_status != TrialStatus.COMPLETED.value and trial_status != TrialStatus.COMPLETED:
            reasons.append(f"Trial is in status '{trial_status}' (must be COMPLETED).")
            details["trial_status"] = ConstraintEvaluationDetail(
                constraint_key="trial_status",
                passed=False,
                threshold="COMPLETED",
                actual_value=str(trial_status),
                reason=f"Trial is '{trial_status}' rather than COMPLETED.",
            )

        # 2. Gate 1 Approval check
        if constraints.get("require_gate1_approval", True):
            gate1_ref = candidate_data.get("gate1_approval_id")
            if not gate1_ref:
                reasons.append("Missing valid Gate 1 data protection approval attestation.")
                details["gate1_approval"] = ConstraintEvaluationDetail(
                    constraint_key="gate1_approval",
                    passed=False,
                    threshold="APPROVED",
                    actual_value=None,
                    reason="Candidate has no verified Gate 1 approval reference.",
                )

        # 3. Global Free-Only Policy Invariant: Disallow paid compute if policy active
        settings = get_settings()
        if not settings.allow_paid_compute:
            target_hw = candidate_data.get("hardware_profile_key", "")
            if "NVIDIA" in target_hw.upper() or "CLOUD" in target_hw.upper():
                reasons.append("Cloud or GPU compute is blocked by global Free-Only Infrastructure Policy ($0.00 spend cap).")
                details["free_only_policy"] = ConstraintEvaluationDetail(
                    constraint_key="free_only_policy",
                    passed=False,
                    threshold="LOCAL_CPU_FREE",
                    actual_value=target_hw,
                    reason="Paid cloud execution violates mandatory zero-spend policy.",
                )

        # 4. Minimum Quality Score
        min_quality = constraints.get("min_quality_score")
        if min_quality is not None:
            actual_q = candidate_data.get("aggregate_score")
            if actual_q is None:
                has_insufficient_evidence = True
                reasons.append("Quality score is missing or unmeasured; cannot satisfy min_quality_score.")
                details["min_quality_score"] = ConstraintEvaluationDetail(
                    constraint_key="min_quality_score",
                    passed=False,
                    threshold=float(min_quality),
                    actual_value=None,
                    reason="Missing aggregate quality score.",
                )
            elif float(actual_q) < float(min_quality):
                reasons.append(
                    f"Aggregate quality score ({actual_q:.1f}) is below minimum required threshold of {min_quality:.1f}."
                )
                details["min_quality_score"] = ConstraintEvaluationDetail(
                    constraint_key="min_quality_score",
                    passed=False,
                    threshold=float(min_quality),
                    actual_value=float(actual_q),
                    reason=f"Score {actual_q:.1f} < {min_quality:.1f}.",
                )

        # 5. Maximum P95 Latency
        max_p95 = constraints.get("max_p95_latency_ms")
        if max_p95 is not None:
            actual_p95 = candidate_data.get("latency_p95_ms")
            if actual_p95 is None:
                has_insufficient_evidence = True
                reasons.append("P95 latency is unmeasured; cannot verify max_p95_latency_ms constraint.")
                details["max_p95_latency_ms"] = ConstraintEvaluationDetail(
                    constraint_key="max_p95_latency_ms",
                    passed=False,
                    threshold=float(max_p95),
                    actual_value=None,
                    reason="Tail latency P95 is missing.",
                )
            elif float(actual_p95) > float(max_p95):
                reasons.append(
                    f"P95 latency ({actual_p95:.1f} ms) exceeds configured maximum threshold of {max_p95:.1f} ms."
                )
                details["max_p95_latency_ms"] = ConstraintEvaluationDetail(
                    constraint_key="max_p95_latency_ms",
                    passed=False,
                    threshold=float(max_p95),
                    actual_value=float(actual_p95),
                    reason=f"Latency {actual_p95:.1f} ms > {max_p95:.1f} ms.",
                )

        # 6. Maximum RAM Requirement
        max_ram = constraints.get("max_ram_mb")
        if max_ram is not None:
            actual_ram = candidate_data.get("required_ram_mb")
            if actual_ram is not None and float(actual_ram) > float(max_ram):
                reasons.append(
                    f"Estimated RAM requirement ({actual_ram:.0f} MB) exceeds maximum allowed limit of {max_ram:.0f} MB."
                )
                details["max_ram_mb"] = ConstraintEvaluationDetail(
                    constraint_key="max_ram_mb",
                    passed=False,
                    threshold=float(max_ram),
                    actual_value=float(actual_ram),
                    reason=f"RAM {actual_ram:.0f} MB > {max_ram:.0f} MB.",
                )

        # 7. Hardware Profile Capacity Constraint
        req_profile_key = constraints.get("required_hardware_profile")
        if req_profile_key and hardware_profiles_map:
            profile = hardware_profiles_map.get(req_profile_key)
            if profile:
                profile_ram = getattr(profile, "system_ram_mb", 0)
                actual_ram = candidate_data.get("required_ram_mb", 0.0)
                if actual_ram and float(actual_ram) > profile_ram:
                    reasons.append(
                        f"Workload RAM ({actual_ram:.0f} MB) exceeds target hardware profile '{req_profile_key}' capacity ({profile_ram} MB)."
                    )
                    details["required_hardware_profile"] = ConstraintEvaluationDetail(
                        constraint_key="required_hardware_profile",
                        passed=False,
                        threshold=profile_ram,
                        actual_value=float(actual_ram),
                        reason=f"Incompatible with profile '{req_profile_key}'.",
                    )

        # 8. Maximum Budget Constraint (Strict Missing Cost Invariant)
        max_budget = constraints.get("max_budget_usd")
        if max_budget is not None:
            cost_val = candidate_data.get("estimated_cost_usd")
            if cost_val is None or str(cost_val).upper() in ("UNKNOWN", "PRICE_UNAVAILABLE"):
                # Missing price cannot be assumed within budget!
                has_insufficient_evidence = True
                reasons.append(
                    f"Cost is unknown/unavailable; cannot verify candidate complies with budget limit of ${float(max_budget):.2f}."
                )
                details["max_budget_usd"] = ConstraintEvaluationDetail(
                    constraint_key="max_budget_usd",
                    passed=False,
                    threshold=float(max_budget),
                    actual_value="UNKNOWN",
                    reason="Missing cost record cannot be assumed below budget.",
                )
            else:
                try:
                    num_cost = float(cost_val)
                    if num_cost > float(max_budget):
                        reasons.append(
                            f"Estimated cost (${num_cost:.2f}) exceeds configured budget cap of ${float(max_budget):.2f}."
                        )
                        details["max_budget_usd"] = ConstraintEvaluationDetail(
                            constraint_key="max_budget_usd",
                            passed=False,
                            threshold=float(max_budget),
                            actual_value=num_cost,
                            reason=f"Cost ${num_cost:.2f} > ${float(max_budget):.2f}.",
                        )
                except (ValueError, TypeError):
                    has_insufficient_evidence = True
                    reasons.append("Unparseable cost value encountered for budget check.")

        # 9. Citation Completeness Constraint
        min_citation = constraints.get("min_citation_score")
        if min_citation is not None:
            actual_cite = candidate_data.get("citation_completeness")
            if actual_cite is not None and float(actual_cite) < float(min_citation):
                reasons.append(
                    f"Citation completeness ({actual_cite:.1f}%) is below minimum requirement of {min_citation:.1f}%."
                )
                details["min_citation_score"] = ConstraintEvaluationDetail(
                    constraint_key="min_citation_score",
                    passed=False,
                    threshold=float(min_citation),
                    actual_value=float(actual_cite),
                    reason=f"Citation {actual_cite:.1f}% < {min_citation:.1f}%.",
                )

        # 10. Safety / Compliance Constraint
        min_safety = constraints.get("min_safety_score")
        if min_safety is not None:
            actual_safety = candidate_data.get("safety")
            if actual_safety is not None and float(actual_safety) < float(min_safety):
                reasons.append(
                    f"Safety score ({actual_safety:.1f}%) is below mandatory threshold of {min_safety:.1f}%."
                )
                details["min_safety_score"] = ConstraintEvaluationDetail(
                    constraint_key="min_safety_score",
                    passed=False,
                    threshold=float(min_safety),
                    actual_value=float(actual_safety),
                    reason=f"Safety score {actual_safety:.1f}% < {min_safety:.1f}%.",
                )

        # Determine overall eligibility status
        if not reasons:
            eligibility = CandidateEligibilityStatus.ELIGIBLE
            is_eligible = True
        elif has_insufficient_evidence:
            eligibility = CandidateEligibilityStatus.INSUFFICIENT_EVIDENCE
            is_eligible = False
        else:
            eligibility = CandidateEligibilityStatus.INELIGIBLE
            is_eligible = False

        return CandidateConstraintResult(
            candidate_id=cid,
            eligibility_status=eligibility,
            is_eligible=is_eligible,
            exclusion_reasons=reasons,
            constraint_details=details,
        )
