"""
Classifier module for CivicTriage (FR3).
Interfaces with local Ollama model (default llama3.2:3b), validates strict JSON,
implements retry-once logic, integrates keyword escalation (FR4), and applies
the 'Needs Review' fallback.
"""

import json
import os
import re
from typing import Any, Dict, Optional, Tuple
import requests
from dotenv import load_dotenv

from core.prompts import SYSTEM_PROMPT, build_triage_prompt
from core.rules import check_keyword_escalation

load_dotenv()

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

ALLOWED_EMOTIONS = {"Angry", "Anxious", "Sad", "Neutral"}
ALLOWED_PRIORITIES = {"High", "Medium", "Low", "Immediate", "Soon", "Routine"}
ALLOWED_CATEGORIES = {"Water", "Roads", "Sanitation", "Electricity", "Other"}

EMOTION_MAP = {e.lower(): e for e in ALLOWED_EMOTIONS}
PRIORITY_MAP = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "immediate": "High",
    "soon": "Medium",
    "routine": "Low",
}
CATEGORY_MAP = {c.lower(): c for c in ALLOWED_CATEGORIES}


def normalize_and_validate_json(raw_text: str) -> Tuple[bool, Optional[Dict[str, str]], str]:
    """
    Parse and validate raw model output.
    Normalizes casing and whitespace.
    Returns:
        (is_valid, validated_dict, error_message)
    """
    cleaned = raw_text.strip()
    # Remove markdown code fences if model included them despite instructions
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except Exception as e:
        # Attempt to extract substring between first { and last }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start:end+1])
            except Exception:
                return False, None, f"JSON parsing failed: {str(e)}"
        else:
            return False, None, f"JSON parsing failed: {str(e)}"

    if not isinstance(data, dict):
        return False, None, "Parsed JSON is not an object/dictionary"

    # Required keys check
    required_keys = ["emotion", "priority", "category", "english_summary", "reason"]
    for key in required_keys:
        if key not in data or not str(data[key]).strip():
            return False, None, f"Missing or empty required field: {key}"

    # Normalize casing
    raw_emotion = str(data["emotion"]).strip().lower()
    raw_priority = str(data["priority"]).strip().lower()
    raw_category = str(data["category"]).strip().lower()

    if raw_emotion not in EMOTION_MAP:
        return False, None, f"Invalid emotion: '{data['emotion']}'. Allowed: {ALLOWED_EMOTIONS}"
    if raw_priority not in PRIORITY_MAP:
        return False, None, f"Invalid priority: '{data['priority']}'. Allowed: {ALLOWED_PRIORITIES}"
    if raw_category not in CATEGORY_MAP:
        return False, None, f"Invalid category: '{data['category']}'. Allowed: {ALLOWED_CATEGORIES}"

    validated = {
        "emotion": EMOTION_MAP[raw_emotion],
        "priority": PRIORITY_MAP[raw_priority],
        "category": CATEGORY_MAP[raw_category],
        "english_summary": str(data["english_summary"]).strip(),
        "reason": str(data["reason"]).strip()
    }

    if len(validated["reason"]) < 5:
        return False, None, "Reason explanation is too short."

    return True, validated, ""


def call_ollama(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    model: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = 15
) -> str:
    """
    Invoke local Ollama generate API with JSON format mode.
    Target completion time: <15 seconds.
    """
    endpoint = f"{(url or DEFAULT_OLLAMA_URL).rstrip('/')}/api/generate"
    payload = {
        "model": model or DEFAULT_OLLAMA_MODEL,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,  # Low temperature for deterministic classification
            "top_p": 0.9
        }
    }

    response = requests.post(endpoint, json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()
    return result.get("response", "")


def classify_grievance(
    text: str,
    detected_lang: str,
    model: Optional[str] = None,
    url: Optional[str] = None,
    keyword_config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify a civic grievance:
    1. Try Ollama inference with strict JSON.
    2. Retry ONCE if invalid or failed.
    3. If still invalid or Ollama unreachable, fallback to 'Needs Review'.
    4. Apply keyword escalation rule (Routine -> Soon -> Immediate, never lower).
    """
    prompt = build_triage_prompt(text, detected_lang)

    validated_result: Optional[Dict[str, str]] = None
    last_error = ""

    # Attempt 1
    try:
        raw_output = call_ollama(prompt, model=model, url=url, timeout=15)
        is_valid, res, err = normalize_and_validate_json(raw_output)
        if is_valid and res:
            validated_result = res
        else:
            last_error = err
    except Exception as e:
        last_error = f"Ollama connection error: {str(e)}"

    # Retry ONCE if attempt 1 failed
    if not validated_result:
        try:
            retry_prompt = (
                prompt
                + f"\n\nNOTE: Your previous output failed validation with error: '{last_error}'. "
                + "Please ensure you output valid JSON matching the exact schema."
            )
            raw_output = call_ollama(retry_prompt, model=model, url=url, timeout=15)
            is_valid, res, err = normalize_and_validate_json(raw_output)
            if is_valid and res:
                validated_result = res
            else:
                last_error = err
        except Exception as e:
            last_error = f"Ollama retry connection error: {str(e)}"

    # Check keyword escalation (FR4)
    if validated_result:
        escalated_pri, escalated_reason, _, _ = check_keyword_escalation(
            text=text,
            current_priority=validated_result["priority"],
            current_reason=validated_result["reason"],
            config_path=keyword_config_path
        )
        return {
            "emotion": validated_result["emotion"],
            "priority": escalated_pri,
            "category": validated_result["category"],
            "english_summary": validated_result["english_summary"],
            "reason": escalated_reason,
            "status": "In Progress"  # Successfully classified, ready for municipal action
        }
    else:
        # Fallback: Mark as 'Needs Review'. Must NEVER delete or hide grievance.
        fallback_pri, fallback_reason, _, _ = check_keyword_escalation(
            text=text,
            current_priority="Low",
            current_reason="Automated classification unavailable. Queued for manual officer review.",
            config_path=keyword_config_path
        )
        return {
            "emotion": "Neutral",
            "priority": fallback_pri,
            "category": "Other",
            "english_summary": text[:120] + ("..." if len(text) > 120 else ""),
            "reason": fallback_reason,
            "status": "Needs Review"
        }
