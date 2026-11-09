"""Deterministic Normalization Service for Multi-Objective Optimization.

Normalizes raw heterogeneous metrics (percentages, milliseconds, megabytes, dollars)
to a unified [0.0, 1.0] scale where 1.0 is always optimal and 0.0 is least desirable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.modules.recommendations.objective_registry import (
    ObjectiveRegistry,
    OptimizationDirection,
)


class ObjectiveNormalizationBounds(BaseModel):
    """Normalization metadata and bounds for a single objective."""

    objective_key: str
    direction: OptimizationDirection
    min_observed: float
    max_observed: float
    is_constant: bool = False
    valid_count: int = 0
    missing_count: int = 0


class NormalizationSnapshot(BaseModel):
    """Complete snapshot of normalization parameters for audit and reproducibility."""

    algorithm: str = "MIN_MAX_DIRECTION_AWARE"
    version: str = "1.0.0"
    bounds: dict[str, ObjectiveNormalizationBounds] = Field(default_factory=dict)


class NormalizationService:
    """Normalizes candidate metric vectors to a unified scale [0.0, 1.0]."""

    @staticmethod
    def calculate_bounds(
        candidates_raw: list[dict[str, Any]],
        objective_keys: list[str],
    ) -> NormalizationSnapshot:
        """Compute min/max bounds across all eligible candidates for each objective."""
        snapshot = NormalizationSnapshot()

        for key in objective_keys:
            direction = ObjectiveRegistry.get_direction(key)
            valid_values: list[float] = []
            missing_count = 0

            for cand in candidates_raw:
                val = cand.get(key)
                if val is not None and isinstance(val, (int, float)):
                    valid_values.append(float(val))
                else:
                    missing_count += 1

            if not valid_values:
                # No data observed
                snapshot.bounds[key] = ObjectiveNormalizationBounds(
                    objective_key=key,
                    direction=direction,
                    min_observed=0.0,
                    max_observed=0.0,
                    is_constant=True,
                    valid_count=0,
                    missing_count=missing_count,
                )
            else:
                min_val = min(valid_values)
                max_val = max(valid_values)
                is_const = (min_val == max_val)

                snapshot.bounds[key] = ObjectiveNormalizationBounds(
                    objective_key=key,
                    direction=direction,
                    min_observed=round(min_val, 4),
                    max_observed=round(max_val, 4),
                    is_constant=is_const,
                    valid_count=len(valid_values),
                    missing_count=missing_count,
                )

        return snapshot

    @staticmethod
    def normalize_value(
        raw_val: float | None,
        bounds: ObjectiveNormalizationBounds,
    ) -> float | None:
        """Normalize a single raw value using computed bounds and optimization direction.

        Returns:
            Normalized float between 0.0 (worst) and 1.0 (best), or None if value is missing.
        """
        if raw_val is None:
            return None

        # Zero-variance / constant value protection (prevents division by zero)
        if bounds.is_constant or bounds.max_observed == bounds.min_observed:
            return 1.0  # All candidates performed equally well

        val_clamped = max(bounds.min_observed, min(bounds.max_observed, float(raw_val)))
        denom = bounds.max_observed - bounds.min_observed

        if bounds.direction == OptimizationDirection.MAXIMIZE:
            norm = (val_clamped - bounds.min_observed) / denom
        elif bounds.direction == OptimizationDirection.MINIMIZE:
            norm = (bounds.max_observed - val_clamped) / denom
        else:
            # Fallback for target range or generic
            norm = (val_clamped - bounds.min_observed) / denom

        return round(max(0.0, min(1.0, norm)), 4)

    @classmethod
    def normalize_candidates(
        cls,
        candidates_raw: list[dict[str, Any]],
        objective_keys: list[str],
        snapshot: NormalizationSnapshot | None = None,
    ) -> tuple[list[dict[str, float | None]], NormalizationSnapshot]:
        """Normalize a collection of candidate raw metric dictionaries.

        Returns:
            (list of normalized dictionaries, normalization snapshot)
        """
        if snapshot is None:
            snapshot = cls.calculate_bounds(candidates_raw, objective_keys)

        normalized_candidates: list[dict[str, float | None]] = []

        for cand in candidates_raw:
            norm_dict: dict[str, float | None] = {}
            for key in objective_keys:
                bounds = snapshot.bounds.get(key)
                if bounds:
                    raw_val = cand.get(key)
                    norm_dict[key] = cls.normalize_value(raw_val, bounds)
                else:
                    norm_dict[key] = None
            normalized_candidates.append(norm_dict)

        return normalized_candidates, snapshot
