# Mizan High-Level Design (HLD) Interpretation

**Source Document:** `docs/reference/mizan_hld.png` (Mizan — High-Level Design v2, 1 November 2026)  
**Authoritative Scope:** Comprehensive architecture, planes, workflow steps, security boundaries, and runtime flows.

---

## 1. System Overview and Core Identity

Mizan is an end-to-end AI experimentation, evaluation, model recommendation, model building, model distribution, and on-premises/edge customer runtime platform. It allows businesses to evaluate diverse AI approaches (prompting, simple/hybrid/reranked/agentic RAG, LoRA, fine-tuning) on their own approved business data, evaluate them against a customized benchmark ("exam"), select the winning configuration for their target hardware (CPU box, GPU server, Cloud VM, Edge device), package and sign the verified build, and distribute it through an enterprise Model and App Zoo for offline-capable, privacy-preserving execution.

---

## 2. High-Level Architectural Planes & Boundaries

The architecture is divided into three distinct logical and physical planes, augmented by gated external services and human-in-the-loop approval gates:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      PEOPLE / BUSINESS TEAM                             │
│       (AI Lead & Data Protection Officer: Describe, Approve, Pick)     │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ Goals, targets, approvals        │ Raw data uploads
                   ▼                                 ▼
┌──────────────────────────────────────┐     ┌───────────────────────────┐
│     CONTROL PLANE — FRONT DESK       │     │   DATA PLANE — WORKSHOP   │
│  - Web Console & FastAPI API         │     │  - Encrypted Secure Storage│
│  - Metadata Store (Job Specs,        │     │  - PII Masking Engine     │
│    Approvals, Zoo Listings, Audit)   │     │  - Exam Generator (Bench) │
│  - Never stores raw business data    │     │  - Experiment Orchestrator│
│  - Enforces Role-Based Approvals     │     │  - Hardware Benchmarking  │
│  - Runs in Sovereign Cloud           │     │  - Model Builder & Signer │
└──────────────────┬───────────────────┘     └─────────────┬─────────────┘
                   │ Signed catalog / manifests            │ Built packages
                   ▼                                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   MODEL AND APP ZOO (Shelf / Catalog)                  │
│   Signed, versioned packages, model cards, tested/estimated benchmarks │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Pull over mTLS / Docker / Helm
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   CUSTOMER RUNTIME — YOUR HARDWARE                     │
│  - Hardware: CPU Box, GPU Server, Cloud VM, Edge Device                │
│  - Site Agent (mTLS pull, signature verification, self-test, health)   │
│  - Blue/Green Slots (Golden test gate before switching traffic)        │
│  - Local Inference (llama.cpp / vLLM 4-8 bit), Local RAG, Guardrails   │
│  - Complete Data Sovereignty: Personal data never leaves customer site │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Plane-by-Plane Component Breakdown

### A. Control Plane — The Front Desk
* **Purpose:** Where business users configure objectives, review reports, execute approvals, and select models. It maintains the system paperwork and audit trail, but **never holds raw business data or model checkpoints**.
* **Deployment:** Sovereign cloud infrastructure (UAE region for MVP).
* **Core Components:**
  1. **Web Console (React / Vite / TypeScript):** Clean, accessible enterprise interface for requirements entry, upload initiation, masking review, approval gates, trial monitoring, and Zoo catalog navigation.
  2. **FastAPI Control Plane Backend:** Versioned REST APIs (`/api/v1/*`), session management, RBAC, pre-signed upload URL generation, and gate orchestration.
  3. **Metadata Store:** Relational database (SQLite in local development; Hostinger MySQL/MariaDB in staging/production) storing:
     - User accounts, organizations, workspaces, memberships, and sessions.
     - Job specifications, experiment specifications, and trial definitions.
     - Role-based approval records with human approver identity, reasoning, and immutable timestamps.
     - Artifact references, checksums, and Ed25519 digital signature records.
     - Model and App Zoo listings, version histories, and compatibility matrices.
     - Tamper-evident, privacy-safe audit trail.

### B. Data Plane — The Workshop
* **Purpose:** Where sensitive data is ingested, masked, tested, evaluated, and compiled into production-ready packages.
* **Guarantees:**
  - Raw business data never leaves this plane.
  - Outside services receive only approved, masked text.
  - Every step is logged to the immutable audit trail.
* **Core Components:**
  1. **Secure Data Store:** Encrypted object storage containing partitioned buckets for:
     - Raw business uploads (strictly isolated, accessible only by the masking service).
     - Masked business datasets (approved for internal and permitted external testing).
     - Generated evaluation benchmarks ("exams").
     - Model checkpoints, quantization intermediates, and release artifacts.
  2. **Agent / Orchestrator:**
     - Deterministic state machine governing steps 3 through 9.
     - Orchestrates 3–9 experimental trials per experiment run.
     - Automatically retries recoverable transient failures with backoff.
     - Explains every planning and recommendation decision.
     - Strictly enforces hard spending caps and approval requirements.
  3. **Hardware Knowledge Base:**
     - Three structured tables:
       * Hardware capabilities and limits (CPU architectures, GPU models, RAM, VRAM).
       * Runtime memory fit and quantization compatibility rules.
       * Measured speed, first-token latency, throughput, and accuracy scores.
     - Continuously updated whenever tests or deployments yield empirical measurements.
  4. **Budget Guard & Audit Ledger:**
     - Enforces hard financial caps on external API spend and GPU hours.
     - Prevents automated budget elevation without explicit Gate 2 human approval.
     - Records every trial expenditure in a cryptographic/tamper-resistant spend ledger.

