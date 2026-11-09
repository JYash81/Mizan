"""Unit tests for Presidio custom UAE Recognizers (Emirates ID, IBAN, Phone)."""

from __future__ import annotations

from app.modules.masking.recognizers.emirates_id import EmiratesIdRecognizer
from app.modules.masking.recognizers.registry import get_analyzer_engine
from app.modules.masking.recognizers.uae_iban import (
    UaeIbanRecognizer,
    validate_iban_mod97,
)
from app.modules.masking.recognizers.uae_phone import UaePhoneRecognizer


def test_emirates_id_recognizer_direct() -> None:
    rec = EmiratesIdRecognizer()

    # Valid formats
    assert rec.validate_result("784-1985-1234567-1") is True
    assert rec.validate_result("784 1985 1234567 1") is True
    assert rec.validate_result("784198512345671") is True

    # Invalid: wrong prefix
    assert rec.validate_result("785-1985-1234567-1") is False
    assert rec.validate_result("123-1985-1234567-1") is False

    # Invalid: wrong length
    assert rec.validate_result("784-1985-123456-1") is False
    assert rec.validate_result("784-1985-12345678-1") is False


def test_uae_iban_mod97_direct() -> None:
    rec = UaeIbanRecognizer()

    # Valid UAE IBANs (calculated with MOD-97)
    valid_iban_1 = "AE140330000000000000000"
    valid_iban_spaced = "AE14 0330 0000 0000 0000 000"
    assert validate_iban_mod97(valid_iban_1) is True
    assert validate_iban_mod97(valid_iban_spaced) is True
    assert rec.validate_result(valid_iban_1) is True
    assert rec.validate_result(valid_iban_spaced) is True

    # Invalid: check digits wrong
    assert validate_iban_mod97("AE070330000000000000000") is False
    assert rec.validate_result("AE070330000000000000000") is False

    # Invalid: wrong country code or length
    assert validate_iban_mod97("GB140330000000000000000") is False
    assert validate_iban_mod97("AE14033000000000000") is False


def test_uae_phone_recognizer_direct() -> None:
    rec = UaePhoneRecognizer()

    # Valid mobile
    assert rec.validate_result("+971 50 123 4567") is True
    assert rec.validate_result("00971 50 123 4567") is True
    assert rec.validate_result("0501234567") is True
    assert rec.validate_result("055 987 6543") is True
    assert rec.validate_result("+971561234567") is True

    # Valid landline
    assert rec.validate_result("+971 4 345 6789") is True
    assert rec.validate_result("04 345 6789") is True
    assert rec.validate_result("02 654 3210") is True

    # Invalid
    assert rec.validate_result("1234567") is False
    assert rec.validate_result("+1 800 555 0199") is False


def test_analyzer_engine_uae_integration() -> None:
    analyzer = get_analyzer_engine()

    text = (
        "Client details: John Doe, "
        "Emirates ID: 784-1985-1234567-1, "
        "IBAN: AE140330000000000000000, "
        "Mobile: +971 50 123 4567, "
        "Email: john.doe@mizan.ae"
    )

    results = analyzer.analyze(text=text, language="en")
    entities = {r.entity_type for r in results}

    assert "UAE_EMIRATES_ID" in entities
    assert "UAE_IBAN" in entities
    assert "UAE_PHONE_NUMBER" in entities
    assert "EMAIL_ADDRESS" in entities
