"""
Language detection module for CivicTriage.
Uses langdetect with unicode script range detection as robust fallback.
"""

import re
from typing import Tuple
from langdetect import DetectorFactory, detect, detect_langs

# Enforce deterministic results from langdetect
DetectorFactory.seed = 42

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu"
}


def detect_language(text: str) -> Tuple[str, str]:
    """
    Detect the language of the grievance text.
    Returns:
        (lang_code, lang_name) e.g., ("en", "English"), ("hi", "Hindi"), ("te", "Telugu")
    """
    cleaned = text.strip()
    if not cleaned:
        return "en", "English"

    # Unicode script checks for foolproof Hindi / Telugu identification
    # Telugu script Unicode range: \u0C00 - \u0C7F
    if re.search(r'[\u0C00-\u0C7F]', cleaned):
        return "te", "Telugu"

    # Devanagari script Unicode range: \u0900 - \u097F
    if re.search(r'[\u0900-\u097F]', cleaned):
        return "hi", "Hindi"

    try:
        detected = detect(cleaned)
        code = detected.lower()
        if code in LANGUAGE_NAMES:
            return code, LANGUAGE_NAMES[code]
        return code, code.upper()
    except Exception:
        return "en", "English"
