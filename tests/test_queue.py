"""
Tests for officer queue sorting order (Immediate > Soon > Routine, oldest first) and filters.
"""

import os
import time
import pytest
from core.db import (
    init_db,
    insert_user,
    insert_grievance_received,
    update_grievance_classification,
    get_officer_queue,
    update_grievance_status_and_note,
    get_status_notes_for_grievance
)
from core.auth import hash_password

TEST_DB = "test_queue_suite.db"


@pytest.fixture(autouse=True)
def setup_teardown_db():
    init_db(TEST_DB)
    yield
    for ext in ["", "-wal", "-shm"]:
        p = f"{TEST_DB}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


def test_queue_sorting_order():
    user_id = insert_user("Citizen Test", "cit@test.com", hash_password("pass123"), "citizen", db_path=TEST_DB)

    # Insert 4 grievances at different times with different priorities
    # g1: Routine (oldest)
    g1 = insert_grievance_received(user_id, "Ward 1", "Routine issue 1", "en", db_path=TEST_DB)
    update_grievance_classification(g1, "Neutral", "Routine", "Other", "Summary 1", "Reason 1", "Received", db_path=TEST_DB)

    # Small delay to ensure timestamp progression
    time.sleep(0.01)

    # g2: Immediate (younger than g1)
    g2 = insert_grievance_received(user_id, "Ward 2", "Immediate danger", "en", db_path=TEST_DB)
    update_grievance_classification(g2, "Angry", "Immediate", "Electricity", "Summary 2", "Reason 2", "Received", db_path=TEST_DB)

    time.sleep(0.01)

    # g3: Soon
    g3 = insert_grievance_received(user_id, "Ward 1", "Soon issue", "en", db_path=TEST_DB)
    update_grievance_classification(g3, "Sad", "Soon", "Water", "Summary 3", "Reason 3", "Received", db_path=TEST_DB)

    time.sleep(0.01)

    # g4: Immediate (younger than g2)
    g4 = insert_grievance_received(user_id, "Ward 3", "Another immediate danger", "en", db_path=TEST_DB)
    update_grievance_classification(g4, "Anxious", "Immediate", "Sanitation", "Summary 4", "Reason 4", "Received", db_path=TEST_DB)

    # Fetch sorted queue
    queue = get_officer_queue(db_path=TEST_DB)

    # Expected order:
    # 1st: g2 (Immediate, older)
    # 2nd: g4 (Immediate, younger)
    # 3rd: g3 (Soon)
    # 4th: g1 (Routine)
    ids_in_order = [row["id"] for row in queue]
    assert ids_in_order == [g2, g4, g3, g1]


def test_queue_filters_and_status_updates():
    officer_id = insert_user("Officer Kumar", "officer@test.com", hash_password("pass123"), "officer", db_path=TEST_DB)
    user_id = insert_user("Citizen Rao", "rao@test.com", hash_password("pass123"), "citizen", db_path=TEST_DB)

    g1 = insert_grievance_received(user_id, "Ward 4", "Water leak", "en", db_path=TEST_DB)
    update_grievance_classification(g1, "Neutral", "Soon", "Water", "Leak summary", "Reason water", "Received", db_path=TEST_DB)

    g2 = insert_grievance_received(user_id, "Ward 10", "Road crack", "en", db_path=TEST_DB)
    update_grievance_classification(g2, "Neutral", "Routine", "Roads", "Road summary", "Reason road", "Received", db_path=TEST_DB)

    # Filter by category Water
    water_queue = get_officer_queue(category_filter="Water", db_path=TEST_DB)
    assert len(water_queue) == 1
    assert water_queue[0]["id"] == g1

    # Filter by ward Ward 10
    ward_queue = get_officer_queue(ward_filter="Ward 10", db_path=TEST_DB)
    assert len(ward_queue) == 1
    assert ward_queue[0]["id"] == g2

    # Update status and add note
    update_grievance_status_and_note(
        grievance_id=g1,
        officer_id=officer_id,
        new_status="In Progress",
        note="Field team dispatched to inspect pipeline.",
        db_path=TEST_DB
    )

    notes = get_status_notes_for_grievance(g1, db_path=TEST_DB)
    assert len(notes) == 1
    assert notes[0]["note"] == "Field team dispatched to inspect pipeline."
    assert notes[0]["officer_name"] == "Officer Kumar"
