"""Mizan Milestone 9: Recommendation Engine & Multi-Objective Optimization Module."""

from app.modules.recommendations.comparability_service import ComparabilityService
from app.modules.recommendations.constraint_engine import ConstraintEngine
from app.modules.recommendations.explanation_engine import ExplanationEngine
from app.modules.recommendations.normalization_service import NormalizationService
from app.modules.recommendations.objective_registry import (
    SUPPORTED_OBJECTIVES,
    ObjectiveDefinition,
    ObjectiveRegistry,
    OptimizationDirection,
)
from app.modules.recommendations.pareto_engine import ParetoEngine
from app.modules.recommendations.recommendation_report import RecommendationReportService
from app.modules.recommendations.recommendation_service import (
    RecommendationService,
    compute_canonical_digest,
)
from app.modules.recommendations.sensitivity_analysis import SensitivityAnalysisEngine
from app.modules.recommendations.weighted_scoring import (
    PREFERENCE_PRESETS,
    WeightedScoringEngine,
)

__all__ = [
    "ComparabilityService",
    "ConstraintEngine",
    "ExplanationEngine",
    "NormalizationService",
    "ObjectiveDefinition",
    "ObjectiveRegistry",
    "OptimizationDirection",
    "PREFERENCE_PRESETS",
    "ParetoEngine",
    "RecommendationReportService",
    "RecommendationService",
    "SUPPORTED_OBJECTIVES",
    "SensitivityAnalysisEngine",
    "WeightedScoringEngine",
    "compute_canonical_digest",
]
