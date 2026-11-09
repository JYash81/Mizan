# MIZAN PLATFORM — COMPLETE USER MANUAL & FEATURE REFERENCE GUIDE
**Version:** 1.0 (Production Release)  
**Classification:** Enterprise Operational Documentation  
**System Architecture:** Multi-Tenant AI Governance, Evaluation & Deployment Platform  

---

## 1. Executive Overview: What Is Mizan?

**Mizan** (from the Arabic word for *"Balance / Scales"*) is an enterprise AI experimentation, evaluation, cost-optimization, governance, and deployment platform. 

Most organizations struggle with AI adoption because they jump directly from raw prompts to production without knowing:
- *Is this model actually accurate for our company?*
- *Are we leaking private customer PII data to third-party APIs?*
- *How much will this cost in cloud GPU bills?*
- *Can this model run on our local office hardware offline?*
- *Who approved this model for customer release?*

Mizan solves this by providing a unified, multi-tenant operating system that guides your AI projects through an audited **Governance Pipeline**:

```
[1. Data & PII Masking (Gate 1)] 
               │
               ▼
[2. RAG & Benchmarking]
               │
               ▼
[3. Hardware & Cost (Gate 2)]
               │
               ▼
[4. Multi-Objective Pareto Selection]
               │
               ▼
[5. Model Fine-Tuning & Quantization]
               │
               ▼
[6. Cryptographic Release (Gate 3)]
               │
               ▼
[7. Site Agent Offline Execution]
               │
               ▼
[8. SLOs & Automated Rollback]
```

---

## 2. Getting Started: First-Time Setup & Onboarding

### Account Registration & Email Verification
1. Open your browser and navigate to the application URL (e.g. `https://llmguru.hennt.in/register`).
2. Enter your **Full Name**, **Work Email**, and choose a strong password (minimum 12 characters).
3. Check your email inbox. A verification email with a single-use token link is dispatched via Hostinger SMTP (`llmguru@hennt.in`).
4. Click **Verify My Email** to activate your account.

### The Onboarding Wizard
When you first log in, Mizan guides you through initial setup:
1. **Organization Name:** Enter your company name (e.g. `Hennt AI Solutions`).
2. **Organization Slug:** A unique URL identifier (e.g. `hennt-ai`).
3. **Initial Workspace:** Name your first project area (e.g. `Customer-Support`).
4. Click **Create Organization**. Your multi-tenant workspace is initialized and the full 17-tab sidebar opens.

---

## 3. Tab-by-Tab Master User Guide

---

### Tab 1: Overview (`/`)
*The Executive Mission Control*

- **What it is:** A centralized real-time dashboard displaying system health, active evaluations, running experiments, and key platform metrics.
- **What you can do here:**
  - View overall counts: Total Datasets, Active Workspaces, Released Models, and Operational Alerts.
  - Review recent activity audit trails (who logged in, who ran an experiment, who approved a release).
  - Quick-launch wizards for datasets, exams, and experiments.
- **When to use it:** Every morning or when checking high-level status across your teams.

---

### Tab 2: Team Management (`/team`)
*User Roles, Invitations & Access Control*

- **What it is:** Enterprise Role-Based Access Control (RBAC) to manage users and permissions within your organization.
- **What you can do here:**
  - **Invite Team Members:** Enter a colleague's email address and assign their role:
    - **Owner:** Full organizational control, billing, and membership management.
    - **Admin:** Can create workspaces, manage datasets, and configure runtime agents.
    - **Member:** Can build models, run experiments, and evaluate datasets.
    - **Auditor (Read-Only):** Can inspect audit logs, reviews, and compliance records without making changes.
  - **Pending Invitations:** View or revoke pending email invites.
  - **Member List:** View active members and modify permissions.
- **When to use it:** When hiring new data scientists, onboarding engineers, or auditing user access.

---

### Tab 3: Workspaces (`/workspaces`)
*Multi-Project Isolation*

- **What it is:** Strict tenant boundaries that separate projects within the same organization.
- **What you can do here:**
  - Create isolated workspaces (e.g., `Finance-Copilot`, `Healthcare-Chat`, `Internal-HR-Bot`).
  - Datasets, API keys, models, and evaluations created inside `Finance-Copilot` are completely invisible to `Internal-HR-Bot`.
  - Switch active workspaces with one click in the top-right header.
- **When to use it:** When starting a new AI project or separating sensitive departmental data.

---

### Tab 4: Datasets & Data Protection (`/datasets`)
*Dataset Upload, Ingestion & Gate 1 PII Masking*

