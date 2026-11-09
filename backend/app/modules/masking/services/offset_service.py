"""Unicode Code-Point Offset Calculation, Overlap Grouping, and Interval Merging Service."""

from __future__ import annotations

import uuid
from typing import Any


class OffsetValidationError(ValueError):
    """Raised when an offset range is invalid."""


def validate_offsets(start: int, end: int, text_length: int) -> None:
    """Validate character-level Unicode code-point offsets against text length.

    Boundary constraint: 0 <= start < end <= text_length
    """
    if start < 0:
        raise OffsetValidationError(f"Start offset {start} cannot be negative.")
    if end <= start:
        raise OffsetValidationError(
            f"End offset {end} must be strictly greater than start offset {start}."
        )
    if end > text_length:
        raise OffsetValidationError(f"End offset {end} exceeds text length {text_length}.")


def spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Check if two half-open intervals [a_start, a_end) and [b_start, b_end) overlap."""
    return max(a_start, b_start) < min(a_end, b_end)


def group_overlapping_spans(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign overlap_group_id to transitively overlapping spans.

    Returns the mutated/updated list of findings with overlap_group_id populated.
    """
    if not findings:
        return []

    # Sort indices by start offset
    indexed = list(enumerate(findings))
    indexed.sort(key=lambda item: (item[1]["start_offset"], item[1]["end_offset"]))

    n = len(indexed)
    parent = list(range(n))

    def find(i: int) -> int:
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    # Check pairwise overlap
    for i in range(n):
        orig_i, f_i = indexed[i]
        for j in range(i + 1, n):
            orig_j, f_j = indexed[j]
            # If j starts after i ends, no later item can overlap i because they are sorted by start
            if f_j["start_offset"] >= f_i["end_offset"]:
                break
            if spans_overlap(
                f_i["start_offset"],
                f_i["end_offset"],
                f_j["start_offset"],
                f_j["end_offset"],
            ):
                union(i, j)

    # Group by connected component
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(indexed[i][0])

    # Assign overlap_group_id only if group size > 1
    for root, member_indices in groups.items():
        if len(member_indices) > 1:
            group_id = str(uuid.uuid4())
            for idx in member_indices:
                findings[idx]["overlap_group_id"] = group_id
        else:
            findings[member_indices[0]]["overlap_group_id"] = None

    return findings


def merge_overlapping_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or contiguous [start, end) intervals into a minimal disjoint set."""
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: list[tuple[int, int]] = [sorted_intervals[0]]

    for current in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = current
        if curr_start <= prev_end:
            # Overlapping or touching: merge
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append(current)

    return merged


def sort_spans_descending(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort span dictionaries in descending order of start_offset.

    If start offsets are equal, sort descending by end_offset.
    This guarantees that text transformations applied from end to beginning
    never perturb earlier offsets.
    """
    return sorted(
        spans,
        key=lambda s: (s["start_offset"], s["end_offset"]),
        reverse=True,
    )
