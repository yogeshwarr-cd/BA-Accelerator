import pytest
from backend.ingestion.text_normalizer import TextNormalizer
from backend.ingestion.fingerprint import Fingerprint

def test_text_normalization_whitespace():
    """
    Tests that double spacing and excessive line break gaps are removed.
    """
    raw = "Requirement  A  \n\n\n\n  Detail content."
    cleaned = TextNormalizer.clean(raw)
    assert cleaned == "Requirement A\n\nDetail content."

def test_language_detection():
    """
    Verifies that the heuristic language detector identifies English content.
    """
    english_text = "The user shall be able to log in to the business system using an email address."
    lang = TextNormalizer.detect_language(english_text)
    assert lang == "en"

def test_fingerprint_generation():
    """
    Asserts that SHA256 returns consistent 64 character hex strings.
    """
    text = "Unified functional requirement body."
    hash1 = Fingerprint.calculate(text)
    hash2 = Fingerprint.calculate(text)
    assert hash1 == hash2
    assert len(hash1) == 64

# INTEGRATION NOTE
# Run test suite using: pytest backend/ingestion/tests/
