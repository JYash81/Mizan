"""Script to generate MIZAN_USER_MANUAL.docx using python-docx."""

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

doc = docx.Document()

# Page Margins
sections = doc.sections
for section in sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

# Color Palette: Deep Slate & Electric Blue
PRIMARY_COLOR = RGBColor(15, 23, 42)    # #0f172a
ACCENT_COLOR = RGBColor(37, 99, 235)    # #2563eb
MUTED_COLOR = RGBColor(100, 116, 139)   # #64748b

def format_cell(cell, bg_color=None, bold=False, color=None, font_size=9.5):
    if bg_color:
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)
    for p in cell.paragraphs:
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(font_size)
            if bold:
                r.bold = True
            if color:
                r.font.color.rgb = color

# ==============================================================================
# TITLE & HEADER
# ==============================================================================
title_p = doc.add_paragraph()
title_p.paragraph_format.space_before = Pt(20)
title_p.paragraph_format.space_after = Pt(4)
run_title = title_p.add_run("MIZAN PLATFORM")
run_title.font.name = "Calibri"
run_title.font.size = Pt(28)
run_title.font.bold = True
run_title.font.color.rgb = PRIMARY_COLOR

sub_p = doc.add_paragraph()
sub_p.paragraph_format.space_after = Pt(16)
run_sub = sub_p.add_run("Enterprise AI Experimentation, Evaluation, Governance & Deployment Manual")
run_sub.font.name = "Calibri"
run_sub.font.size = Pt(13)
run_sub.font.color.rgb = ACCENT_COLOR

meta_p = doc.add_paragraph()
meta_p.paragraph_format.space_after = Pt(24)
run_meta = meta_p.add_run("Document Version: 1.0 (Production Release)  |  Hennt AI Solutions  |  Live Web & Cloud Deployment")
run_meta.font.name = "Calibri"
run_meta.font.size = Pt(9.5)
run_meta.font.color.rgb = MUTED_COLOR

doc.add_heading("1. Executive Overview: What Is Mizan?", level=1)
p1 = doc.add_paragraph(
    "Mizan (from the Arabic word for 'Balance / Scales') is an enterprise AI experimentation, evaluation, "
    "cost-optimization, governance, and deployment platform. Most organizations struggle with AI adoption because "
    "they jump directly from raw prompts to production without knowing whether the model is accurate, whether sensitive "
    "customer data is protected, how much cloud GPUs will cost, or who approved the model for release."
)
p1.paragraph_format.space_after = Pt(8)

p2 = doc.add_paragraph(
    "Mizan solves this by providing a unified, multi-tenant operating system that guides your AI projects through an "
    "audited 8-step governance lifecycle: Data Ingestion -> Gate 1 PII Masking -> RAG & Benchmarking -> Gate 2 Cost "
    "Approval -> Multi-Objective Pareto Optimization -> Model Fine-Tuning & Quantization -> Gate 3 Cryptographic Release -> "
    "Site Agent Offline Execution & Automated Rollback."
)
p2.paragraph_format.space_after = Pt(16)

# ==============================================================================
# ONBOARDING SECTION
# ==============================================================================
doc.add_heading("2. Getting Started: Account Creation & Onboarding", level=1)
doc.add_paragraph(
    "1. Register at your live domain (e.g. https://llmguru.hennt.in/register).\n"
    "2. Enter your Full Name, Work Email, and Password.\n"
    "3. Check your inbox for the automated verification email sent via Hostinger SMTP (llmguru@hennt.in).\n"
    "4. Click 'Verify My Email' to activate your account.\n"
    "5. When you first log in, the Onboarding Wizard prompts you to enter your Organization Name (e.g. 'Hennt AI Solutions') "
    "and initial Workspace name (e.g. 'Customer-Support')."
)

# ==============================================================================
# TAB-BY-TAB MASTER GUIDE
# ==============================================================================
doc.add_heading("3. Tab-by-Tab Feature Reference Guide", level=1)

