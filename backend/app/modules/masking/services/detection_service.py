"""PII Detection and Batch Masking Service for Mizan.

Coordinates document text loading, Presidio analysis with localized UAE recognizers,
finding extraction (without persisting raw PII to database), overlap grouping,
and masked dataset artifact creation in StorageBucket.MASKED_DATASETS.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import (
    DatasetVersion,
    Document,
    DocumentFileType,
    ExtractionStatus,
)
from app.models.masking import (
    ExtractionCoverage,
    FindingStatus,
    MaskingProfile,
    MaskingRun,
    MaskingRunStatus,
    MaskingStrategy,
    PiiFinding,
)
from app.modules.masking.recognizers.registry import get_analyzer_engine
from app.modules.masking.services.masking_service import mask_text
from app.modules.masking.services.offset_service import (
    group_overlapping_spans,
    validate_offsets,
)
from app.modules.storage.provider import StorageBucket, StorageProvider

logger = logging.getLogger(__name__)


def assess_extraction_coverage(
    documents: list[Document],
    excluded_doc_ids: set[str] | None = None,
) -> tuple[ExtractionCoverage, int, int]:
    """Assess extraction coverage across all documents in a dataset version.

    If any non-excluded document has failed extraction or is an image/scanned document,
    coverage is flagged as OCR_REQUIRED or EXTRACTION_FAILED.
    """
    excluded = excluded_doc_ids or set()
    total_docs = len(documents)
    failed_count = 0
    has_ocr_needed = False

    for doc in documents:
        if doc.id in excluded:
            continue

        if doc.file_type == DocumentFileType.IMAGE or (
            doc.file_type == DocumentFileType.PDF and doc.char_count == 0
        ):
            has_ocr_needed = True
            failed_count += 1
        elif doc.extraction_status == ExtractionStatus.FAILED:
            failed_count += 1

    if has_ocr_needed:
        return ExtractionCoverage.OCR_REQUIRED, total_docs, failed_count
    if failed_count > 0:
        return ExtractionCoverage.EXTRACTION_FAILED, total_docs, failed_count
    return ExtractionCoverage.EXTRACTION_COMPLETE, total_docs, 0


def detect_pii_in_text(
    text: str,
    language: str = "en",
    enabled_entities: list[str] | None = None,
    confidence_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Scan text using Presidio Analyzer Engine and return structured finding dicts.

    NOTE: No raw PII text is stored in the finding dictionary.
    """
    if not text:
        return []

    analyzer = get_analyzer_engine()
    results = analyzer.analyze(
        text=text,
        language=language,
        entities=enabled_entities if enabled_entities else None,
        score_threshold=confidence_threshold,
    )

    findings: list[dict[str, Any]] = []
    text_len = len(text)

    for res in results:
        # Validate offsets
        try:
            validate_offsets(res.start, res.end, text_len)
        except Exception:
            continue

        findings.append(
            {
                "entity_type": res.entity_type,
                "recognizer_name": res.recognition_metadata.get(
                    "recognizer_name", "PresidioAnalyzer"
                )
                if hasattr(res, "recognition_metadata") and res.recognition_metadata
                else "PresidioAnalyzer",
                "recognizer_version": "1.0",
                "detection_score": round(float(res.score), 4),
                "start_offset": res.start,
                "end_offset": res.end,
                "offset_unit": "unicode_codepoint",
                "page_number": None,
                "status": FindingStatus.DETECTED,
                "is_manual": False,
            }
        )

    # Group overlapping spans
    group_overlapping_spans(findings)
    return findings


