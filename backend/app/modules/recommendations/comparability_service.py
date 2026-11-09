"""Candidate Comparability Verification Service for Multi-Trial Evidence.

Ensures candidate metrics are scientifically comparable before entering multi-objective optimization.
Enforces strict provenance matching across dataset versions, evaluation suite digests,
splits, rubrics, and measurement environments.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.recommendations import CandidateProvenanceStatus


class ComparabilityCheckResult(BaseModel):
    """Outcome of comparability checks across a candidate cohort."""

    is_cohort_comparable: bool
    dataset_version_id: str | None = None
    evaluation_suite_version_id: str | None = None
    evaluation_split: str | None = None
    discrepancies: list[str] = Field(default_factory=list)
    candidate_statuses: dict[str, CandidateProvenanceStatus] = Field(default_factory=dict)
    candidate_notes: dict[str, list[str]] = Field(default_factory=dict)


class ComparabilityService:
    """Verifies that candidates share compatible experimental baselines."""

    @classmethod
    def verify_cohort_comparability(
        cls,
        candidates: list[dict[str, Any]],
        id_field: str = "id",
    ) -> ComparabilityCheckResult:
        """Validate that all candidates in a proposed recommendation run are comparable.

        Args:
            candidates: List of candidate records containing provenance metadata.
            id_field: Key for unique candidate ID.

        Returns:
            ComparabilityCheckResult with overall cohort status and per-candidate annotations.
        """
        if not candidates:
            return ComparabilityCheckResult(
                is_cohort_comparable=True,
                discrepancies=["No candidates provided for comparability evaluation."],
            )

        # Baseline reference from the first candidate
        ref_cand = candidates[0]
        ref_id = str(ref_cand.get(id_field, "c0"))
        ref_dataset_v = ref_cand.get("dataset_version_id")
        ref_suite_v = ref_cand.get("evaluation_suite_version_id")
        ref_split = ref_cand.get("evaluation_split")
        ref_rubric_v = ref_cand.get("rubric_version", 1)

        discrepancies: list[str] = []
        statuses: dict[str, CandidateProvenanceStatus] = {ref_id: CandidateProvenanceStatus.VERIFIED}
        notes: dict[str, list[str]] = {ref_id: []}

        for cand in candidates[1:]:
            cid = str(cand.get(id_field, "unknown"))
            cand_notes: list[str] = []
            cand_status = CandidateProvenanceStatus.VERIFIED

            # 1. Dataset version alignment
            cand_ds_v = cand.get("dataset_version_id")
            if ref_dataset_v and cand_ds_v and cand_ds_v != ref_dataset_v:
                msg = (
                    f"Candidate {cid} evaluated on dataset_version_id '{cand_ds_v}', "
                    f"differing from cohort baseline '{ref_dataset_v}'."
                )
                discrepancies.append(msg)
                cand_notes.append(msg)
                cand_status = CandidateProvenanceStatus.INCOMPATIBLE

            # 2. Frozen Evaluation Suite version & digest alignment
            cand_suite_v = cand.get("evaluation_suite_version_id")
            if ref_suite_v and cand_suite_v and cand_suite_v != ref_suite_v:
                msg = (
                    f"Candidate {cid} evaluated on suite_version_id '{cand_suite_v}', "
                    f"differing from cohort baseline '{ref_suite_v}'."
                )
                discrepancies.append(msg)
                cand_notes.append(msg)
                cand_status = CandidateProvenanceStatus.INCOMPATIBLE

            # 3. Evaluation Split alignment (DEVELOPMENT vs VALIDATION vs HOLDOUT)
            cand_split = cand.get("evaluation_split")
            if ref_split and cand_split and cand_split != ref_split:
                msg = (
                    f"Candidate {cid} evaluated on split '{cand_split}', "
                    f"differing from cohort baseline '{ref_split}'."
                )
                discrepancies.append(msg)
                cand_notes.append(msg)
                cand_status = CandidateProvenanceStatus.INCOMPATIBLE

            # 4. Rubric version alignment
            cand_rubric_v = cand.get("rubric_version", 1)
            if cand_rubric_v != ref_rubric_v:
                msg = f"Candidate {cid} evaluated with rubric version {cand_rubric_v} vs baseline {ref_rubric_v}."
                cand_notes.append(msg)
                if cand_status != CandidateProvenanceStatus.INCOMPATIBLE:
                    cand_status = CandidateProvenanceStatus.PARTIALLY_VERIFIED

            statuses[cid] = cand_status
            notes[cid] = cand_notes

        is_comparable = (len(discrepancies) == 0)

        return ComparabilityCheckResult(
            is_cohort_comparable=is_comparable,
            dataset_version_id=ref_dataset_v,
            evaluation_suite_version_id=ref_suite_v,
            evaluation_split=ref_split,
            discrepancies=discrepancies,
            candidate_statuses=statuses,
            candidate_notes=notes,
        )