tabs = [
    ("Tab 1: Overview (/)", "Executive Mission Control", 
     "Centralized real-time dashboard displaying system health, active evaluations, running experiments, and key platform metrics. Use it daily to check overall progress across teams."),
    ("Tab 2: Team Management (/team)", "User Roles & Permissions (RBAC)", 
     "Manage team members, invite data scientists, and assign enterprise roles (Owner, Admin, Member, Auditor). Track pending email invites and manage access controls."),
    ("Tab 3: Workspaces (/workspaces)", "Multi-Project Isolation", 
     "Strict tenant boundaries separating projects (e.g., Finance-Copilot, HR-Bot). All datasets, API keys, models, and evaluations are strictly isolated by workspace."),
    ("Tab 4: Datasets & Data Protection (/datasets)", "Data Ingestion & Gate 1 Privacy", 
     "Upload enterprise documents (.jsonl, .csv, .pdf). Runs Gate 1 PII Masking: detects emails, phone numbers, credit cards, SSNs, and UAE Emirates IDs. Choose redaction or tokenization before sharing data with LLMs."),
    ("Tab 5: Evaluation Centre (/evaluation)", "Standardized LLM Grading & Benchmarks", 
     "Automated grading system testing models against standardized Q&A benchmarks. Evaluates factual accuracy, hallucination rates, semantic similarity, and latency (ms)."),
    ("Tab 6: Experiments Arena (/experiments)", "Head-to-Head Battles & ELO Ratings", 
     "Pits multiple candidate models (e.g., Llama-3-8B vs Mistral-7B) against identical enterprise prompts. Calculates chess-style ELO ratings and statistical confidence intervals."),
    ("Tab 7: Hardware & Cost (/hardware)", "VRAM Profiling & Gate 2 Financial Sign-Off", 
     "Calculates exact VRAM required for model sizes (8B, 70B) across FP16 and INT4/GGUF quantizations. Estimates cloud run-rates across AWS/GCP and enforces Gate 2 budget approval."),
    ("Tab 8: Governance & Approvals (/approvals)", "The 3 Safety Gates & Audit Trail", 
     "Central clearinghouse enforcing Separation of Duties: Gate 1 (Privacy Officer), Gate 2 (Financial Lead), Gate 3 (Release Manager). Every action is cryptographically signed with Ed25519 keys."),
    ("Tab 9: Recommendations (/recommendations)", "Multi-Objective Pareto Frontier", 
     "Balances Quality, Latency, and Cost. Filters out dominated configurations and highlights Pareto-optimal choices on an interactive 2D/3D trade-off chart."),
    ("Tab 10: Model Building (/model-building)", "LoRA/QLoRA & 1-Click Colab Notebooks", 
     "Configures reproducible fine-tuning recipes (Rank, Alpha, Learning Rate). Generates turnkey Jupyter notebooks to train for free on Google Colab GPUs, then packages weights into GGUF."),
    ("Tab 11: Artifact Registry (/artifact-registry)", "Model Versioning & Cryptographic Integrity", 
     "Enterprise registry for trained model weights. Tracks versions (v1.0.0, v1.1.0) with SHA-256 checksums to guarantee weights have not been altered before deployment."),
    ("Tab 12: Model Zoo (/zoo/models)", "Curated Internal Model Catalog", 
     "Library of approved models tagged with Hardware Badges ('Runs on 8GB MacBook', 'Requires 16GB GPU', 'Cloud Cluster'). Inspect context limits and benchmark scores."),
    ("Tab 13: App Zoo (/zoo/apps)", "Ready-to-Deploy Enterprise Blueprints", 
     "Packaged turnkey applications bundling models, system prompts, guardrails, and RAG knowledge bases (e.g., Customer Support Bot, SQL Generator, Contract Analyzer)."),
    ("Tab 14: Customer Sites (/sites)", "Edge & Remote Installation Management", 
     "Infrastructure management for deploying models into client offices or private data centers. Generates single-use Site Enrollment tokens and monitors remote CPU/GPU health."),
    ("Tab 15: Customer Runtime (/runtime)", "Blue/Green Deployment & Golden Tests", 
     "Offline inference server featuring Blue/Green slots. Executes automated Golden Test suites before cutting over live production traffic to prevent silent performance regressions."),
    ("Tab 16: Operations Centre (/operations)", "Real-Time Telemetry & Auto-Rollback", 
     "Tracks P50/P95/P99 latency, error budget burn rates, and active incidents. Features an automated circuit-breaker that rolls back to a healthy slot if error thresholds are exceeded."),
    ("Tab 17: Settings & Security (/settings)", "Global Configuration & Disaster Recovery", 
     "Manage user profiles, local AI provider keys (Ollama, Gemini), cryptographic signing keys, and AES-256-GCM encrypted database backups.")
]

for title, subtitle, desc in tabs:
    h = doc.add_heading(title, level=2)
    p_sub = doc.add_paragraph()
    r = p_sub.add_run(f"Purpose: {subtitle}")
    r.bold = True
    r.font.color.rgb = ACCENT_COLOR
    p_desc = doc.add_paragraph(desc)
    p_desc.paragraph_format.space_after = Pt(12)

