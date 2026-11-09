# Milestone 10: Google Colab Free Lab Operator Guide

## 1. The Colab Free Infrastructure Model ($0.00 Spend)

To respect Mizan's strict non-negotiable **$0.00 additional spend policy**, GPU training and heavy quantization workloads are executed using **Google Colab Free**.

### Why Manual User-Operated Execution?
1. Google Colab Free does not provide an automated headless API; attempting to programmatically scrape or automate Colab sessions violates Google terms of service.
2. Cloud GPU instances (AWS EC2, GCP Compute Engine, RunPod) incur hourly dollar costs that violate the $0.00 spend policy.
3. Operating Colab Free interactively in the developer's browser provides access to a dedicated **NVIDIA Tesla T4 GPU (16 GB VRAM)** with zero billing accounts, zero credit cards, and zero cloud API keys.

---

## 2. Pinned Dependency Locks

All exported notebooks embed locked, tested Python package versions to guarantee exact reproducibility:

```python
DEPENDENCY_LOCK = {
    "python": "3.11",
    "torch": "2.5.1",
    "transformers": "4.46.3",
    "peft": "0.13.2",
    "accelerate": "1.1.1",
    "bitsandbytes": "0.44.1",
    "safetensors": "0.4.5",
}
```

---

## 3. End-to-End Workflow Walkthrough

### Step 1: Export Colab Notebook from Mizan
1. Navigate to **Model Building** in the Mizan web interface.
2. Select your build run and click **Google Colab Lab & Staging**.
3. Click **Download .ipynb Notebook** and **Download build_manifest.json**.
4. Note the canonical `manifest_digest` displayed on the drawer.

### Step 2: Open and Configure Runtime in Google Colab
1. Navigate to [Google Colab](https://colab.research.google.com).
2. Click **Upload** and upload the downloaded `.ipynb` notebook.
3. Set execution hardware: Click **Runtime → Change runtime type**.
4. Under *Hardware accelerator*, select **T4 GPU**. Under *GPU type*, select **Standard**. Click **Save**.

### Step 3: Run Training Cells Sequentially
1. **Cell 1 (Environment Preflight):** Verifies that a valid NVIDIA GPU is attached (`torch.cuda.is_available()`) and checks available VRAM ($\ge 12\text{ GB}$).
2. **Cell 2 (Dependencies):** Installs pinned library versions from the dependency lock.
3. **Cell 3 (Manifest Verification):** Reads the embedded build manifest and confirms the SHA-256 digest matches Mizan's expectation.
4. **Cell 4 (Model Loading & Adaptation):** Loads base weights in 16-bit or 4-bit NF4, initializes LoRA matrices on verified target modules, and validates the trainable parameter ratio (~0.5-1.5%).
5. **Cell 5 (Training & Checkpoints):** Trains the adapter across configured steps, saving intermediate checkpoints and computing loss metrics.
6. **Cell 6 (Export & Checksum Calculation):** Saves the final adapter weights or quantized GGUF file and outputs its exact byte size and SHA-256 checksum.

### Step 4: Import Staged Artifact into Mizan
1. Return to Mizan and open the **Google Colab Lab & Staging** drawer.
2. In the **Import Staged Artifact** form, enter:
   - **Artifact Type:** `LORA_ADAPTER` or `GGUF_QUANTIZED`
   - **Format:** `SAFETENSORS` or `GGUF`
   - **SHA-256 Checksum:** 64-character hex hash computed in Cell 6.
   - **File Size:** Output byte size.
3. Click **Stage Artifact for Review**.
4. The artifact is validated, staged into Mizan storage, and tagged as `Staged for M11`.
