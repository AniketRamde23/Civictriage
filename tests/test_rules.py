"""
Tests for keyword priority escalation logic (FR4).
Tests that critical keywords raise priority by exactly one level and never lower it.
"""

import pytest
from core.rules import check_keyword_escalation


def test_keyword_escalation_english_routine_to_soon():
    # Low (or Routine) complaint with keyword 'fire' should escalate to Medium
    text = "Someone set fire to dry leaves in the corner of the park."
    new_pri, reason, escalated, kw = check_keyword_escalation(
        text=text,
        current_priority="Low",
        current_reason="Park waste burning."
    )
    assert escalated is True
    assert new_pri == "Medium"
    assert kw == "fire"
    assert "Priority escalated from Low to Medium" in reason


def test_keyword_escalation_english_soon_to_immediate():
    # Medium (or Soon) complaint with keyword 'live wire' should escalate to High
    text = "A live wire has snapped and fallen near our house."
    new_pri, reason, escalated, kw = check_keyword_escalation(
        text=text,
        current_priority="Medium",
        current_reason="Broken electrical cable."
    )
    assert escalated is True
    assert new_pri == "High"
    assert kw == "live wire"
    assert "Priority escalated from Medium to High" in reason


def test_keyword_escalation_immediate_remains_immediate():
    # High (or Immediate) complaint already at max priority stays High
    text = "Huge flooding in our basement."
    new_pri, reason, escalated, kw = check_keyword_escalation(
        text=text,
        current_priority="High",
        current_reason="Severe water ingress."
    )
    assert new_pri == "High"
    assert kw == "flooding"
    assert escalated is False  # Cannot escalate beyond High


def test_keyword_escalation_never_lowers_priority():
    # If text has no keywords and priority is already High, it must stay High
    text = "The road surface is slightly uneven outside the post office."
    new_pri, reason, escalated, kw = check_keyword_escalation(
        text=text,
        current_priority="High",
        current_reason="Emergency road assessment."
    )
    assert new_pri == "High"
    assert escalated is False
    assert kw is None


def test_keyword_escalation_hindi_keywords():
    # Hindi native script keyword: 'बिजली का नंगा तार'
    text = "गली में बिजली का नंगा तार लटक रहा है, बहुत बड़ा खतरा है।"
    new_pri, reason, escalated, kw = check_keyword_escalation(
        text=text,
        current_priority="Medium",
        current_reason="बिजली का तार टूटा है।"
    )
    assert escalated is True
    assert new_pri == "High"
    assert "बिजली का नंगा तार" in kw or "नंगा तार" in kw


def test_keyword_escalation_telugu_keywords():
    # Telugu native script keyword: 'మ్యాన్‌హోల్'
    text = "రహదారిపై తెరిచి ఉన్న మ్యాన్‌హోల్ మూత విరిగిపోయింది."
    new_pri, reason, escalated, kw = check_keyword_escalation(
        text=text,
        current_priority="Medium",
        current_reason="డ్రైనేజీ సమస్య."
    )
    assert escalated is True
    assert new_pri == "High"

