"""
Tests for LLM response validation, retry-once logic, and Needs Review fallback.
Uses unittest.mock to mock Ollama network calls.
"""

from unittest.mock import patch
import pytest
from core.classifier import (
    normalize_and_validate_json,
    classify_grievance
)


def test_normalize_and_validate_json_success():
    raw = """
    {
        "emotion": "ANGRY",
        "priority": "immediate",
        "category": "electricity",
        "english_summary": "Live wire sparking near school.",
        "reason": "Exposed high voltage wire presents lethal danger to children."
    }
    """
    valid, res, err = normalize_and_validate_json(raw)
    assert valid is True
    assert res["emotion"] == "Angry"
    assert res["priority"] in ("High", "Immediate")
    assert res["category"] == "Electricity"
    assert res["english_summary"] == "Live wire sparking near school."
    assert "lethal danger" in res["reason"]


def test_normalize_and_validate_json_code_fences():
    raw = """```json
    {
        "emotion": "Sad",
        "priority": "Soon",
        "category": "Water",
        "english_summary": "No water for 3 days.",
        "reason": "Basic utility disrupted for multiple days."
    }
    ```"""
    valid, res, err = normalize_and_validate_json(raw)
    assert valid is True
    assert res["emotion"] == "Sad"
    assert res["priority"] in ("Medium", "Soon")


def test_normalize_and_validate_json_invalid_values():
    # Invalid priority
    raw = """
    {
        "emotion": "Angry",
        "priority": "Critical_Urgent",
        "category": "Water",
        "english_summary": "Summary",
        "reason": "Long reason here."
    }
    """
    valid, res, err = normalize_and_validate_json(raw)
    assert valid is False
    assert "Invalid priority" in err


def test_normalize_and_validate_json_missing_keys():
    raw = '{"emotion": "Neutral", "priority": "Routine"}'
    valid, res, err = normalize_and_validate_json(raw)
    assert valid is False
    assert "Missing or empty required field" in err


@patch("core.classifier.call_ollama")
def test_classify_retry_once_success(mock_ollama):
    # Attempt 1 returns invalid json; Attempt 2 returns valid json
    invalid_json = '{"emotion": "Angry", "broken_json": true'
    valid_json = """{
        "emotion": "Angry",
        "priority": "Medium",
        "category": "Sanitation",
        "english_summary": "Garbage pile in neighborhood.",
        "reason": "Waste accumulation causes hygiene hazards."
    }"""
    mock_ollama.side_effect = [invalid_json, valid_json]

    result = classify_grievance("Garbage has not been collected", detected_lang="en")

    assert mock_ollama.call_count == 2
    assert result["emotion"] == "Angry"
    assert result["priority"] in ("Medium", "Soon")
    assert result["category"] == "Sanitation"
    assert result["status"] == "In Progress"


@patch("core.classifier.call_ollama")
def test_classify_fallback_to_needs_review_when_ollama_fails_twice(mock_ollama):
    # Both attempts return malformed data
    mock_ollama.side_effect = ["Garbage text output 1", "Garbage text output 2"]

    result = classify_grievance("Unclassified street complaint", detected_lang="en")

    assert mock_ollama.call_count == 2
    assert result["status"] == "Needs Review"
    assert "manual" in result["reason"].lower() or "review" in result["reason"].lower()


@patch("core.classifier.call_ollama")
def test_classify_fallback_when_ollama_is_down(mock_ollama):
    # Ollama is offline (ConnectionError)
    import requests
    mock_ollama.side_effect = requests.exceptions.ConnectionError("Connection refused")

    result = classify_grievance("Power transformer is making noise", detected_lang="en")

    # Should gracefully return Needs Review without raising an uncaught exception
    assert result["status"] == "Needs Review"
    assert result["priority"] in ["High", "Medium", "Low", "Routine", "Soon", "Immediate"]

