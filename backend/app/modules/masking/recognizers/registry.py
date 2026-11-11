"""Central Presidio Analyzer Registry with localized UAE recognizers."""

from __future__ import annotations

import logging
from functools import lru_cache

import spacy
from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_analyzer.predefined_recognizers.generic.email_recognizer import EmailRecognizer

from app.modules.masking.recognizers.emirates_id import EmiratesIdRecognizer
from app.modules.masking.recognizers.uae_iban import UaeIbanRecognizer
from app.modules.masking.recognizers.uae_phone import UaePhoneRecognizer

logger = logging.getLogger(__name__)


class MizanNlpEngine(SpacyNlpEngine):
    """Lightweight NLP engine that loads available models or falls back to blank pipelines

    without downloading hundreds of megabytes in local or resource-constrained environments.
    """

    def load(self) -> None:
        self.nlp = {}
        target_languages = ["en", "ar"]
        for lang in target_languages:
            model_name = f"{lang}_core_news_sm" if lang == "ar" else f"{lang}_core_web_sm"
            try:
                self.nlp[lang] = spacy.load(model_name)
                logger.info("Loaded spaCy model '%s' for language '%s'", model_name, lang)
            except Exception:
                try:
                    self.nlp[lang] = spacy.blank(lang)
                    logger.info("Loaded blank spaCy pipeline for language '%s'", lang)
                except Exception as exc:
                    logger.warning(
                        "Could not initialize blank spaCy pipeline for '%s': %s",
                        lang,
                        exc,
                    )


@lru_cache
def get_analyzer_engine() -> AnalyzerEngine:
    """Create and cache the singleton AnalyzerEngine with UAE recognizers registered."""
    nlp_engine = MizanNlpEngine()
    engine = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["en", "ar"],
    )

    # Register custom UAE recognizers for both English and Arabic, plus a syntax-only
    # email fallback. The default EmailRecognizer validates domains with a public suffix
    # list, which can reject reserved synthetic domains or newly introduced TLDs. The
    # pattern still requires a conventional complete email shape and never stores raw text.
    for lang in ["en", "ar"]:
        engine.registry.add_recognizer(EmiratesIdRecognizer(supported_language=lang))
        engine.registry.add_recognizer(UaeIbanRecognizer(supported_language=lang))
        engine.registry.add_recognizer(UaePhoneRecognizer(supported_language=lang))
        engine.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="EMAIL_ADDRESS",
                name="MizanEmailSyntaxRecognizer",
                patterns=EmailRecognizer.PATTERNS,
                context=EmailRecognizer.CONTEXT,
                supported_language=lang,
            )
        )

    return engine