# ==============================================================================
# ENTERPRISE SCENARIO TABLE
# ==============================================================================
doc.add_heading("4. End-to-End Enterprise Scenario Walkthrough", level=1)
doc.add_paragraph("A step-by-step example showing how an enterprise moves from customer support transcripts to an offline, privacy-compliant fine-tuned model:")

table = doc.add_table(rows=1, cols=4)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr_cells = table.rows[0].cells
headers = ["Phase", "Business Action", "Platform Mechanism", "Tab Used"]
for i, h in enumerate(headers):
    hdr_cells[i].text = h
    format_cell(hdr_cells[i], bg_color="0F172A", bold=True, color=RGBColor(255, 255, 255), font_size=10)

scenario_data = [
    ("1. Ingestion", "Upload customer transcripts", "Upload .jsonl and validate schema checksum", "Datasets (/datasets)"),
    ("2. Privacy", "Protect customer PII", "Run Gate 1 anonymization on credit cards & emails", "Data Protection"),
    ("3. Benchmark", "Compare candidate models", "Run standardized Q&A exam against Llama-3 & Mistral", "Evaluation (/evaluation)"),
    ("4. Costing", "Forecast hardware costs", "Compute VRAM requirements & request Gate 2 approval", "Hardware & Cost (/hardware)"),
    ("5. Optimization", "Select best trade-off", "Use Pareto Matrix to balance accuracy with <500ms latency", "Recommendations"),
    ("6. Training", "Fine-tune on company terms", "Export LoRA Colab notebook and train adapter weights", "Model Building (/model-building)"),
    ("7. Audit", "Formal release sign-off", "Release Manager verifies benchmarks and signs Gate 3", "Approvals (/approvals)"),
    ("8. Release", "Publish model to registry", "Version model (v1.0.0) with immutable SHA-256 hash", "Artifact Registry"),
    ("9. Deployment", "Deploy to client office", "Site Agent stages model into Green slot with Golden Tests", "Runtime (/runtime)"),
    ("10. Operations", "24/7 Production monitor", "Track SLOs & error budgets; automated rollback on failure", "Operations (/operations)")
]

for row_data in scenario_data:
    row_cells = table.add_row().cells
    for i, val in enumerate(row_data):
        row_cells[i].text = val
        format_cell(row_cells[i], font_size=9)

# ==============================================================================
# ROLES & RESPONSIBILITIES MATRIX
# ==============================================================================
doc.add_heading("5. Roles & Responsibilities Matrix", level=1)
doc.add_paragraph("Mizan strictly enforces Separation of Duties across departments:")

role_table = doc.add_table(rows=1, cols=3)
role_table.alignment = WD_TABLE_ALIGNMENT.CENTER
r_hdr = role_table.rows[0].cells
r_headers = ["User Role", "Key Responsibilities", "Primary Features Used"]
for i, h in enumerate(r_headers):
    r_hdr[i].text = h
    format_cell(r_hdr[i], bg_color="0F172A", bold=True, color=RGBColor(255, 255, 255), font_size=10)

roles_data = [
    ("Executive / Sponsor", "Authorizes budgets, monitors organizational progress and ROI", "Overview (/), Hardware & Cost (/hardware)"),
    ("AI Engineer / Data Scientist", "Prepares datasets, builds LoRA models, runs evaluation benchmarks", "Evaluation (/evaluation), Experiments, Model Building"),
    ("Privacy Officer / CISO", "Audits PII findings, configures masking, authorizes Gate 1 compliance", "Datasets (/datasets), Approvals (/approvals)"),
    ("Release Manager / Auditor", "Authorizes Gate 3 production releases, inspects immutable audit logs", "Approvals (/approvals), Artifact Registry (/artifact-registry)"),
    ("DevOps / Site SRE", "Deploys site agents, manages Blue/Green runtime slots, monitors SLOs", "Customer Sites (/sites), Runtime (/runtime), Operations (/operations)")
]

for row_data in roles_data:
    row_cells = role_table.add_row().cells
    for i, val in enumerate(row_data):
        row_cells[i].text = val
        format_cell(row_cells[i], font_size=9)

# Save Document
output_path = "E:\\WEB BACKUPS\\Llmstarter\\docs\\MIZAN_USER_MANUAL.docx"
doc.save(output_path)
print(f"Successfully generated Word document: {output_path}")
