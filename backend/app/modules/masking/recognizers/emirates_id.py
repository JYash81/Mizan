"""UAE Emirates ID Presidio Recognizer.

Specification:
- Exactly 15 digits.
- Starts with '784' (UAE ISO numeric code).
- Formatted as 784-XXXX-XXXXXXX-X, or space-separated, or unhyphenated.
"""

from __future__ import annotations

import re

from presidio_analyzer import Pattern, PatternRecognizer


class EmiratesIdRecognizer(PatternRecognizer):
    """Recognizer for UAE Emirates ID numbers."""

    PATTERNS = [
        Pattern(
            name="uae_emirates_id_formatted",
            regex=r"\b784-\d{4}-\d{7}-\d\b",
            score=0.85,
        ),
        Pattern(
            name="uae_emirates_id_spaced",
            regex=r"\b784\s\d{4}\s\d{7}\s\d\b",
            score=0.8,
        ),
        Pattern(
            name="uae_emirates_id_unformatted",
            regex=r"\b784\d{12}\b",
            score=0.75,
        ),
    ]

    CONTEXT = [
        "emirates id",
        "eid",
        "identity card",
        "national id",
        "resident id",
        "الهوية الإماراتية",
        "بطاقة الهوية",
        "رقم الهوية",
    ]

    def __init__(
        self,
        patterns: list[Pattern] | None = None,
        context: list[str] | None = None,
        supported_language: str = "en",
        supported_entity: str = "UAE_EMIRATES_ID",
    ):
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name="UAEEmiratesIdRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate structure of Emirates ID: exactly 15 digits starting with 784."""
        digits = re.sub(r"\D", "", pattern_text)
        if len(digits) != 15:
            return False
        if not digits.startswith("784"):
            return False
        return True
