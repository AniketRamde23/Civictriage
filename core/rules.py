"""
Keyword escalation rules for CivicTriage (FR4).
Loads keywords from config/keywords.json and escalates priority if critical keywords are matched.
Escalation rules:
- Routine -> Soon
- Soon -> Immediate
- Never lowers priority
- Annotates the reason string with the escalation detail.
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "keywords.json")

PRIORITY_LEVELS = ["Low", "Medium", "High", "Routine", "Soon", "Immediate"]


def load_keywords(config_path: Optional[str] = None) -> List[str]:
    """Load all escalation keywords across languages from JSON config."""
    path = config_path or CONFIG_PATH
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        keywords_dict: Dict[str, List[str]] = data.get("escalation_keywords", {})
        all_kw: List[str] = []
        for lang_kws in keywords_dict.values():
            all_kw.extend(lang_kws)
        # Deduplicate while preserving order
        return list(dict.fromkeys(k.strip().lower() for k in all_kw if k.strip()))
    except Exception:
        return []


def check_keyword_escalation(
    text: str,
    current_priority: Optional[str],
    current_reason: Optional[str],
    config_path: Optional[str] = None
) -> Tuple[str, str, bool, Optional[str]]:
    """
    Check if grievance text matches any escalation keywords.
    Promotes priority by exactly one level if matched:
      Low (or Routine) -> Medium
      Medium (or Soon) -> High
      High (or Immediate) -> High (recorded but priority already maximum)

    Returns:
        (new_priority, updated_reason, escalated_bool, matched_keyword)
    """
    norm_text = text.lower()
    keywords = load_keywords(config_path)

    matched_kw: Optional[str] = None
    for kw in keywords:
        pattern = re.escape(kw)
        if re.search(pattern, norm_text):
            matched_kw = kw
            break

    # Normalize incoming priority
    raw_pri = current_priority if current_priority in PRIORITY_LEVELS else "Low"
    if raw_pri in ("Routine", "Low"):
        priority = "Low"
    elif raw_pri in ("Soon", "Medium"):
        priority = "Medium"
    else:
        priority = "High"

    reason = current_reason.strip() if current_reason else "Evaluated by triage system."

    if not matched_kw:
        return priority, reason, False, None

    old_priority = priority
    escalated = False

    if old_priority == "Low":
        priority = "Medium"
        escalated = True
    elif old_priority == "Medium":
        priority = "High"
        escalated = True
    elif old_priority == "High":
        # Already at highest priority, record keyword hit
        escalated = False

    if escalated:
        note = f" [Priority escalated from {old_priority} to {priority} due to safety keyword: '{matched_kw}']"
        updated_reason = f"{reason}{note}".strip()
    else:
        updated_reason = reason

    return priority, updated_reason, escalated, matched_kw
