"""UAE Telephone Presidio Recognizer with TDRA operator allocation and Google phonenumbers validation.

Specification:
- TDRA mobile prefixes: 050, 052, 054, 055, 056, 058.
- Landline area codes: 02, 04, 06, 07, 09.
- Formats: National (050 123 4567) or International (+971 50 123 4567, 00971 50 123 4567).
- Validation via Google phonenumbers library.
"""

from __future__ import annotations

import phonenumbers
from presidio_analyzer import Pattern, PatternRecognizer


class UaePhoneRecognizer(PatternRecognizer):
    """Recognizer for UAE mobile and landline telephone numbers."""

    PATTERNS = [
        Pattern(
            name="uae_phone_international",
            regex=r"(?:\+971|00971)[ -]?(?:[234679]|5[024568])[ -]?\d{3}[ -]?\d{4}\b",
            score=0.85,
        ),
        Pattern(
            name="uae_phone_national_mobile",
            regex=r"\b05[024568][ -]?\d{3}[ -]?\d{4}\b",
            score=0.8,
        ),
        Pattern(
            name="uae_phone_national_landline",
            regex=r"\b0[234679][ -]?\d{3}[ -]?\d{4}\b",
            score=0.75,
        ),
    ]

    CONTEXT = [
        "phone",
        "mobile",
        "telephone",
        "cell",
        "call",
        "contact",
        "tel",
        "fax",
        "هاتف",
        "متحرك",
        "اتصال",
        "جوال",
    ]

    def __init__(
        self,
        patterns: list[Pattern] | None = None,
        context: list[str] | None = None,
        supported_language: str = "en",
        supported_entity: str = "UAE_PHONE_NUMBER",
    ):
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name="UAEPhoneRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate candidate phone number with Google phonenumbers library for UAE."""
        try:
            parsed = phonenumbers.parse(pattern_text, "AE")
            if parsed.country_code != 971:
                return False
            return phonenumbers.is_valid_number(parsed)
        except Exception:
            return False