- **What it is:** The ingestion engine and mandatory privacy boundary.
- **Features & Capabilities:**
  - **Datasets Overview:** Upload enterprise documents (`.jsonl`, `.csv`, `.txt`, `.pdf`).
  - **Pre-flight Schema Validation:** Automatically validates headers, detects malformed JSON lines, and computes file SHA-256 checksums.
  - **Gate 1: PII Masking & Sensitive Data Protection:**
    - Scans text for emails, phone numbers, credit cards, SSNs, and regional IDs (e.g. UAE Emirates IDs).
    - Choose masking mode: **Redaction** (`[REDACTED]`), **Tokenization** (`<EMAIL_1>`), or **Synthetic Replacement**.
    - Requires Gate 1 sign-off before raw data can be passed to external commercial LLMs.
- **When to use it:** Whenever you upload enterprise data, training corpora, or customer chat logs.

---

### Tab 5: Evaluation Centre (`/evaluation`)
*Standardized LLM Grading & Benchmarks*

- **What it is:** Automated grading system that tests models against standardized question-and-answer benchmarks.
- **What you can do here:**
  - **Design Evaluation Suites:** Create test suites with ground truth references.
  - **Rubric Criteria:** Grade models on multiple dimensions:
    - Factual Accuracy (Ground Truth Match)
    - Hallucination Rate
    - Semantic Similarity (Cosine distance)
    - Latency (Response time in milliseconds)
    - Token Efficiency
  - **Case-by-Case Breakdown:** Click any evaluation run to see exactly which questions a model passed and where it failed.
- **When to use it:** Before deploying any model to verify if it actually knows your company's product documentation.

---

### Tab 6: Experiments Arena (`/experiments`)
*Head-to-Head Model Battles & ELO Ratings*

- **What it is:** A competitive testing ground where two or more models compete on the exact same enterprise prompts.
- **What you can do here:**
  - **A/B Head-to-Head Trials:** Pit `Llama-3-8B` vs. `Mistral-7B` vs. `GPT-4o-mini`.
  - **LLM-as-a-Judge or Human Evaluation:** Score winning answers.
  - **ELO Leaderboard:** Computes dynamic chess-style ELO ratings for each model based on win/loss/tie ratios.
  - **Statistical Significance:** Calculates confidence intervals to prove whether Model A is genuinely better than Model B or if the result was random chance.
- **When to use it:** When deciding which open-source or commercial model is best for your specific use case.

---

### Tab 7: Hardware & Cost Estimator (`/hardware`)
*VRAM Profiling & Gate 2 Financial Sign-Off*

- **What it is:** Hardware profiling and budget forecasting engine.
- **What you can do here:**
  - **Host Inspection:** Detects your local CPU, RAM, and GPU capabilities.
  - **Model VRAM Calculator:** Input model parameter size (e.g., 8B, 14B, 70B) and quantization (FP16, INT8, INT4 / GGUF). The system tells you the exact VRAM needed:
    $$\text{VRAM (GB)} \approx \frac{\text{Parameters} \times \text{Bits per weight}}{8 \times 10^9} \times 1.25 \text{ (KV Cache overhead)}$$
  - **Cloud Run-Rate Estimator:** Enter expected Requests Per Second (RPS) &rarr; Calculates monthly cloud spend across AWS, Azure, GCP, and RunPod.
  - **Gate 2 Financial Approval:** Requires formal budget sign-off before training or cloud instances can be provisioned.
- **When to use it:** Before purchasing GPUs, training models, or subscribing to cloud infrastructure.

---

### Tab 8: Governance & Approvals (`/approvals`)
*The 3 Enterprise Safety Gates*

- **What it is:** The central compliance clearinghouse enforcing **Separation of Duties**.
- **The Three Gates:**
  1. **Gate 1 (Privacy):** Privacy Officer signs off that sensitive PII has been masked.
  2. **Gate 2 (Financial):** Department Head approves compute and hosting spend estimates.
  3. **Gate 3 (Model Release):** Independent Release Manager signs off that the model has passed evaluation benchmarks and is safe for production.
- **Cryptographic Audit Log:** Every approval is stamped with the user ID, timestamp, and purpose-separated Ed25519 signature.
- **When to use it:** Whenever a model or dataset is ready to move to the next stage of the lifecycle.

---

### Tab 9: Recommendations Engine (`/recommendations`)
*Multi-Objective Pareto Analysis*

- **What it is:** An optimization engine that finds the "sweet spot" between Quality, Latency, and Cost.
- **What you can do here:**
  - **Set Priority Weights:** E.g., *"We want 80% accuracy, but latency must be under 600ms and cost under $0.001 per query"*.
  - **Pareto Dominance Matrix:** Automatically filters out "dominated" models (models that are both slower and more expensive than an alternative).
  - **Interactive Trade-Off Scatter Chart:** Visualizes models on a 2D/3D frontier so you can select the exact balance your business requires.
