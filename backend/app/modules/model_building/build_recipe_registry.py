"""Centralized registry of model building, fine-tuning, conversion, and quantization recipes."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.model_building import ModelBuildRecipe, RecipeType

# Architecture-specific target module maps for LoRA/QLoRA
ARCHITECTURE_TARGET_MODULES: dict[str, list[str]] = {
    "LlamaForCausalLM": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "Qwen2ForCausalLM": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "MistralForCausalLM": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "GPT2LMHeadModel": [
        "c_attn",
        "c_proj",
    ],
}

STANDARD_BUILD_RECIPES: list[dict[str, Any]] = [
    {
        "recipe_key": "SMOKE_TEST_CPU",
        "recipe_version": "1.0.0",
        "recipe_type": RecipeType.SMOKE_TEST,
        "name": "Deterministic CPU Smoke Test (Local)",
        "description": "Safe, lightweight local CPU execution using miniature test model and mock adapter simulation. Verifies end-to-end pipeline with $0 spend.",
        "supported_architectures_json": json.dumps(
            ["LlamaForCausalLM", "Qwen2ForCausalLM", "GPT2LMHeadModel"]
        ),
        "supported_runtimes_json": json.dumps(["CPU"]),
        "configuration_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "learning_rate": {"type": "number", "default": 0.0002},
                    "epochs": {"type": "integer", "default": 1},
                    "max_steps": {"type": "integer", "default": 5},
                    "batch_size": {"type": "integer", "default": 1},
                    "lora_rank": {"type": "integer", "default": 4},
                    "lora_alpha": {"type": "integer", "default": 8},
                },
            }
        ),
        "default_config_json": json.dumps(
            {
                "learning_rate": 0.0002,
                "epochs": 1,
                "max_steps": 5,
                "batch_size": 1,
                "lora_rank": 4,
                "lora_alpha": 8,
            }
        ),
        "dependency_lock_json": json.dumps(
            {
                "python": ">=3.11",
                "torch": ">=2.2.0",
            }
        ),
        "resource_requirements_json": json.dumps(
            {
                "min_ram_mb": 1024,
                "min_vram_mb": 0,
                "min_disk_mb": 500,
                "requires_gpu": False,
                "max_parameter_count_millions": 150.0,
            }
        ),
        "is_executable_locally": True,
    },
    {
        "recipe_key": "LORA_COLAB_FREE",
        "recipe_version": "1.0.0",
        "recipe_type": RecipeType.LORA_FINETUNE,
        "name": "LoRA Adapter Fine-Tuning (Colab Free T4)",
        "description": "Parameter-efficient LoRA adapter training in 16-bit precision designed for Google Colab Free T4 GPU (15 GB VRAM).",
        "supported_architectures_json": json.dumps(
            ["LlamaForCausalLM", "Qwen2ForCausalLM", "MistralForCausalLM"]
        ),
        "supported_runtimes_json": json.dumps(["COLAB_FREE_T4", "GPU_T4"]),
        "configuration_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "learning_rate": {"type": "number", "default": 0.0002},
                    "epochs": {"type": "integer", "default": 3},
                    "max_steps": {"type": "integer", "default": 100},
                    "batch_size": {"type": "integer", "default": 2},
                    "gradient_accumulation_steps": {"type": "integer", "default": 4},
                    "lora_rank": {"type": "integer", "default": 16},
                    "lora_alpha": {"type": "integer", "default": 32},
                    "lora_dropout": {"type": "number", "default": 0.05},
                    "target_modules": {"type": "array", "items": {"type": "string"}},
                    "weight_decay": {"type": "number", "default": 0.01},
                    "warmup_ratio": {"type": "number", "default": 0.05},
                },
                "required": ["lora_rank", "lora_alpha"],
            }
        ),
        "default_config_json": json.dumps(
            {
                "learning_rate": 0.0002,
                "epochs": 3,
                "max_steps": 100,
                "batch_size": 2,
                "gradient_accumulation_steps": 4,
                "lora_rank": 16,
                "lora_alpha": 32,
                "lora_dropout": 0.05,
                "target_modules": ["q_proj", "v_proj"],
                "weight_decay": 0.01,
                "warmup_ratio": 0.05,
            }
        ),
        "dependency_lock_json": json.dumps(
            {
                "python": "3.11",
                "torch": "2.5.1",
                "transformers": "4.46.3",
                "peft": "0.13.2",
                "accelerate": "1.1.1",
            }
        ),
        "resource_requirements_json": json.dumps(
            {
                "min_ram_mb": 8192,
                "min_vram_mb": 12000,
                "min_disk_mb": 15000,
                "requires_gpu": True,
                "max_parameter_count_millions": 3000.0,
            }
        ),
        "is_executable_locally": False,
    },
    {
        "recipe_key": "QLORA_COLAB_FREE",
        "recipe_version": "1.0.0",
        "recipe_type": RecipeType.QLORA_FINETUNE,
        "name": "QLoRA 4-bit NF4 Quantized Fine-Tuning (Colab Free T4)",
        "description": "4-bit NormalFloat base model quantization with 16-bit LoRA adapter training via bitsandbytes, fitting up to 3B models in Colab Free T4 VRAM.",
        "supported_architectures_json": json.dumps(
            ["LlamaForCausalLM", "Qwen2ForCausalLM", "MistralForCausalLM"]
        ),
        "supported_runtimes_json": json.dumps(["COLAB_FREE_T4", "GPU_T4"]),
        "configuration_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "learning_rate": {"type": "number", "default": 0.0002},
                    "epochs": {"type": "integer", "default": 3},
                    "max_steps": {"type": "integer", "default": 100},
                    "batch_size": {"type": "integer", "default": 2},
                    "gradient_accumulation_steps": {"type": "integer", "default": 4},
                    "lora_rank": {"type": "integer", "default": 16},
                    "lora_alpha": {"type": "integer", "default": 32},
                    "lora_dropout": {"type": "number", "default": 0.05},
                    "quant_type": {"type": "string", "enum": ["nf4", "fp4"], "default": "nf4"},
                    "use_double_quant": {"type": "boolean", "default": True},
                },
                "required": ["lora_rank", "lora_alpha"],
            }
        ),
        "default_config_json": json.dumps(
            {
                "learning_rate": 0.0002,
                "epochs": 3,
                "max_steps": 100,
                "batch_size": 2,
                "gradient_accumulation_steps": 4,
                "lora_rank": 16,
                "lora_alpha": 32,
                "lora_dropout": 0.05,
                "quant_type": "nf4",
                "use_double_quant": True,
            }
        ),
        "dependency_lock_json": json.dumps(
            {
                "python": "3.11",
                "torch": "2.5.1",
                "transformers": "4.46.3",
                "peft": "0.13.2",
                "bitsandbytes": "0.44.1",
                "accelerate": "1.1.1",
            }
        ),
        "resource_requirements_json": json.dumps(
            {
                "min_ram_mb": 8192,
                "min_vram_mb": 8000,
                "min_disk_mb": 15000,
                "requires_gpu": True,
                "max_parameter_count_millions": 7000.0,
            }
        ),
        "is_executable_locally": False,
    },
    {
        "recipe_key": "GGUF_CONVERT_AND_QUANTIZE",
        "recipe_version": "1.0.0",
        "recipe_type": RecipeType.GGUF_CONVERT_QUANTIZE,
        "name": "Two-Stage GGUF Conversion and llama.cpp Quantization",
        "description": "Converts Hugging Face FP16 model to high-precision GGUF baseline, then quantizes to Q8_0 and Q4_K_M formats via llama.cpp quantizer.",
        "supported_architectures_json": json.dumps(
            ["LlamaForCausalLM", "Qwen2ForCausalLM", "MistralForCausalLM"]
        ),
        "supported_runtimes_json": json.dumps(["COLAB_FREE_CPU", "COLAB_FREE_T4", "CPU"]),
        "configuration_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "source_precision": {"type": "string", "enum": ["fp16", "bf16"], "default": "fp16"},
                    "quantization_formats": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["Q8_0", "Q4_K_M"]},
                        "default": ["Q8_0", "Q4_K_M"],
                    },
                    "allow_requantize": {"type": "boolean", "default": False},
                },
                "required": ["quantization_formats"],
            }
        ),
        "default_config_json": json.dumps(
            {
                "source_precision": "fp16",
                "quantization_formats": ["Q8_0", "Q4_K_M"],
                "allow_requantize": False,
            }
        ),
        "dependency_lock_json": json.dumps(
            {
                "python": "3.11",
                "llama_cpp_release": "b3900",
                "gguf": "0.10.0",
            }
        ),
        "resource_requirements_json": json.dumps(
            {
                "min_ram_mb": 6000,
                "min_vram_mb": 0,
                "min_disk_mb": 20000,
                "requires_gpu": False,
                "max_parameter_count_millions": 7000.0,
            }
        ),
        "is_executable_locally": False,  # Conversion of multi-GB models exceeds local 8 GB RAM headroom
    },
    {
        "recipe_key": "AWQ_QUANTIZE_COMPATIBLE",
        "recipe_version": "1.0.0",
        "recipe_type": RecipeType.AWQ_QUANTIZE,
        "name": "Activation-Aware Weight Quantization (AutoAWQ 4-bit)",
        "description": "Distinct 4-bit AWQ quantization with calibration data for high-throughput GPU serving. Strictly separate from GGUF.",
        "supported_architectures_json": json.dumps(
            ["LlamaForCausalLM", "Qwen2ForCausalLM", "MistralForCausalLM"]
        ),
        "supported_runtimes_json": json.dumps(["COLAB_FREE_T4", "GPU_CUDA_75"]),
        "configuration_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "w_bit": {"type": "integer", "default": 4},
                    "q_group_size": {"type": "integer", "default": 128},
                    "zero_point": {"type": "boolean", "default": True},
                    "version": {"type": "string", "default": "GEMM"},
                },
            }
        ),
        "default_config_json": json.dumps(
            {
                "w_bit": 4,
                "q_group_size": 128,
                "zero_point": True,
                "version": "GEMM",
            }
        ),
        "dependency_lock_json": json.dumps(
            {
                "python": "3.11",
                "torch": "2.5.1",
                "autoawq": "0.2.7",
                "cuda": ">=12.1",
            }
        ),
        "resource_requirements_json": json.dumps(
            {
                "min_ram_mb": 8192,
                "min_vram_mb": 12000,
                "min_disk_mb": 20000,
                "requires_gpu": True,
                "max_parameter_count_millions": 3000.0,
            }
        ),
        "is_executable_locally": False,
    },
]


def sync_build_recipes(db: Session) -> list[ModelBuildRecipe]:
    """Ensure all standard recipes are seeded and up to date in the database."""
    recipes: list[ModelBuildRecipe] = []
    for entry in STANDARD_BUILD_RECIPES:
        existing = (
            db.query(ModelBuildRecipe)
            .filter(
                ModelBuildRecipe.recipe_key == entry["recipe_key"],
                ModelBuildRecipe.recipe_version == entry["recipe_version"],
            )
            .first()
        )
        if not existing:
            item = ModelBuildRecipe(
                recipe_key=entry["recipe_key"],
                recipe_version=entry["recipe_version"],
                recipe_type=entry["recipe_type"],
                name=entry["name"],
                description=entry["description"],
                supported_architectures_json=entry["supported_architectures_json"],
                supported_runtimes_json=entry["supported_runtimes_json"],
                configuration_schema_json=entry["configuration_schema_json"],
                default_config_json=entry["default_config_json"],
                dependency_lock_json=entry["dependency_lock_json"],
                resource_requirements_json=entry["resource_requirements_json"],
                is_executable_locally=entry["is_executable_locally"],
                is_active=True,
            )
            db.add(item)
            recipes.append(item)
        else:
            recipes.append(existing)
    db.commit()
    return recipes


def validate_recipe_compatibility(
    recipe: ModelBuildRecipe,
    model_architecture: str,
    training_config: dict[str, Any],
) -> list[str]:
    """Validate that architecture and hyperparameters conform to recipe schema and architecture rules.

    Returns list of validation error strings (empty if valid).
    """
    errors: list[str] = []

    # 1. Architecture compatibility check
    supported_archs = recipe.supported_architectures
    if supported_archs and model_architecture not in supported_archs:
        errors.append(
            f"Model architecture '{model_architecture}' is not supported by recipe '{recipe.recipe_key}'. "
            f"Supported architectures: {supported_archs}"
        )

    # 2. LoRA / QLoRA specific checks
    if recipe.recipe_type in (RecipeType.LORA_FINETUNE, RecipeType.QLORA_FINETUNE):
        rank = training_config.get("lora_rank")
        if rank is not None and (not isinstance(rank, int) or rank <= 0 or rank > 256):
            errors.append(f"Invalid lora_rank '{rank}'. Expected positive integer <= 256.")

        alpha = training_config.get("lora_alpha")
        if alpha is not None and (not isinstance(alpha, int) or alpha <= 0 or alpha > 512):
            errors.append(f"Invalid lora_alpha '{alpha}'. Expected positive integer <= 512.")

        # Architecture-aware target module validation
        target_mods = training_config.get("target_modules")
        if target_mods:
            valid_mods = ARCHITECTURE_TARGET_MODULES.get(model_architecture)
            if valid_mods:
                for mod in target_mods:
                    if mod not in valid_mods:
                        errors.append(
                            f"Target module '{mod}' is invalid for architecture '{model_architecture}'. "
                            f"Permitted modules: {valid_mods}"
                        )

    # 3. GGUF checks
    if recipe.recipe_type == RecipeType.GGUF_CONVERT_QUANTIZE:
        allow_requantize = training_config.get("allow_requantize", False)
        if allow_requantize:
            errors.append(
                "Requantization of already quantized models is blocked by policy due to severe quality degradation."
            )
        quants = training_config.get("quantization_formats", [])
        valid_quants = {"Q8_0", "Q4_K_M"}
        for q in quants:
            if q not in valid_quants:
                errors.append(f"Unsupported GGUF quantization format '{q}'. Expected one of {list(valid_quants)}")

    # 4. AWQ separation check
    if recipe.recipe_type == RecipeType.AWQ_QUANTIZE:
        w_bit = training_config.get("w_bit", 4)
        if w_bit != 4:
            errors.append(f"AWQ currently supports w_bit=4, received {w_bit}.")

    return errors
