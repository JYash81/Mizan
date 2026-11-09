# Milestone 10: LoRA and QLoRA Training Recipes

## 1. Overview & Parameter-Efficient Fine-Tuning (PEFT)

Full-parameter fine-tuning of modern LLMs requires extensive VRAM (typically 16-20 bytes per parameter including AdamW optimizer states and FP32 gradients). On free-tier hardware such as Google Colab Free (16 GB T4 GPU) or local CPU workstations (8 GB RAM), full fine-tuning is infeasible and prohibited by Mizan's $0.00 spend policy.

Milestone 10 standardizes **Low-Rank Adaptation (LoRA)** and **Quantized Low-Rank Adaptation (QLoRA)** recipes that constrain trainable parameters to low-rank decomposition matrices ($W = W_0 + \Delta W = W_0 + B \times A$), freezing the base model weights.

---

## 2. Architecture-Aware Target Modules

To avoid runtime exceptions during PEFT initialization, M10 validates `target_modules` against model architectures before authorizing build runs:

| Model Architecture | Supported Base Models | Valid Target Modules |
| :--- | :--- | :--- |
| **LlamaForCausalLM** | `mizan-test/tiny-llama-35m`, `meta-llama/Llama-3.2-1B` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| **Qwen2ForCausalLM** | `Qwen/Qwen2.5-0.5B` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| **MistralForCausalLM** | `mistralai/Mistral-7B-v0.1` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| **GPT2LMHeadModel** | Miniature GPT-2 Variants | `c_attn`, `c_proj` |

Specifying target modules incompatible with the model architecture immediately returns an unprocessable entity error (422) during preflight and build run creation.

---

## 3. Standard Recipe Specifications

### 3.1 `SMOKE_TEST_CPU` (Local Execution)
- **Purpose:** Fast, deterministic local CPU validation of the entire pipeline.
- **Model Constraints:** Max 150M parameters (e.g. `mizan-test/tiny-llama-35m` or `SmolLM2-135M`).
- **Runtime:** CPU only. Requires $\le 4096\text{ MB}$ peak working RAM.
- **Default Hyperparameters:** `learning_rate: 0.0002`, `max_steps: 4`, `batch_size: 1`, `lora_rank: 8`, `lora_alpha: 16`.
- **Output:** Staged `.safetensors` adapter artifact with verified SHA-256 hash.

### 3.2 `LORA_COLAB_FREE` (Colab Free T4 GPU)
- **Purpose:** 16-bit LoRA fine-tuning for models up to 3B parameters in Google Colab Free.
- **Base Model Precision:** FP16 / BF16.
- **VRAM Footprint:** Fits comfortably within 15,360 MB VRAM of NVIDIA Tesla T4.
- **Default Hyperparameters:** `learning_rate: 0.0002`, `epochs: 3`, `max_steps: 100`, `batch_size: 2`, `gradient_accumulation_steps: 4`, `lora_rank: 16`, `lora_alpha: 32`, `lora_dropout: 0.05`.
- **Output:** Checkpoints every 25 steps, final merged or standalone LoRA adapter.

### 3.3 `QLORA_COLAB_FREE` (Colab Free T4 GPU with 4-bit NF4)
- **Purpose:** 4-bit quantized base model with 16-bit LoRA adapters (via `bitsandbytes`).
- **Base Model Precision:** NF4 (NormalFloat4) with double quantization.
- **VRAM Savings:** Reduces base model weight footprint by ~65-75%, enabling adaptation of 3B to 7B models on 16 GB T4 GPU.
- **Default Hyperparameters:** `learning_rate: 0.0002`, `epochs: 3`, `max_steps: 100`, `batch_size: 2`, `lora_rank: 16`, `lora_alpha: 32`.

---

## 4. Training/Validation Partition Integrity & Holdout Protection

To prevent test-set leakage:
1. **Deterministic Splitting:** Dataset records are partitioned into `TRAIN` and `VALIDATION` partitions using deterministic pseudo-random hashing keyed by `record_id` and an immutable seed (default `42`).
2. **Partition Digests:** Train and validation partitions receive independent SHA-256 partition digests recorded in `build_manifest.json`.
3. **M6 Holdout Split Isolation:** M6 `HOLDOUT` split records are strictly blocked from being used as training inputs. Any attempt to use holdout data fails-closed with `DatasetIntegrityError`.
