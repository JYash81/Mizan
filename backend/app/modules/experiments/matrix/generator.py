"""Deterministic trial matrix generation engine for Mizan experiments."""

from __future__ import annotations

import itertools
from typing import Any

from app.modules.experiments.matrix.presets import get_preset_configs
from app.modules.experiments.matrix.validator import validate_trial_matrix
from app.modules.experiments.schemas.experiment import MatrixGenerateStrategy
from app.modules.experiments.schemas.trial import TrialConfig


class TrialMatrixGenerator:
    """Generates bounded 3 to 9 trial matrices from presets, manual inputs, or parametric variations."""

    def generate(
        self,
        strategy: MatrixGenerateStrategy,
        baseline_config: dict[str, Any],
        preset_name: str | None = None,
        variations: dict[str, list[Any]] | None = None,
        manual_trials: list[TrialConfig] | list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate and validate a trial matrix."""
        raw_candidates: list[dict[str, Any]] = []

        if strategy == MatrixGenerateStrategy.MANUAL:
            if not manual_trials:
                raise ValueError("Manual trial strategy requires an explicit list of 3 to 9 trial configurations.")
            for t in manual_trials:
                if isinstance(t, TrialConfig):
                    raw_candidates.append(t.model_dump())
                else:
                    raw_candidates.append(t)

        elif strategy == MatrixGenerateStrategy.PRESET_MATRIX:
            p_name = preset_name or "chunk_sensitivity"
            raw_candidates = get_preset_configs(p_name, baseline_config)

        elif strategy == MatrixGenerateStrategy.PARAMETRIC_VARIATION:
            if not variations:
                raise ValueError("Parametric variation strategy requires a dictionary of variations.")

            # Filter out empty lists
            valid_vars = {k: v for k, v in variations.items() if isinstance(v, list) and len(v) > 0}
            if not valid_vars:
                raise ValueError("No valid variation parameters provided.")

            keys = list(valid_vars.keys())
            value_lists = [valid_vars[k] for k in keys]

            combinations = list(itertools.product(*value_lists))
            if len(combinations) < 3:
                raise ValueError(
                    f"Parametric variations produce only {len(combinations)} trials. At least 3 are required."
                )
            if len(combinations) > 9:
                # Clamp to first 9 to preserve bounded limit
                combinations = combinations[:9]

            for idx, combo in enumerate(combinations, start=1):
                cfg = baseline_config.copy()
                labels = []
                for k, v in zip(keys, combo):
                    cfg[k] = v
                    labels.append(f"{k}={v}")
                cfg["_trial_name"] = f"Trial {idx} ({', '.join(labels)})"
                raw_candidates.append(cfg)

        else:
            raise ValueError(f"Unsupported matrix strategy: {strategy}")

        return validate_trial_matrix(raw_candidates)
