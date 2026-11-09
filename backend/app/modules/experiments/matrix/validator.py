"""Validation rules for trial configurations and trial matrices."""

from __future__ import annotations

from typing import Any

from app.modules.experiments.digest import compute_canonical_config_digest
from app.modules.experiments.schemas.trial import TrialConfig


def validate_trial_matrix(
    raw_trials: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate a candidate trial matrix against M7 bounded constraints.

    Rules:
    - Minimum 3 trials.
    - Maximum 9 trials.
    - Every trial must conform to TrialConfig schema.
    - All trial configurations must be unique (distinct SHA-256 canonical digests).
    """
    if len(raw_trials) < 3:
        raise ValueError(
            f"Trial matrix requires at least 3 unique trials to be comparable, got {len(raw_trials)}."
        )
    if len(raw_trials) > 9:
        raise ValueError(
            f"Trial matrix cannot exceed 9 trials under local resource limits, got {len(raw_trials)}."
        )

    validated_trials = []
    seen_digests: set[str] = set()

    for idx, raw in enumerate(raw_trials, start=1):
        # Extract metadata
        trial_name = raw.get("_trial_name") or raw.get("name") or f"Trial {idx}"

        # Clean config dictionary: support both nested "configuration" and flat dicts
        if "configuration" in raw and isinstance(raw["configuration"], dict):
            config_dict = raw["configuration"]
        else:
            config_dict = {
                k: v
                for k, v in raw.items()
                if not k.startswith("_")
                and k not in ("name", "trial_number", "configuration_digest", "id", "status")
            }

        # Validate with TrialConfig schema
        try:
            cfg = TrialConfig(**config_dict)
            dumped = cfg.model_dump()
        except Exception as exc:
            raise ValueError(f"Trial {idx} configuration invalid: {exc}") from exc

        digest = compute_canonical_config_digest(dumped)
        if digest in seen_digests:
            raise ValueError(
                f"Duplicate configuration detected: Trial {idx} ('{trial_name}') matches an earlier trial."
            )
        seen_digests.add(digest)

        validated_trials.append(
            {
                "trial_number": idx,
                "name": trial_name,
                "configuration": dumped,
                "configuration_digest": digest,
            }
        )

    return validated_trials