### C. External Services (Gated & Masked Only)
* **Teacher AI (Optional):** Large frontier model (e.g. Gemini, OpenAI, Claude, or self-hosted sovereign model) used exclusively to generate synthetic questions, edge cases, and exam rubrics from *masked* business text.
* **Open-Model Hub:** Curated open-source model repository (Hugging Face) providing open foundation weights (e.g. Qwen, Jais, Fanar, Llama) with explicit license validation prior to experimental ingestion.
* **Rented GPU Providers:** Pay-as-you-go GPU compute (e.g. RunPod, Kaggle, Lambda) utilized exclusively for heavy model fine-tuning and benchmark execution. Operates only on approved, masked datasets under Gate 2 budget ceilings.

---

## 4. End-to-End Workflow Steps (1 through 13)

### Step 1: Describe the Need (Control Plane)
* Business lead specifies requirements in the Web Console:
  - Task objectives and domain context.
  - Accuracy, speed, and latency targets.
  - Language requirements (e.g., Arabic, English, or bilingual).
  - Target deployment hardware (or requests the agent to recommend optimal hardware).
  - Maximum project budget ceiling.
* Serialized as an immutable `JobSpec` in the Metadata Store.

### Step 2: Get a Secure Upload Link (Control Plane & Data Plane)
* Control plane generates a scoped, short-lived, pre-signed upload URL.
* Business data, documents, and reference logs are uploaded directly to the Data Plane's Secure Data Store.
* Control plane never inspects, proxies, or retains raw document contents.

### Step 3: Mask Personal Data (Data Plane & GATE 1)
* Automated PII engine scans incoming documents:
  - Detects personal names, Emirates IDs, telephone numbers, emails, addresses, IBANs, and financial identifiers.
  - Utilizes Microsoft Presidio with localized UAE and enterprise regex recognizers.
  - Computes detection confidence scores and generates character-level span offsets.
* Produces an isolated masked dataset candidate.
* **GATE 1 — A person approves the masked sample:**
  - Designated Data Protection Officer / AI Lead reviews sample extractions and masking quality in the Web Console.
  - Approval is cryptographically bound to the exact dataset version ID and approver identity.
  - Experimentation cannot commence without Gate 1 approval.

### Step 4: Build the Exam (Data Plane)
* The agent constructs a rigorous, domain-specific evaluation suite ("the exam") from approved masked data:
  - Generates realistic test questions and query variations.
  - Extracts ground-truth reference answers and acceptable rubrics.
  - Generates retrieval relevance test sets, groundedness checks, and hallucination probes.
  - Incorporates domain-specific safety tests.
* Human spot-checks and validates the exam suite (e.g. via an Argilla-style review interface).

### Step 5: Shortlist What Fits (Data Plane)
* The agent consults the Hardware Knowledge Base:
  - Evaluates candidate models against the user's chosen hardware constraints (CPU, RAM, VRAM, context window).
  - Eliminates models that exceed hardware memory limits or lack required quantization formats.
  - Ranks remaining eligible candidates based on historical benchmark evidence.

### Step 6: Test Options, Cheapest First (Data Plane & GATE 2)
* The agent devises a cost-effective, progressive testing hierarchy:
  $$\text{Prompt Only} \longrightarrow \text{Simple RAG} \longrightarrow \text{Hybrid / Reranked RAG} \longrightarrow \text{Agentic RAG} \longrightarrow \text{LoRA Fine-Tuning} \longrightarrow \text{Full Fine-Tuning of Small Model} \longrightarrow \text{Fine-Tuning + RAG}$$
* Runs a quick mini-exam on all shortlisted options to eliminate poor performers cheaply.
* Selects the top 3 contenders for full benchmark evaluation.
* **GATE 2 — A person approves the spend:**
  - Before utilizing paid external resources or rented GPUs, the system generates an itemized cost estimate.
  - Business user reviews provider, resource allocation, and maximum spend ceiling.
  - Work halts until explicit human financial authorization is granted.

### Step 7: Recommend (Data Plane to Control Plane)
* The agent generates an explainable, multi-objective recommendation report:
  - Compares contenders across Arabic and English accuracy, first-token latency, tokens/sec, RAM/VRAM footprint, and cost per 1,000 queries.
  - Details the exact combination: base model, inference engine (llama.cpp vs. vLLM), quantization format (GGUF, AWQ, FP16), and retrieval strategy.
  - Explicitly documents why alternative candidates were rejected.
  - Transmits recommendation report to Control Plane for user review.

