"""UAE IBAN Presidio Recognizer with ISO 13616 MOD-97 algorithmic validation.

Specification:
- Exactly 23 characters.
- Starts with 'AE'.
- 2 check digits, 3-digit bank code, 16-digit account number.
- ISO 13616 MOD-97 check: rearranged string modulo 97 == 1.
"""

from __future__ import annotations

import re

from presidio_analyzer import Pattern, PatternRecognizer


def validate_iban_mod97(iban: str) -> bool:
    """Validate an IBAN string using the ISO 13616 MOD-97 algorithm."""
    clean = re.sub(r"[\s\-]", "", iban).upper()
    if len(clean) != 23 or not clean.startswith("AE"):
        return False
    if not clean[2:4].isdigit():
        return False

    # Rearrange: move first 4 characters to end
    rearranged = clean[4:] + clean[:4]

    # Convert letters to digits (A=10, ..., Z=35)
    numeric_str = ""
    for ch in rearranged:
        if ch.isdigit():
            numeric_str += ch
        elif "A" <= ch <= "Z":
            numeric_str += str(ord(ch) - ord("A") + 10)
        else:
            return False

    try:
        return int(numeric_str) % 97 == 1
    except ValueError:
        return False


class UaeIbanRecognizer(PatternRecognizer):
    """Recognizer for UAE International Bank Account Numbers (IBAN)."""

    PATTERNS = [
        Pattern(
            name="uae_iban_general",
            regex=r"\bAE\d{2}(?:[ -]?\d{4}){4}[ -]?\d{3}\b",
            score=0.9,
        ),
        Pattern(
            name="uae_iban_continuous",
            regex=r"\bAE\d{21}\b",
            score=0.85,
        ),
        Pattern(
            name="uae_iban_spaced_flexible",
            regex=r"\bAE\d{2}[ -]?\d{3}[ -]?\d{16}\b",
            score=0.85,
        ),
    ]

    CONTEXT = [
        "iban",
        "bank account",
        "account number",
        "wire transfer",
        "swift",
        "حساب مصرفي",
        "الآيبان",
        "رقم الحساب",
    ]

    def __init__(
        self,
        patterns: list[Pattern] | None = None,
        context: list[str] | None = None,
        supported_language: str = "en",
        supported_entity: str = "UAE_IBAN",
    ):
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name="UAEIbanRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate structure and MOD-97 checksum of UAE IBAN."""
        return validate_iban_mod97(pattern_text)
