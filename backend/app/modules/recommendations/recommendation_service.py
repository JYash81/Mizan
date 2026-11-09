"""Master Recommendation Service for Mizan Milestone 9.

Orchestrates candidate extraction from completed M7 experiments, comparability verification,
hard constraint evaluation, multi-objective Pareto analysis, preference scoring,
deterministic explanation synthesis, and immutable report generation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experiment import Experiment, ExperimentTrial, TrialStatus
from app.models.hardware import HardwareProfile
from app.models.recommendations import (
    CandidateEligibilityStatus,
    CandidateProvenanceStatus,
    OptimizationProfile,
    RecommendationCandidate,
    RecommendationDecision,
    RecommendationEvent,
    RecommendationRun,
    RecommendationRunStatus,
    RecommendationScenario,
)
from app.modules.hardware.resource_estimator import estimate_model_resources
from app.modules.recommendations.comparability_service import ComparabilityService
from app.modules.recommendations.constraint_engine import ConstraintEngine
from app.modules.recommendations.explanation_engine import ExplanationEngine
from app.modules.recommendations.normalization_service import NormalizationService
from app.modules.recommendations.pareto_engine import ParetoEngine
from app.modules.recommendations.recommendation_report import RecommendationReportService
from app.modules.recommendations.schemas.recommendations import (
    CandidateValidationResult,
    CreateOptimizationProfileRequest,
    CreateRecommendationRunRequest,
    RecordDecisionRequest,
    UpdateOptimizationProfileRequest,
)
from app.modules.recommendations.sensitivity_analysis import SensitivityAnalysisEngine
from app.modules.recommendations.weighted_scoring import (
    WeightedScoringEngine,
)

logger = logging.getLogger(__name__)


def compute_canonical_digest(data: Any) -> str:
    """Compute deterministic SHA-256 digest of canonical RFC 8785 JSON."""
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class RecommendationService:
    """Enterprise service executing M9 recommendation engine pipelines."""

    # --------------------------------------------------------------------------
    # Optimization Profiles Management
    # --------------------------------------------------------------------------

    @staticmethod
    def create_optimization_profile(
        db: Session,
        workspace_id: str,
        user_id: str,
        org_id: str,
        req: CreateOptimizationProfileRequest,
    ) -> OptimizationProfile:
        """Create a user-configurable optimization preference profile."""
        profile = OptimizationProfile(
            organization_id=org_id,
            workspace_id=workspace_id,
            name=req.name,
            description=req.description,
            objectives_json=json.dumps(req.objectives),
            weights_json=json.dumps(req.weights),
            constraints_json=json.dumps(req.constraints),
            preferred_hardware_profile=req.preferred_hardware_profile,
            budget_currency=req.budget_currency,
            created_by=user_id,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def list_optimization_profiles(
        db: Session,
        workspace_id: str,
    ) -> list[OptimizationProfile]:
        """List all optimization profiles for a workspace."""
        return list(
            db.scalars(
                select(OptimizationProfile)
                .where(OptimizationProfile.workspace_id == workspace_id)
                .order_by(OptimizationProfile.created_at.desc())
            ).all()
        )

    @staticmethod
    def get_optimization_profile(
        db: Session,
        profile_id: str,
        workspace_id: str,
    ) -> OptimizationProfile | None:
        """Get an optimization profile by ID with tenant isolation."""
        return db.scalars(
            select(OptimizationProfile).where(
                OptimizationProfile.id == profile_id,
                OptimizationProfile.workspace_id == workspace_id,
            )
        ).first()

    @staticmethod
    def update_optimization_profile(
        db: Session,
        profile_id: str,
        workspace_id: str,
        user_id: str,
        req: UpdateOptimizationProfileRequest,
    ) -> OptimizationProfile:
        """Update an existing optimization profile."""
        profile = RecommendationService.get_optimization_profile(db, profile_id, workspace_id)
        if not profile:
            raise ValueError(f"Optimization profile '{profile_id}' not found.")

        if req.name is not None:
            profile.name = req.name
        if req.description is not None:
            profile.description = req.description
        if req.objectives is not None:
            profile.objectives_json = json.dumps(req.objectives)
        if req.weights is not None:
            profile.weights_json = json.dumps(req.weights)
        if req.constraints is not None:
            profile.constraints_json = json.dumps(req.constraints)
        if req.preferred_hardware_profile is not None:
            profile.preferred_hardware_profile = req.preferred_hardware_profile
        if req.budget_currency is not None:
            profile.budget_currency = req.budget_currency

        profile.version += 1
        profile.updated_by = user_id
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def delete_optimization_profile(
        db: Session,
        profile_id: str,
        workspace_id: str,
    ) -> bool:
        """Delete an optimization profile."""
        profile = RecommendationService.get_optimization_profile(db, profile_id, workspace_id)
        if not profile:
            return False
        db.delete(profile)
        db.commit()
        return True

    # --------------------------------------------------------------------------
    # Candidate Validation & Extraction
    # --------------------------------------------------------------------------

    @staticmethod
    def validate_candidate_trials(
        db: Session,
        workspace_id: str,
        experiment_ids: list[str],
        trial_ids: list[str] | None = None,
    ) -> list[CandidateValidationResult]:
        """Pre-flight inspection of completed trials for proposed recommendation runs."""
        query = (
            select(ExperimentTrial, Experiment)
            .join(Experiment, ExperimentTrial.experiment_id == Experiment.id)
            .where(
                Experiment.workspace_id == workspace_id,
                Experiment.id.in_(experiment_ids),
            )
        )
        if trial_ids:
            query = query.where(ExperimentTrial.id.in_(trial_ids))

        rows = db.execute(query).all()
        results: list[CandidateValidationResult] = []

        for trial, exp in rows:
            exclusion_reasons: list[str] = []
            is_eligible = True

            if trial.status != TrialStatus.COMPLETED:
                exclusion_reasons.append(f"Trial is in status '{trial.status.value}' (must be COMPLETED).")
                is_eligible = False

            if not trial.evaluation_run_id:
                exclusion_reasons.append("Trial has no linked M6 evaluation run.")
                is_eligible = False

            if not exp.gate1_approval_id:
                exclusion_reasons.append("Trial experiment lacks a verified Gate 1 approval reference.")
                is_eligible = False

            status = (
                CandidateProvenanceStatus.VERIFIED
                if is_eligible
                else CandidateProvenanceStatus.INCOMPLETE
            )

            results.append(
                CandidateValidationResult(
                    trial_id=trial.id,
                    experiment_id=exp.id,
                    trial_number=trial.trial_number,
                    candidate_label=f"{exp.name} - Trial #{trial.trial_number} ({trial.name})",
                    trial_status=trial.status.value,
                    configuration_digest=trial.configuration_digest,
                    is_eligible=is_eligible,
                    exclusion_reasons=exclusion_reasons,
                    provenance_status=status,
                )
            )

        return results

    # --------------------------------------------------------------------------
    # Recommendation Run Execution
    # --------------------------------------------------------------------------

    @classmethod
    def create_and_execute_recommendation_run(
        cls,
        db: Session,
        workspace_id: str,
        user_id: str,
        org_id: str,
        req: CreateRecommendationRunRequest,
    ) -> RecommendationRun:
        """Create, execute, and persist a full multi-objective recommendation run."""
        # 1. Fetch eligible trials
        query = (
            select(ExperimentTrial, Experiment)
            .join(Experiment, ExperimentTrial.experiment_id == Experiment.id)
            .where(
                Experiment.workspace_id == workspace_id,
                Experiment.id.in_(req.experiment_ids),
            )
        )
        if req.trial_ids:
            query = query.where(ExperimentTrial.id.in_(req.trial_ids))

        rows = db.execute(query).all()
        if not rows:
            raise ValueError("No matching trials found in the specified experiments for this workspace.")

        # 2. Check for optional optimization profile defaults
        selected_objectives = list(req.selected_objectives)
        active_weights = dict(req.weights) if req.weights else {}
        active_constraints = dict(req.hard_constraints)

        if req.optimization_profile_id:
            profile = cls.get_optimization_profile(db, req.optimization_profile_id, workspace_id)
            if profile:
                if not req.selected_objectives and profile.objectives_json:
                    selected_objectives = json.loads(profile.objectives_json)
                if not active_weights and profile.weights_json:
                    active_weights = json.loads(profile.weights_json)
                if not req.hard_constraints and profile.constraints_json:
                    active_constraints = json.loads(profile.constraints_json)

        # 3. Compute Canonical Input Digest
        input_payload = {
            "workspace_id": workspace_id,
            "experiment_ids": sorted(req.experiment_ids),
            "trial_ids": sorted([t.id for t, _ in rows]),
            "selected_objectives": sorted(selected_objectives),
            "weights": active_weights,
            "hard_constraints": active_constraints,
        }
        input_digest = compute_canonical_digest(input_payload)

        # 4. Create RecommendationRun record
        rec_run = RecommendationRun(
            organization_id=org_id,
            workspace_id=workspace_id,
            name=req.name,
            description=req.description,
            status=RecommendationRunStatus.RUNNING,
            algorithm_version="1.0.0",
            input_digest=input_digest,
            input_snapshot_json=json.dumps(input_payload, sort_keys=True),
            constraints_snapshot_json=json.dumps(active_constraints, sort_keys=True),
            weights_snapshot_json=json.dumps(active_weights, sort_keys=True) if active_weights else None,
            total_candidates=len(rows),
            created_by=user_id,
        )
        db.add(rec_run)
        db.flush()

        # 5. Extract Candidate Raw Attributes and Objective Values
        candidates_raw: list[dict[str, Any]] = []
        candidate_meta: list[dict[str, Any]] = []

        # Load hardware profiles for capacity constraints
        hw_profiles = db.scalars(select(HardwareProfile)).all()
        hardware_profiles_map = {p.profile_key: p for p in hw_profiles}

        for trial, exp in rows:
            cid = trial.id
            config_dict = trial.configuration
            score_breakdown: dict[str, float] = {}
            if trial.score_breakdown_json:
                try:
                    score_breakdown = json.loads(trial.score_breakdown_json)
                except Exception:
                    pass

            # Primary measured metrics from trial
            raw_metrics: dict[str, Any] = {
                "aggregate_score": trial.aggregate_score,
                "latency_p50_ms": trial.latency_p50_ms,
                "latency_p95_ms": trial.latency_p95_ms,
                "execution_duration_ms": trial.execution_duration_ms,
            }

            # Map breakdown metrics if present
            for m_key in ("exact_match", "faithfulness", "groundedness", "citation_verification", "safety", "compliance"):
                if m_key in score_breakdown:
                    raw_metrics[m_key] = score_breakdown[m_key]

            # Estimate resource requirements using M8 estimator
            param_count = float(config_dict.get("parameter_count_millions", 1500.0))
            quant_fmt = str(config_dict.get("quantization_format", "Q4_K_M"))
            target_hw = str(config_dict.get("hardware_profile_key", "LOCAL_CPU_I5_8GB"))
            context_len = int(config_dict.get("context_length", 2048))
            model_name = str(config_dict.get("model_name") or getattr(exp, "target_model", None) or trial.name)

            hw_profile = hardware_profiles_map.get(target_hw)
            hw_profile_dict = (
                {
                    "profile_key": hw_profile.profile_key,
                    "name": hw_profile.name,
                    "system_ram_mb": hw_profile.system_ram_mb,
                    "available_ram_mb": hw_profile.available_ram_mb,
                    "gpu_vram_mb": hw_profile.gpu_vram_mb,
                }
                if hw_profile
                else None
            )

            res_est = estimate_model_resources(
                model_name=model_name,
                parameter_count_millions=param_count,
                quantization_format=quant_fmt,
                context_length=context_len,
                batch_size=1,
                execution_mode="INFERENCE_CPU",
                hardware_profile=hw_profile_dict,
            )

            raw_metrics["required_ram_mb"] = res_est["peak_memory_mb"]
            raw_metrics["artifact_size_mb"] = res_est["artifact_size_mb"]
            raw_metrics["memory_headroom_mb"] = res_est["headroom_mb"]

            # Handle cost: Local CPU is guaranteed $0.00; missing cloud price is UNKNOWN
            if "LOCAL" in target_hw.upper():
                raw_metrics["estimated_cost_usd"] = 0.0
            else:
                raw_metrics["estimated_cost_usd"] = "UNKNOWN"

            # Evidence provenance tags
            evidence_summary = {
                "aggregate_score": "MEASURED" if trial.aggregate_score is not None else "UNAVAILABLE",
                "latency_p95_ms": "MEASURED" if trial.latency_p95_ms is not None else "UNAVAILABLE",
                "required_ram_mb": "ESTIMATED",
                "artifact_size_mb": "ESTIMATED",
                "estimated_cost_usd": "MEASURED" if "LOCAL" in target_hw.upper() else "UNKNOWN",
            }

            c_info = {
                "id": cid,
                "trial_id": trial.id,
                "experiment_id": exp.id,
                "trial_number": trial.trial_number,
                "candidate_label": f"{exp.name} - Trial #{trial.trial_number} ({trial.name})",
                "configuration_digest": trial.configuration_digest,
                "configuration_json": trial.configuration_json,
                "evaluation_run_id": trial.evaluation_run_id,
                "dataset_id": exp.dataset_id,
                "dataset_version_id": exp.dataset_version_id,
                "evaluation_suite_id": exp.evaluation_suite_id,
                "evaluation_suite_version_id": exp.evaluation_suite_version_id,
                "evaluation_split": exp.evaluation_split.value if exp.evaluation_split else None,
                "hardware_profile_key": target_hw,
                "gate1_approval_id": exp.gate1_approval_id,
                "trial_status": trial.status.value,
                "raw_metrics": raw_metrics,
                "evidence_summary": evidence_summary,
            }
            # Flatten metrics into dict for engine evaluation
            eval_dict = dict(c_info)
            eval_dict.update(raw_metrics)
            candidates_raw.append(eval_dict)
            candidate_meta.append(c_info)

        # 6. Check Cohort Comparability
        comp_result = ComparabilityService.verify_cohort_comparability(candidates_raw)

        # 7. Evaluate Hard Constraints
        constraint_results: list[Any] = []
        for cand in candidates_raw:
            c_res = ConstraintEngine.evaluate_candidate(
                cand, active_constraints, hardware_profiles_map
            )
            # Propagate comparability status
            comp_status = comp_result.candidate_statuses.get(cand["id"])
            if comp_status and comp_status == CandidateProvenanceStatus.INCOMPATIBLE:
                c_res.is_eligible = False
                c_res.eligibility_status = CandidateEligibilityStatus.INELIGIBLE
                c_res.exclusion_reasons.append("Cohort comparability failure across baseline dataset/suite version.")

            cand["is_eligible"] = c_res.is_eligible
            cand["eligibility_status"] = c_res.eligibility_status
            cand["exclusion_reasons"] = c_res.exclusion_reasons
            cand["constraint_details"] = {k: v.model_dump() for k, v in c_res.constraint_details.items()}
            constraint_results.append(c_res)

        # 8. Normalize Metrics for Eligible Candidates
        eligible_raw = [c for c in candidates_raw if c["is_eligible"]]
        norm_snapshot = None
        if eligible_raw:
            _, norm_snapshot = NormalizationService.normalize_candidates(
                eligible_raw, selected_objectives
            )

        # Apply normalization to all candidates using the snapshot
        for cand in candidates_raw:
            norm_dict: dict[str, float | None] = {}
            for obj_key in selected_objectives:
                bounds = norm_snapshot.bounds.get(obj_key) if norm_snapshot else None
                if bounds:
                    norm_dict[obj_key] = NormalizationService.normalize_value(
                        cand.get(obj_key) if isinstance(cand.get(obj_key), (int, float)) else None,
                        bounds,
                    )
                else:
                    norm_dict[obj_key] = None
            cand["normalized_objective_values"] = norm_dict

        # 9. Compute Pareto Dominance and Frontier
        pareto_res = ParetoEngine.compute_frontier(
            candidates=candidates_raw,
            objective_keys=selected_objectives,
        )

        # 10. Optional Preference-Weighted Scoring
        weighted_res = None
        if active_weights:
            try:
                weighted_res = WeightedScoringEngine.calculate_weighted_scores(
                    candidates=candidates_raw,
                    weights=active_weights,
                    scenario_name="User Preference",
                )
            except ValueError as e:
                logger.warning("Could not compute weighted scores: %s", e)

        # Map weighted scores back to candidates
        weighted_scores_map = {}
        if weighted_res:
            for item in weighted_res.ranked_candidates:
                weighted_scores_map[item.candidate_id] = item.weighted_score

        # 11. Run Sensitivity Analysis if weights provided
        sensitivity_report = None
        if active_weights and len(eligible_raw) >= 2:
            sensitivity_report = SensitivityAnalysisEngine.analyze_sensitivity(
                candidates=candidates_raw,
                base_weights=active_weights,
                frontier_ids=pareto_res.frontier_candidate_ids,
            )

        # 12. Synthesize Deterministic Explanations & Persist Candidates
        candidates_map = {c["id"]: c for c in candidates_raw}
        db_candidates: list[RecommendationCandidate] = []

        for cand in candidates_raw:
            cid = cand["id"]
            is_frontier = cid in pareto_res.frontier_candidate_ids
            dom_by = pareto_res.dominated_by.get(cid, [])
            dominates = pareto_res.dominates.get(cid, [])
            w_score = weighted_scores_map.get(cid)

            explanation = ExplanationEngine.explain_candidate(
                candidate_id=cid,
                label=cand["candidate_label"],
                eligibility_status=cand["eligibility_status"],
                exclusion_reasons=cand["exclusion_reasons"],
                is_frontier_member=is_frontier,
                dominating_ids=dom_by,
                dominated_ids=dominates,
                raw_values=cand["raw_metrics"],
                evidence_summary=cand["evidence_summary"],
                all_candidates_map=candidates_map,
            )

            db_cand = RecommendationCandidate(
                recommendation_run_id=rec_run.id,
                experiment_id=cand["experiment_id"],
                experiment_trial_id=cand["trial_id"],
                candidate_label=cand["candidate_label"],
                configuration_digest=cand["configuration_digest"],
                configuration_json=cand["configuration_json"],
                evaluation_run_id=cand["evaluation_run_id"],
                dataset_id=cand["dataset_id"],
                dataset_version_id=cand["dataset_version_id"],
                evaluation_suite_id=cand["evaluation_suite_id"],
                evaluation_suite_version_id=cand["evaluation_suite_version_id"],
                evaluation_split=cand["evaluation_split"],
                hardware_profile_key=cand["hardware_profile_key"],
                provenance_status=comp_result.candidate_statuses.get(cid, CandidateProvenanceStatus.VERIFIED),
                eligibility_status=cand["eligibility_status"],
                exclusion_reasons_json=json.dumps(cand["exclusion_reasons"]),
                objective_values_json=json.dumps(cand["raw_metrics"], default=str),
                normalized_objective_values_json=json.dumps(cand["normalized_objective_values"]),
                constraint_results_json=json.dumps(cand["constraint_details"]),
                pareto_frontier_member=is_frontier,
                dominated_by_json=json.dumps(dom_by),
                dominates_json=json.dumps(dominates),
                weighted_score=w_score,
                evidence_summary_json=json.dumps(cand["evidence_summary"]),
                explanation_text=explanation,
            )
            db.add(db_cand)
            db_candidates.append(db_cand)

        # 13. Persist Scenarios if generated
        if weighted_res:
            sc_record = RecommendationScenario(
                recommendation_run_id=rec_run.id,
                scenario_name=weighted_res.scenario_name,
                weight_snapshot_json=json.dumps(weighted_res.weights),
                ranking_snapshot_json=json.dumps([d.model_dump() for d in weighted_res.ranked_candidates]),
                explanation=weighted_res.ranking_explanation,
            )
            db.add(sc_record)

        if sensitivity_report:
            sens_record = RecommendationScenario(
                recommendation_run_id=rec_run.id,
                scenario_name="Preference Sensitivity Analysis",
                weight_snapshot_json=json.dumps(active_weights),
                ranking_snapshot_json=json.dumps(sensitivity_report.model_dump()),
                explanation=(
                    f"Sensitivity analysis evaluated across {len(sensitivity_report.evaluated_scenarios)} scenarios. "
                    f"Ranking flips detected: {sensitivity_report.ranking_flips_detected}."
                ),
            )
            db.add(sens_record)

        # 14. Compute Result Digest and Finalize Run Status
        result_payload = {
            "input_digest": input_digest,
            "frontier_candidate_ids": pareto_res.frontier_candidate_ids,
            "eligible_candidates_count": len(eligible_raw),
            "normalization_bounds": norm_snapshot.model_dump() if norm_snapshot else {},
        }
        result_digest = compute_canonical_digest(result_payload)

        rec_run.result_digest = result_digest
        rec_run.normalization_snapshot_json = (
            json.dumps(norm_snapshot.model_dump()) if norm_snapshot else None
        )
        rec_run.eligible_candidates = len(eligible_raw)
        rec_run.frontier_candidates = len(pareto_res.frontier_candidate_ids)
        rec_run.status = (
            RecommendationRunStatus.COMPLETED
            if comp_result.is_cohort_comparable and len(eligible_raw) > 0
            else RecommendationRunStatus.COMPLETED_WITH_WARNINGS
        )
        rec_run.completed_at = datetime.now(UTC)

        # Audit Event
        event = RecommendationEvent(
            recommendation_run_id=rec_run.id,
            actor_id=user_id,
            event_type="RECOMMENDATION_RUN_COMPLETED",
            metadata_json=json.dumps({
                "total_candidates": len(rows),
                "eligible_candidates": len(eligible_raw),
                "frontier_candidates": len(pareto_res.frontier_candidate_ids),
                "input_digest": input_digest,
                "result_digest": result_digest,
            }),
        )
        db.add(event)

        db.commit()
        db.refresh(rec_run)
        return rec_run

    # --------------------------------------------------------------------------
    # Retrieval & Reporting
    # --------------------------------------------------------------------------

    @staticmethod
    def get_recommendation_run(
        db: Session,
        run_id: str,
        workspace_id: str,
    ) -> RecommendationRun | None:
        """Retrieve a recommendation run with tenant isolation."""
        return db.scalars(
            select(RecommendationRun).where(
                RecommendationRun.id == run_id,
                RecommendationRun.workspace_id == workspace_id,
            )
        ).first()

    @staticmethod
    def list_recommendation_runs(
        db: Session,
        workspace_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[RecommendationRun], int]:
        """List recommendation runs in a workspace with pagination."""
        count = len(list(db.scalars(
            select(RecommendationRun.id).where(RecommendationRun.workspace_id == workspace_id)
        ).all()))

        items = list(
            db.scalars(
                select(RecommendationRun)
                .where(RecommendationRun.workspace_id == workspace_id)
                .order_by(RecommendationRun.created_at.desc())
                .offset(skip)
                .limit(limit)
            ).all()
        )
        return items, count

    @classmethod
    def archive_recommendation_run(
        cls,
        db: Session,
        run_id: str,
        workspace_id: str,
        user_id: str,
    ) -> RecommendationRun:
        """Archive a recommendation run."""
        rec_run = cls.get_recommendation_run(db, run_id, workspace_id)
        if not rec_run:
            raise ValueError(f"Recommendation run '{run_id}' not found.")

        rec_run.status = RecommendationRunStatus.ARCHIVED

        event = RecommendationEvent(
            recommendation_run_id=rec_run.id,
            actor_id=user_id,
            event_type="RECOMMENDATION_RUN_ARCHIVED",
            metadata_json=json.dumps({"status": "ARCHIVED"}),
        )
        db.add(event)
        db.commit()
        db.refresh(rec_run)
        return rec_run

    @classmethod
    def record_decision(
        cls,
        db: Session,
        run_id: str,
        workspace_id: str,
        user_id: str,
        req: RecordDecisionRequest,
    ) -> RecommendationDecision:
        """Record a human review decision on an evaluated candidate or run."""
        rec_run = cls.get_recommendation_run(db, run_id, workspace_id)
        if not rec_run:
            raise ValueError(f"Recommendation run '{run_id}' not found.")

        decision = RecommendationDecision(
            recommendation_run_id=run_id,
            selected_candidate_id=req.selected_candidate_id,
            decision=req.decision,
            decision_reason=req.decision_reason,
            actor_id=user_id,
        )
        db.add(decision)

        # Audit Event
        event = RecommendationEvent(
            recommendation_run_id=run_id,
            actor_id=user_id,
            event_type="RECOMMENDATION_DECISION_RECORDED",
            metadata_json=json.dumps({
                "decision": req.decision.value,
                "selected_candidate_id": req.selected_candidate_id,
            }),
        )
        db.add(event)

        db.commit()
        db.refresh(decision)
        return decision

    @classmethod
    def export_report(
        cls,
        db: Session,
        run_id: str,
        workspace_id: str,
        format_type: str = "json",
    ) -> tuple[str, str]:
        """Export recommendation report in JSON, Markdown, or CSV format.

        Returns:
            (content_string, media_type)
        """
        rec_run = cls.get_recommendation_run(db, run_id, workspace_id)
        if not rec_run:
            raise ValueError(f"Recommendation run '{run_id}' not found.")

        candidates_data = []
        for c in rec_run.candidates:
            candidates_data.append({
                "id": c.id,
                "candidate_label": c.candidate_label,
                "eligibility_status": c.eligibility_status.value,
                "pareto_frontier_member": c.pareto_frontier_member,
                "weighted_score": c.weighted_score,
                "objective_values": c.objective_values,
                "normalized_objective_values": c.normalized_objective_values,
                "exclusion_reasons": json.loads(c.exclusion_reasons_json) if c.exclusion_reasons_json else [],
                "explanation_text": c.explanation_text,
                "configuration_digest": c.configuration_digest,
            })

        run_dict = {
            "id": rec_run.id,
            "name": rec_run.name,
            "description": rec_run.description,
            "status": rec_run.status.value,
            "algorithm_version": rec_run.algorithm_version,
            "input_digest": rec_run.input_digest,
            "result_digest": rec_run.result_digest,
            "total_candidates": rec_run.total_candidates,
            "eligible_candidates": rec_run.eligible_candidates,
            "frontier_candidates": rec_run.frontier_candidates,
            "created_at": rec_run.created_at.isoformat(),
            "completed_at": rec_run.completed_at.isoformat() if rec_run.completed_at else None,
            "candidates": candidates_data,
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "weight_snapshot": s.weight_snapshot,
                    "ranking_snapshot": s.ranking_snapshot,
                    "explanation": s.explanation,
                }
                for s in rec_run.scenarios
            ],
            "decisions": [
                {
                    "decision": d.decision.value,
                    "decision_reason": d.decision_reason,
                    "actor_id": d.actor_id,
                    "created_at": d.created_at.isoformat(),
                }
                for d in rec_run.decisions
            ],
        }

        fmt = format_type.lower()
        if fmt == "markdown" or fmt == "md":
            return RecommendationReportService.generate_markdown_report(run_dict), "text/markdown"
        elif fmt == "csv":
            return RecommendationReportService.generate_csv_report(candidates_data), "text/csv"
        else:
            return RecommendationReportService.generate_json_report(run_dict), "application/json"
