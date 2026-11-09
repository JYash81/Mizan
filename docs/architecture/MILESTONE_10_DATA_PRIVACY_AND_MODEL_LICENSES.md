# Milestone 10: Data Privacy, Gate 1 Protection & Model Licensing

## 1. Sensitive Data Protection in Model Building

Training and fine-tuning AI models on corporate data introduces significant data leakage risks if confidential information or personal identifiable information (PII) is inadvertently memorized by model weights. Milestone 10 tightly integrates with **Milestone 4 (Sensitive Data Protection & Gate 1)** to guarantee zero leakage.

### Non-Negotiable Privacy Rules:
1. **Raw Document Block:** Unmasked, raw documents uploaded to Mizan are **never** accessible to model training recipes. Any request referencing an unapproved dataset fails-closed with `Gate1ApprovalRequiredError`.
2. **Gate 1 Approval Verification:** Build runs verify that the dataset version has an active `APPROVED` Gate 1 attestation signed with Ed25519 cryptographic signatures.
3. **Holdout Split Isolation:** Test cases from Milestone 6 frozen evaluation suites designated as `HOLDOUT` are strictly prohibited from being included in training or validation partitions.

---

## 2. External Processing Authorization

Exporting enterprise data to external third-party infrastructure (such as Google Colab Free) poses external boundary traversal risks. M10 introduces a formal approval checkpoint:

```
+-----------------------------------------------------------+
| Gate 1 Approved Masked Dataset (PII Replaced with Tokens) |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| Human External Processing Authorization                   |
| - Specific Workspace Operator Sign-off                    |
| - Time-Bounded Validity Window (12h, 24h, 48h, 72h)       |
| - Destination: GOOGLE_COLAB_EPHEMERAL_RUNTIME             |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| Authorized Export to Colab Free Ephemeral Environment      |
+-----------------------------------------------------------+
```

If an operator attempts to configure a Colab build run using a dataset without an active `ExternalProcessingAuthorization`, the platform blocks creation with HTTP 422 Unprocessable Entity.

---

## 3. Curated Open Weights Catalog & Model Licensing

Milestone 10 maintains a curated registry of approved open models with explicit legal licensing metadata:

| Model Key | Parameters | License | License Status | Commercial Use Allowed | Gated Token Required |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mizan-test/tiny-llama-35m` | 35M | Apache-2.0 | `APPROVED` | Yes | No |
| `HuggingFaceTB/SmolLM2-135M` | 135M | Apache-2.0 | `APPROVED` | Yes | No |
| `Qwen/Qwen2.5-0.5B` | 490M | Apache-2.0 | `APPROVED` | Yes | No |
| `meta-llama/Llama-3.2-1B` | 1,238M | Llama 3.2 Community | `COMMERCIAL_USE_ALLOWED` | Yes ($\le 700\text{M}$ MAU) | Yes (Accept Terms) |

### Model Revision Immutability:
To ensure cryptographic reproducibility, Mizan resolves symbolic branch names (e.g. `main` or `v1.0`) to their **40-character immutable Git commit SHAs**. Build manifests bind strictly to this immutable commit digest, preventing upstream silent weight updates from corrupting downstream evaluation validity.
