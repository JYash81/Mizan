"""Unit tests for Unicode Code-Point Offsets, Overlap Detection and Grouping."""

from __future__ import annotations

import pytest

from app.modules.masking.services.offset_service import (
    OffsetValidationError,
    group_overlapping_spans,
    merge_overlapping_intervals,
    sort_spans_descending,
    spans_overlap,
    validate_offsets,
)


def test_validate_offsets_boundary_conditions() -> None:
    text = "Hello, world!"
    length = len(text)

    # Valid bounds
    validate_offsets(0, 5, length)
    validate_offsets(7, length, length)

    # Negative start
    with pytest.raises(OffsetValidationError, match="negative"):
        validate_offsets(-1, 5, length)

    # End <= Start
    with pytest.raises(OffsetValidationError, match="strictly greater"):
        validate_offsets(5, 5, length)
    with pytest.raises(OffsetValidationError, match="strictly greater"):
        validate_offsets(6, 5, length)

    # End exceeds text length
    with pytest.raises(OffsetValidationError, match="exceeds text length"):
        validate_offsets(0, length + 1, length)


def test_spans_overlap() -> None:
    # Overlapping
    assert spans_overlap(0, 10, 5, 15) is True
    assert spans_overlap(5, 15, 0, 10) is True
    assert spans_overlap(2, 8, 3, 7) is True  # Subsumed

    # Touching but half-open [0, 5) and [5, 10) do not overlap
    assert spans_overlap(0, 5, 5, 10) is False
    assert spans_overlap(5, 10, 0, 5) is False

    # Disjoint
    assert spans_overlap(0, 5, 10, 15) is False


def test_group_overlapping_spans() -> None:
    # Disjoint spans
    disjoint = [
        {"start_offset": 0, "end_offset": 5},
        {"start_offset": 10, "end_offset": 15},
        {"start_offset": 20, "end_offset": 25},
    ]
    grouped_disjoint = group_overlapping_spans(disjoint)
    for f in grouped_disjoint:
        assert f.get("overlap_group_id") is None

    # Two overlapping spans
    overlapping = [
        {"start_offset": 10, "end_offset": 25},
        {"start_offset": 15, "end_offset": 30},
        {"start_offset": 50, "end_offset": 60},
    ]
    grouped = group_overlapping_spans(overlapping)
    assert grouped[0]["overlap_group_id"] is not None
    assert grouped[0]["overlap_group_id"] == grouped[1]["overlap_group_id"]
    assert grouped[2]["overlap_group_id"] is None

    # Transitive chain: A overlaps B, B overlaps C
    chain = [
        {"start_offset": 10, "end_offset": 20},
        {"start_offset": 18, "end_offset": 25},
        {"start_offset": 22, "end_offset": 35},
    ]
    grouped_chain = group_overlapping_spans(chain)
    group_id = grouped_chain[0]["overlap_group_id"]
    assert group_id is not None
    assert grouped_chain[1]["overlap_group_id"] == group_id
    assert grouped_chain[2]["overlap_group_id"] == group_id


def test_merge_overlapping_intervals() -> None:
    intervals = [(0, 5), (3, 8), (10, 12), (12, 15), (20, 25)]
    merged = merge_overlapping_intervals(intervals)
    assert merged == [(0, 8), (10, 15), (20, 25)]


def test_sort_spans_descending() -> None:
    spans = [
        {"start_offset": 10, "end_offset": 20},
        {"start_offset": 50, "end_offset": 60},
        {"start_offset": 25, "end_offset": 30},
    ]
    sorted_spans = sort_spans_descending(spans)
    starts = [s["start_offset"] for s in sorted_spans]
    assert starts == [50, 25, 10]


def test_unicode_code_point_preservation() -> None:
    # Text with emoji and Arabic text
    text = "مرحبا بكم 🇦🇪 في منصة ميزان 🚀 مع أطيب التحيات"
    length = len(text)

    # Substring with Arabic
    start_ar = text.index("ميزان")
    end_ar = start_ar + len("ميزان")
    validate_offsets(start_ar, end_ar, length)
    assert text[start_ar:end_ar] == "ميزان"

    # Substring with emoji
    start_rocket = text.index("🚀")
    end_rocket = start_rocket + 1
    validate_offsets(start_rocket, end_rocket, length)
    assert text[start_rocket:end_rocket] == "🚀"