- **When to use it:** When executive management asks: *"Which model gives us the highest quality for the lowest monthly spend?"*

---

### Tab 10: Model Building & Colab Lab (`/model-building`)
*Fine-Tuning, LoRA/QLoRA & Exportable Notebooks*

- **What it is:** Reproducible model training laboratory without expensive vendor lock-in.
- **What you can do here:**
  - **Recipe Configuration:** Configure LoRA (Low-Rank Adaptation) and QLoRA recipes:
    - Rank ($r$), Alpha ($\alpha$), Dropout, Learning Rate, Target Modules (`q_proj`, `v_proj`).
  - **Google Colab 1-Click Export:** Download a turnkey, pre-configured `.ipynb` Jupyter Notebook that runs training on Google Colab's free T4/A100 GPUs.
  - **Quantization Recipes:** Convert trained models to GGUF format (Q4_K_M, Q5_K_M, Q8_0) for fast CPU/Mac execution.
  - **Artifact Staging:** Upload completed adapter weights back to Mizan for benchmarking.
- **When to use it:** When generic foundation models aren't specialized enough and you need a custom model fine-tuned on your internal terminology.

---

### Tab 11: Artifact Registry (`/artifact-registry`)
*Model Versioning & Cryptographic Integrity*

- **What it is:** An enterprise registry for trained model weights and adapter checkpoints (similar to Docker Hub, but for AI models).
- **What you can do here:**
  - **Model Families & Versions:** Track versions cleanly (e.g., `hennt-support-bot:v1.0.0`, `v1.1.0`).
  - **Cryptographic Fingerprints:** Computes SHA-256 checksums of every model weight file to guarantee that weights have not been corrupted or tampered with.
  - **Gate 3 Verification:** Only models with verified Gate 3 signatures can be marked as `RELEASED` and downloaded by customer sites.
- **When to use it:** To manage production releases and retire obsolete models.

---

### Tab 12: Model Zoo (`/zoo/models`)
*The Internal Model Marketplace*

- **What it is:** A curated internal library of certified foundation models, quantized variants, and enterprise fine-tunes.
- **What you can do here:**
  - Browse models with **Hardware Badges**:
    - 🟢 *"Runs on 8GB MacBook / Laptop"*
    - 🟡 *"Requires 16GB VRAM GPU"*
    - 🔴 *"Requires Cloud GPU Cluster"*
  - Inspect model parameters, context window limits, licensing details, and evaluation benchmark scores.
- **When to use it:** When team members need to pick a pre-approved model for a new application.

---

### Tab 13: App Zoo (`/zoo/apps`)
*Ready-to-Deploy Enterprise Applications*

- **What it is:** Catalog of packaged AI application templates that bundle a model, system prompts, guardrails, and knowledge retrieval into a turnkey solution.
- **Examples of Apps in the Zoo:**
  - **Customer Support Agent:** Pre-configured with sentiment analysis and escalation triggers.
  - **SQL Query Generator:** Translates natural language questions into secure read-only SQL queries.
  - **Contract Document Analyzer:** Summarizes legal agreements and flags risk clauses.
- **When to use it:** To deploy ready-made AI applications to departments with zero coding required.

---

### Tab 14: Customer Sites (`/sites`)
*Edge & On-Premise Site Management*

- **What it is:** Infrastructure management for deploying models to external client offices, hospitals, or private data centers.
- **What you can do here:**
  - **Site Enrollment:** Generate secure, single-use Enrollment Tokens to connect a remote customer machine.
  - **Heartbeat & Telemetry Monitoring:** See which customer sites are online, their CPU/GPU utilization, and memory headroom.
  - **Remote Configuration:** Push model updates and policy configurations down to remote Site Agents.
- **When to use it:** When selling your AI solutions to enterprise clients who require on-premise installation behind their own corporate firewalls.

---

### Tab 15: Customer Runtime (`/runtime`)
*Blue/Green Slots & Golden Test Validation*

- **What it is:** The runtime execution engine that serves models with zero downtime.
- **Key Features:**
  - **Blue/Green Deployment Slots:**
    - **Blue Slot:** Active live model currently serving traffic.
    - **Green Slot:** Staging model undergoing validation.
  - **Automated Golden Test Runner:**
    - Before switching production traffic from Blue to Green, Mizan automatically runs a battery of critical *"Golden Tests"*.
    - If accuracy drops or latency spikes, the switch is rejected automatically.
  - **Traffic Flip:** Seamlessly cut over traffic once Golden Tests pass.