def execute_masking_run(
    db: Session,
    masking_run_id: str,
    storage: StorageProvider,
) -> MaskingRun:
    """Execute complete detection and initial masking for a MaskingRun."""
    run = db.execute(select(MaskingRun).where(MaskingRun.id == masking_run_id)).scalar_one_or_none()
    if not run:
        raise ValueError(f"MaskingRun {masking_run_id} not found.")

    version = db.execute(
        select(DatasetVersion).where(DatasetVersion.id == run.dataset_version_id)
    ).scalar_one_or_none()
    if not version:
        raise ValueError(f"DatasetVersion {run.dataset_version_id} not found.")

    profile: MaskingProfile | None = None
    if run.masking_profile_id:
        profile = db.execute(
            select(MaskingProfile).where(MaskingProfile.id == run.masking_profile_id)
        ).scalar_one_or_none()

    # Load profile parameters
    lang = profile.language if profile else "en"
    threshold = profile.confidence_threshold if profile else 0.5
    strategy = (
        profile.replacement_strategy if profile else MaskingStrategy.REPLACE_WITH_ENTITY_LABEL
    )
    enabled_entities: list[str] | None = None
    if profile and profile.enabled_entities_json:
        try:
            enabled_entities = json.loads(profile.enabled_entities_json)
        except Exception:
            enabled_entities = None

    run.status = MaskingRunStatus.ANALYZING
    run.started_at = datetime.now(UTC)
    db.commit()

    documents = (
        db.execute(select(Document).where(Document.dataset_version_id == version.id))
        .scalars()
        .all()
    )

    coverage, total_docs, failed_docs = assess_extraction_coverage(list(documents))
    run.extraction_coverage = coverage
    run.documents_processed = 0
    run.documents_failed = failed_docs

    total_findings_count = 0
    masked_digests: list[str] = []

    try:
        run.status = MaskingRunStatus.MASKING
        db.commit()

        for doc in documents:
            doc_text = ""
            if doc.extracted_text_key:
                try:
                    data, _ = storage.get_object(StorageBucket.RAW_UPLOADS, doc.extracted_text_key)
                    doc_text = data.decode("utf-8", errors="replace")
                except Exception as exc:
                    logger.warning("Could not read document text for %s: %s", doc.id, exc)

            if not doc_text and doc.extracted_text_sample:
                doc_text = doc.extracted_text_sample

            # Run detection
            findings_data = detect_pii_in_text(
                text=doc_text,
                language=lang,
                enabled_entities=enabled_entities,
                confidence_threshold=threshold,
            )

            # Persist findings to database (ZERO raw text stored)
            persisted_findings: list[dict[str, Any]] = []
            for fd in findings_data:
                finding_model = PiiFinding(
                    masking_run_id=run.id,
                    document_id=doc.id,
                    entity_type=fd["entity_type"],
                    recognizer_name=fd["recognizer_name"],
                    recognizer_version=fd["recognizer_version"],
                    detection_score=fd["detection_score"],
                    start_offset=fd["start_offset"],
                    end_offset=fd["end_offset"],
                    offset_unit=fd["offset_unit"],
                    page_number=fd["page_number"],
                    overlap_group_id=fd.get("overlap_group_id"),
                    status=fd["status"],
                    is_manual=fd["is_manual"],
                )
                db.add(finding_model)
                persisted_findings.append(fd)
                total_findings_count += 1

            # Perform masking
            masked_text, _, doc_digest = mask_text(
                canonical_text=doc_text,
                findings=persisted_findings,
                decisions_by_finding_id=None,
                strategy=strategy,
            )

            # Store masked document artifact
            masked_key = f"runs/{run.id}/docs/{doc.id}.masked.txt"
            storage.put_object(
                bucket=StorageBucket.MASKED_DATASETS,
                key=masked_key,
                data=masked_text.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
            )
            masked_digests.append(doc_digest)
            run.documents_processed += 1

        # Calculate overall masked dataset package digest
        combined_digest = hashlib.sha256(
            "".join(sorted(masked_digests)).encode("utf-8")
        ).hexdigest()

        run.findings_count = total_findings_count
        run.unresolved_findings_count = total_findings_count
        run.masked_output_digest = combined_digest
        run.status = MaskingRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        return run

    except Exception as exc:
        db.rollback()
        run.status = MaskingRunStatus.FAILED
        run.error_message = str(exc)
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise
