"""Built-in controlled trial matrix presets for Mizan experiments."""

from __future__ import annotations

from typing import Any


def get_preset_configs(preset_name: str, baseline: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a validated list of 3 to 9 unique trial configurations for a standard preset."""
    name = preset_name.lower().strip()

    if name in ("chunk_sensitivity", "chunks"):
        # 3 variations: Small, Medium, Large chunks
        sizes = [
            (250, 50, "Small Chunks (250/50)"),
            (500, 100, "Medium Chunks (500/100)"),
            (1000, 200, "Large Chunks (1000/200)"),
        ]
        trials = []
        for sz, ov, label in sizes:
            cfg = baseline.copy()
            cfg["chunk_size_chars"] = sz
            cfg["chunk_overlap_chars"] = ov
            cfg["_trial_name"] = label
            trials.append(cfg)
        return trials

    elif name in ("retrieval_depth", "top_k"):
        # 3 variations: Shallow, Standard, Deep retrieval
        k_values = [
            (2, "Shallow Retrieval (k=2)"),
            (4, "Standard Retrieval (k=4)"),
            (8, "Deep Retrieval (k=8)"),
        ]
        trials = []
        for k, label in k_values:
            cfg = baseline.copy()
            cfg["top_k"] = k
            cfg["_trial_name"] = label
            trials.append(cfg)
        return trials

    elif name in ("prompt_strategy", "prompts"):
        # 3 variations: Standard, Grounded, Regulatory
        strategies = [
            ("standard_qa", "Standard QA Prompt"),
            ("precise_grounded", "Strict Groundedness Prompt"),
            ("regulatory_strict", "Regulatory Compliance Prompt"),
        ]
        trials = []
        for st, label in strategies:
            cfg = baseline.copy()
            cfg["prompt_strategy"] = st
            cfg["_trial_name"] = label
            trials.append(cfg)
        return trials

    elif name in ("chunk_and_retrieval", "grid_3x3"):
        # 9 variations: 3 chunk sizes x 3 top_k values
        trials = []
        for sz, ov in [(300, 50), (600, 100), (1200, 200)]:
            for k in [2, 4, 8]:
                cfg = baseline.copy()
                cfg["chunk_size_chars"] = sz
                cfg["chunk_overlap_chars"] = ov
                cfg["top_k"] = k
                cfg["_trial_name"] = f"Chunk {sz} / Overlap {ov} / Top-K {k}"
                trials.append(cfg)
        return trials

    raise ValueError(
        f"Unknown preset name '{preset_name}'. Supported presets: "
        "'chunk_sensitivity', 'retrieval_depth', 'prompt_strategy', 'chunk_and_retrieval'"
    )