- **When to use it:** During model updates, patch releases, or version upgrades.

---

### Tab 16: Operations Centre (`/operations`)
*Real-Time Telemetry, SLOs & Automated Rollback*

- **What it is:** Production observability, Prometheus metrics, and automated disaster recovery.
- **Key Features:**
  - **SLO & Error Budget Tracking:** Monitor P50, P95, and P99 latency alongside error budget burn rates.
  - **Active Incident Management:** Tracks degraded performance, high error rates, or memory exhaustion.
  - **Automated Rollback Circuit-Breaker:**
    - If a newly deployed model experiences an error rate exceeding your SLO threshold (e.g., > 2% failures), the system triggers an **instant automated rollback** to the last known healthy model slot.
- **When to use it:** To monitor production health, manage on-call alerts, and prevent service outages.

---

### Tab 17: Settings & Security (`/settings`)
*Platform Configuration & Disaster Recovery*

- **What it is:** Global preferences, security keys, and encrypted backups.
- **What you can do here:**
  - Update user profile and change password.
  - Configure AI provider keys (Ollama, Gemini, Local models).
  - Manage AES-256-GCM encrypted database backups (`app.core.backup_manager`).
  - View cryptographic signing keys and session audit logs.
- **When to use it:** For administrative maintenance, password changes, and disaster recovery drills.

---

## 4. End-to-End Enterprise Scenario Walkthrough

| Phase | Action | How to Perform | Tab Used |
| :--- | :--- | :--- | :--- |
| **1. Ingest Data** | Upload customer service transcripts | Upload `.jsonl` or `.csv` files | **Datasets** (`/datasets`) |
| **2. Protect Privacy** | Mask credit cards, emails, and names | Run Gate 1 anonymization & approve findings | **Data Protection** |
| **3. Benchmark Baseline** | Test candidate models on company FAQs | Run evaluation suite against Llama-3 and Mistral | **Evaluation** (`/evaluation`) |
| **4. Cost Analysis** | Estimate VRAM & GPU costs | Calculate VRAM and submit Gate 2 budget request | **Hardware & Cost** (`/hardware`) |
| **5. Model Decision** | Find best quality vs. cost ratio | Review Pareto Matrix and select optimal config | **Recommendations** (`/recommendations`) |
| **6. Fine-Tuning** | Specialize model on company vocabulary | Export LoRA Colab notebook & run training | **Model Building** (`/model-building`) |
| **7. Gate 3 Approval** | Independent release audit | Release Manager verifies metrics and signs release | **Approvals** (`/approvals`) |
| **8. Publish Artifact** | Lock weights in registry | Version weights (`v1.0.0`) with SHA-256 digest | **Artifact Registry** (`/artifact-registry`) |
| **9. Deploy to Runtime** | Stage in customer office | Site Agent downloads model into Green slot and runs Golden Tests | **Customer Runtime** (`/runtime`) |
| **10. 24/7 Operations** | Production monitoring & safeguards | Track P95 latency & SLOs; auto-rollback on failure | **Operations Centre** (`/operations`) |

---

## 5. Roles & Responsibilities Matrix

| Role | Core Responsibilities | Primary Tabs |
| :--- | :--- | :--- |
| **Executive / Sponsor** | Approves budgets, reviews high-level ROI | Overview (`/`), Hardware & Cost (`/hardware`) |
| **Data Scientist / AI Engineer** | Builds models, fine-tunes LoRA, runs benchmarks | Evaluation (`/evaluation`), Experiments (`/experiments`), Model Building (`/model-building`) |
| **Privacy Officer / CISO** | Audits PII findings, approves masking | Datasets (`/datasets`), Approvals (`/approvals`) |
| **Release Manager** | Authorizes Gate 3 production deployment | Approvals (`/approvals`), Artifact Registry (`/artifact-registry`) |
| **DevOps / SRE** | Manages site agents, runtime slots, and SLO alerts | Customer Sites (`/sites`), Runtime (`/runtime`), Operations (`/operations`) |

---

## 6. Technical Specifications & Hosting Architecture

- **Frontend:** Single Page Application built with React 19, TypeScript 5.8, Tailwind CSS, Vite 6.
- **Backend API:** FastAPI ASGI application running under Python 3.12, Uvicorn, and SQLAlchemy.
- **Primary Database:** MariaDB / MySQL 8.0+ running with utf8mb4 encoding across 93 relational tables.
- **Email Delivery:** Hostinger SMTP over TLS/SSL (Port 465) with multipart HTML/plain-text templates.
- **Security Standards:** Argon2id password hashing, AES-256-GCM backup encryption, Ed25519 signing, Bearer and HttpOnly session authentication.
