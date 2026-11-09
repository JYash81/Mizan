"""Report Generation Service for Evaluation Runs (JSON, Markdown, CSV)."""

from __future__ import annotations

import csv
import io
import json

from sqlalchemy.orm import Session

from app.modules.evaluation.repositories.case_repository import CaseRepository
from app.modules.evaluation.repositories.run_repository import RunRepository
from app.modules.evaluation.repositories.suite_repository import SuiteRepository
from app.modules.evaluation.schemas.report import (
    EvaluationCaseReportItem,
    EvaluationReportSummary,
    FullEvaluationReport,
)


def interpret_score(score: float) -> str:
    """Return qualitative score band interpretation."""
    if score >= 90.0:
        return "EXCELLENT"
    elif score >= 80.0:
        return "STRONG"
    elif score >= 70.0:
        return "ACCEPTABLE"
    elif score >= 50.0:
        return "NEEDS_IMPROVEMENT"
    else:
        return "POOR"


class ReportService:
    def __init__(
        self,
        run_repo: RunRepository | None = None,
        case_repo: CaseRepository | None = None,
        suite_repo: SuiteRepository | None = None,
    ):
        self.run_repo = run_repo or RunRepository()
        self.case_repo = case_repo or CaseRepository()
        self.suite_repo = suite_repo or SuiteRepository()

    def generate_full_report(self, db: Session, workspace_id: str, run_id: str) -> FullEvaluationReport:
        run = self.run_repo.get_run(db, run_id, workspace_id)
        if not run:
            raise ValueError(f"EvaluationRun {run_id} not found.")

        suite = self.suite_repo.get_suite(db, workspace_id, run.suite_id)
        suite_name = suite.name if suite else "Unknown Suite"

        version = self.suite_repo.get_version(db, run.suite_version_id)
        version_num = version.version_number if version else 1
        digest = version.suite_digest if version else ""

        duration_ms = 0.0
        if run.started_at and run.completed_at:
            duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000

        breakdown = json.loads(run.score_breakdown_json) if run.score_breakdown_json else {}
        overall = run.overall_score or 0.0

        summary = EvaluationReportSummary(
            run_id=run.id,
            suite_id=run.suite_id,
            suite_name=suite_name,
            suite_version_number=version_num,
            suite_digest=digest,
            target_name=run.target_name,
            provider_name=run.provider_name,
            model_name=run.model_name,
            status=run.status.value,
            total_cases=run.total_cases,
            completed_cases=run.completed_cases,
            failed_cases=run.failed_cases,
            overall_score=overall,
            score_interpretation=interpret_score(overall),
            criterion_averages=breakdown,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=round(duration_ms, 2),
        )

        # Build Case Report Items
        case_results = self.run_repo.list_case_results(db, run.id)
        case_items: list[EvaluationCaseReportItem] = []

        for cr in case_results:
            case = self.case_repo.get_case(db, cr.case_id)
            if not case:
                continue

            metrics = self.run_repo.list_metric_results_for_case_result(db, cr.id)
            metric_scores = {m.metric_key: m.normalized_score for m in metrics}

            citations = json.loads(cr.citations_json) if cr.citations_json else []
            chunks = json.loads(cr.retrieved_chunks_json) if cr.retrieved_chunks_json else []

            item = EvaluationCaseReportItem(
                case_id=case.id,
                question=case.question,
                expected_answer=case.expected_answer,
                actual_answer=cr.actual_answer,
                is_unanswerable=case.is_unanswerable,
                category=case.category.value,
                difficulty=case.difficulty.value,
                overall_case_score=cr.overall_case_score,
                status=cr.status,
                metrics=metric_scores,
                citations_count=len(citations),
                retrieved_chunks_count=len(chunks),
                latency_ms=cr.latency_ms,
            )
            case_items.append(item)

        return FullEvaluationReport(
            summary=summary,
            cases=case_items,
            run_id=summary.run_id,
            suite_name=summary.suite_name,
            interpretation=summary.score_interpretation,
        )

    def export_markdown_report(self, report: FullEvaluationReport) -> str:
        s = report.summary
        md = [
            f"# Mizan AI Evaluation Report: {s.suite_name} (v{s.suite_version_number})",
            "",
            "## 1. Executive Summary",
            f"- **Evaluation Run ID:** `{s.run_id}`",
            f"- **Target System:** `{s.target_name}` ({s.provider_name} / {s.model_name})",
            f"- **Overall Score:** **{s.overall_score:.1f}%** ({s.score_interpretation})",
            f"- **Total Cases:** {s.total_cases} ({s.completed_cases} completed, {s.failed_cases} failed)",
            f"- **Execution Duration:** {s.duration_ms:.0f} ms",
            f"- **Suite Canonical Digest (SHA-256):** `{s.suite_digest}`",
            "",
            "## 2. Multi-Dimensional Criterion Averages",
            "| Evaluation Metric | Average Score (0-100) | Band |",
            "| :--- | :---: | :--- |",
        ]

        for crit, score in s.criterion_averages.items():
            md.append(f"| `{crit}` | **{score:.1f}%** | {interpret_score(score)} |")

        md.extend([
            "",
            "## 3. Examination Case Results",
            "| # | Category | Difficulty | Score | Question | Result |",
            "| :--- | :--- | :--- | :---: | :--- | :--- |",
        ])

        for idx, c in enumerate(report.cases, start=1):
            q_short = c.question[:60] + ("..." if len(c.question) > 60 else "")
            md.append(f"| {idx} | `{c.category}` | `{c.difficulty}` | {c.overall_case_score:.1f}% | {q_short} | `{c.status}` |")

        md.extend([
            "",
            "---",
            "### Disclaimer & Methodology",
            f"> {report.limitations_disclaimer}",
        ])
        return "\n".join(md)

    def export_csv_report(self, report: FullEvaluationReport) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "case_id",
            "category",
            "difficulty",
            "is_unanswerable",
            "overall_score",
            "status",
            "latency_ms",
            "question",
            "expected_answer",
            "actual_answer",
        ])

        for c in report.cases:
            writer.writerow([
                c.case_id,
                c.category,
                c.difficulty,
                c.is_unanswerable,
                c.overall_case_score,
                c.status,
                c.latency_ms,
                c.question,
                c.expected_answer,
                c.actual_answer or "",
            ])

        return output.getvalue()