### Step 8: Build for Each Hardware Target (Data Plane)
* The build engine compiles and optimizes the winning configuration for each designated target:
  - **CPU Box:** Quantizes to 4-bit GGUF for execution via `llama.cpp`.
  - **GPU Server:** Quantizes to 4-bit AWQ / GPTQ for high-throughput serving via `vLLM`.
  - **Cloud VM / Edge:** Packages containerized runtimes with pinned dependencies.
* Executes a mandatory local "golden test" on the build container. Builds unverified on physical hardware are explicitly labeled `ESTIMATED`.

### Step 9: Publish to the Zoo (Data Plane & GATE 3)
* Final release packaging:
  - Generates Model Card, license manifest, dependency SBOM, and golden test suite.
  - Computes SHA-256 digests and signs the package using private Ed25519 digital keys.
* **GATE 3 — A person approves the release:**
  - Human reviewer inspects validation results, checksums, and benchmark scores.
  - Upon approval, the release is promoted to the enterprise Model and App Zoo.

### Step 10: Model and App Zoo & One-Command Installation
* The Model and App Zoo displays verified, versioned, signed entries (e.g. `Card-services triage v3`, `Policy Q&A app v1`).
* Each entry displays verified hardware badges (`CPU box: TESTED`, `Cloud VM: ESTIMATED`).
* Customer copies a single setup command:
  ```bash
  docker compose -f mizan-runtime.yml up -d
  # or: helm install mizan-app mizan/runtime-chart
  ```

### Step 11: Self-Test, Then Go Live (Customer Runtime)
* The runtime installer downloads the signed package via mTLS.
* Verifies Ed25519 signature, SHA-256 checksums, and hardware compatibility.
* Loads the application into a staging slot and executes the embedded "Golden Test" against the local machine.
* Traffic switches from the old slot to the new slot **only if** the golden test passes.
* Measured empirical speed and latency metrics are reported back to update Zoo estimates into verified numbers.

### Step 12: Customer Interaction Flow (Real-Time Runtime Operation)
Executed locally on customer premises in seconds:
```
[12a. Customer Request] (Arabic / English via Web, Mobile App, or Contact Center)
         │
         ▼
[12b. Front Door] (OpenAI-compatible API, Tenant Auth, Language Detect, Zero-PII Log)
         │
         ▼
[12c. Document Lookup] (Hybrid Keyword + Dense Vector Search + Reranker)
         │
         ▼
[12d. Local Model Inference] (Compressed local model on llama.cpp or vLLM, 4- to 8-bit)
         │
         ▼
[12e. Safety & Guardrail Check]
         ├── If Confident & Safe ──► [12f. Reply & Record] (Answer + Sources/Citations)
         │                                    │
         │                                    ▼
         │                             Returned to Customer via Same Channel
         │
         └── If Unsure or Sensitive ──► [Human Agent Takeover] (Staff handles with context)
```

### Step 13: Watch, Maintain & Automatic Rollback (Customer Runtime)
* Continuous local telemetry monitors response latency, token throughput, error spikes, and customer thumbs-up/down feedback.
* Updates from the Zoo are pulled by the Site Agent, verified, and self-tested in the inactive blue/green slot.
* In the event of performance degradation or runtime errors, the Site Agent automatically triggers a zero-downtime rollback to the previous known-good release.

---

## 5. The Three Mandatory Human Approval Gates

| Gate | Name | Gatekeeper | Timing | Non-Negotiable Rule |
| :--- | :--- | :--- | :--- | :--- |
| **GATE 1** | **Masked Data Approval** | Data Protection Officer / AI Lead | After PII masking, before any external processing or exam generation | No external model, teacher API, or training process may access datasets without an explicit, version-pinned human approval record. |
| **GATE 2** | **Spending Approval** | Project Owner / Finance Lead | After experiment planning, before renting GPUs or calling paid APIs | No paid cloud service or GPU instance may be spun up without prior human authorization of the itemized budget cap. |
| **GATE 3** | **Release Approval** | Enterprise Architect / Security Lead | After hardware build and golden test, before Zoo publication | No build package may be published to the catalog or installed by customer runtimes without human sign-off on signatures and test results. |

---

## 6. Plain-Words Architectural Summary

* **Control Plane (Front Desk):** The administrative office where teams describe what they need, review progress, click approvals, and pick finished applications. It holds paper records, never customer secrets.
* **Data Plane (The Workshop):** The secure laboratory where documents are cleaned of personal info, tested against multiple AI configurations, and built into compact software.
* **Customer Runtime:** The customer's private computers where finished AI applications answer real end users without sending private data over the internet.
* **Model and App Zoo:** The curated store shelf of sealed, tamper-proof AI applications with verified hardware speed stickers.
* **Golden Test:** A fixed, automated mini-exam that a new model must pass on the target computer before it is allowed to serve real traffic.
