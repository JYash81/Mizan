"""Centralized Objective Registry for Mizan Milestone 9 Multi-Objective Optimization.

Defines all supported objectives, their optimization directions, units,
provenance sources, and missing-data policies.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict


class OptimizationDirection(str, enum.Enum):
    """Direction for optimization."""

    MAXIMIZE = "MAXIMIZE"
    MINIMIZE = "MINIMIZE"
    TARGET_RANGE = "TARGET_RANGE"


class MissingDataPolicy(str, enum.Enum):
    """Policy when candidate data for this objective is missing or unavailable."""

    PRESERVE_UNKNOWN = "PRESERVE_UNKNOWN"
    EXCLUDE_FROM_DOMINANCE = "EXCLUDE_FROM_DOMINANCE"
    INELIGIBLE_IF_MANDATORY = "INELIGIBLE_IF_MANDATORY"


class ObjectiveCategory(str, enum.Enum):
    """Category of evaluation dimension."""

    QUALITY = "QUALITY"
    PERFORMANCE = "PERFORMANCE"
    RESOURCE = "RESOURCE"
    COST = "COST"
    SAFETY_COMPLIANCE = "SAFETY_COMPLIANCE"


class ObjectiveDefinition(BaseModel):
    """Definition of an optimization objective."""

    model_config = ConfigDict(frozen=True)

    key: str
    display_name: str
    category: ObjectiveCategory
    direction: OptimizationDirection
    unit: str
    description: str
    source_module: str  # "M6_EVALUATION", "M7_EXPERIMENT", "M8_RESOURCE", "M8_COST"
    source_field: str
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.PRESERVE_UNKNOWN
    min_reasonable_value: float | None = None
    max_reasonable_value: float | None = None
    is_mandatory_by_default: bool = False
    version: str = "1.0.0"


# Centralized registry of supported optimization objectives
SUPPORTED_OBJECTIVES: dict[str, ObjectiveDefinition] = {
    # 1. Quality Objectives (M6 / M7)
    "aggregate_score": ObjectiveDefinition(
        key="aggregate_score",
        display_name="Aggregate Rubric Score",
        category=ObjectiveCategory.QUALITY,
        direction=OptimizationDirection.MAXIMIZE,
        unit="pts",
        description="Overall multi-criteria rubric evaluation score (0-100 scale).",
        source_module="M7_EXPERIMENT",
        source_field="aggregate_score",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
        is_mandatory_by_default=True,
    ),
    "correctness": ObjectiveDefinition(
        key="correctness",
        display_name="Correctness & Exact Match",
        category=ObjectiveCategory.QUALITY,
        direction=OptimizationDirection.MAXIMIZE,
        unit="%",
        description="Factual correctness and token F1 / exact match accuracy.",
        source_module="M6_EVALUATION",
        source_field="exact_match",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
    ),
    "faithfulness": ObjectiveDefinition(
        key="faithfulness",
        display_name="Faithfulness Score",
        category=ObjectiveCategory.QUALITY,
        direction=OptimizationDirection.MAXIMIZE,
        unit="%",
        description="Degree to which model responses are faithful to retrieved context without hallucination.",
        source_module="M6_EVALUATION",
        source_field="faithfulness",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
    ),
    "groundedness": ObjectiveDefinition(
        key="groundedness",
        display_name="Groundedness Score",
        category=ObjectiveCategory.QUALITY,
        direction=OptimizationDirection.MAXIMIZE,
        unit="%",
        description="Alignment of claims with verified source document chunks.",
        source_module="M6_EVALUATION",
        source_field="groundedness",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
    ),
    "citation_completeness": ObjectiveDefinition(
        key="citation_completeness",
        display_name="Citation Completeness",
        category=ObjectiveCategory.QUALITY,
        direction=OptimizationDirection.MAXIMIZE,
        unit="%",
        description="Ratio of generated statements with valid, verifiable document citations.",
        source_module="M6_EVALUATION",
        source_field="citation_verification",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
    ),
    "safety": ObjectiveDefinition(
        key="safety",
        display_name="Safety & Abstention",
        category=ObjectiveCategory.SAFETY_COMPLIANCE,
        direction=OptimizationDirection.MAXIMIZE,
        unit="%",
        description="Appropriate refusal of out-of-scope or unanswerable queries.",
        source_module="M6_EVALUATION",
        source_field="safety",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
    ),
    "compliance": ObjectiveDefinition(
        key="compliance",
        display_name="Compliance Score",
        category=ObjectiveCategory.SAFETY_COMPLIANCE,
        direction=OptimizationDirection.MAXIMIZE,
        unit="%",
        description="Compliance with enterprise governance and privacy standards.",
        source_module="M6_EVALUATION",
        source_field="compliance",
        min_reasonable_value=0.0,
        max_reasonable_value=100.0,
    ),

    # 2. Performance & Latency Objectives (M7 / M6)
    "latency_p50_ms": ObjectiveDefinition(
        key="latency_p50_ms",
        display_name="Median Latency (P50)",
        category=ObjectiveCategory.PERFORMANCE,
        direction=OptimizationDirection.MINIMIZE,
        unit="ms",
        description="Median observed per-query response latency.",
        source_module="M7_EXPERIMENT",
        source_field="latency_p50_ms",
        min_reasonable_value=1.0,
        max_reasonable_value=120000.0,
    ),
    "latency_p95_ms": ObjectiveDefinition(
        key="latency_p95_ms",
        display_name="Tail Latency (P95)",
        category=ObjectiveCategory.PERFORMANCE,
        direction=OptimizationDirection.MINIMIZE,
        unit="ms",
        description="95th percentile observed per-query response latency.",
        source_module="M7_EXPERIMENT",
        source_field="latency_p95_ms",
        min_reasonable_value=1.0,
        max_reasonable_value=300000.0,
    ),
    "execution_duration_ms": ObjectiveDefinition(
        key="execution_duration_ms",
        display_name="Total Run Duration",
        category=ObjectiveCategory.PERFORMANCE,
        direction=OptimizationDirection.MINIMIZE,
        unit="ms",
        description="Total elapsed execution time for the evaluation trial workload.",
        source_module="M7_EXPERIMENT",
        source_field="execution_duration_ms",
        min_reasonable_value=10.0,
        max_reasonable_value=3600000.0,
    ),

    # 3. Resource Requirements (M8 Resource Estimator)
    "required_ram_mb": ObjectiveDefinition(
        key="required_ram_mb",
        display_name="Peak RAM / VRAM",
        category=ObjectiveCategory.RESOURCE,
        direction=OptimizationDirection.MINIMIZE,
        unit="MB",
        description="Estimated peak system RAM or GPU VRAM required for model inference.",
        source_module="M8_RESOURCE",
        source_field="peak_memory_mb",
        min_reasonable_value=100.0,
        max_reasonable_value=256000.0,
    ),
    "artifact_size_mb": ObjectiveDefinition(
        key="artifact_size_mb",
        display_name="Model Artifact Size",
        category=ObjectiveCategory.RESOURCE,
        direction=OptimizationDirection.MINIMIZE,
        unit="MB",
        description="On-disk storage required for quantized model weights and container headers.",
        source_module="M8_RESOURCE",
        source_field="artifact_size_mb",
        min_reasonable_value=50.0,
        max_reasonable_value=256000.0,
    ),
    "memory_headroom_mb": ObjectiveDefinition(
        key="memory_headroom_mb",
        display_name="Memory Headroom",
        category=ObjectiveCategory.RESOURCE,
        direction=OptimizationDirection.MAXIMIZE,
        unit="MB",
        description="Available RAM buffer remaining on the target hardware profile.",
        source_module="M8_RESOURCE",
        source_field="headroom_mb",
        min_reasonable_value=0.0,
        max_reasonable_value=256000.0,
    ),

    # 4. Cost Objectives (M8 Cost Estimator)
    "estimated_cost_usd": ObjectiveDefinition(
        key="estimated_cost_usd",
        display_name="Estimated Cost",
        category=ObjectiveCategory.COST,
        direction=OptimizationDirection.MINIMIZE,
        unit="USD",
        description="Total estimated infrastructure expenditure for the workload. Missing price returns UNKNOWN (never $0).",
        source_module="M8_COST",
        source_field="total_estimated_cost",
        missing_data_policy=MissingDataPolicy.PRESERVE_UNKNOWN,
        min_reasonable_value=0.0,
        max_reasonable_value=10000.0,
    ),
}


class ObjectiveRegistry:
    """Provides querying and validation for supported optimization objectives."""

    @staticmethod
    def get_objective(key: str) -> ObjectiveDefinition | None:
        """Retrieve objective definition by key."""
        return SUPPORTED_OBJECTIVES.get(key)

    @staticmethod
    def list_objectives() -> list[ObjectiveDefinition]:
        """List all supported objective definitions."""
        return list(SUPPORTED_OBJECTIVES.values())

    @staticmethod
    def validate_keys(keys: list[str]) -> list[str]:
        """Validate list of objective keys, returning any unknown keys."""
        return [k for k in keys if k not in SUPPORTED_OBJECTIVES]

    @staticmethod
    def get_direction(key: str) -> OptimizationDirection:
        """Get optimization direction for an objective key."""
        obj = SUPPORTED_OBJECTIVES.get(key)
        if not obj:
            raise KeyError(f"Unknown objective key: '{key}'.")
        return obj.direction
