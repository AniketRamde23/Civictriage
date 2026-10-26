"""
End-to-end Demo Script for CivicTriage.
Demonstrates the entire lifecycle:
Submit Grievance -> Immediate Save ('Received') -> Background/Sync Classify -> Priority Escalation -> Officer Queue Ranking -> Status Update & Notes -> Insights Summary.

Usage:
    python scripts/demo_walkthrough.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import (
    init_db,
    insert_user,
    get_user_by_email,
    insert_grievance_received,
    get_grievances_for_citizen,
    get_officer_queue,
    update_grievance_status_and_note,
    get_status_notes_for_grievance,
    get_insights_data
)
from core.auth import hash_password
from core.lang import detect_language
from core.background import process_grievance_sync

DEMO_DB = "civictriage_demo.db"


def run_demo():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("=" * 70)
    print("      CIVICTRIAGE: END-TO-END DEMO WALKTHROUGH SCRIPT")
    print("=" * 70)

    # Clean previous demo DB if exists
    for ext in ["", "-wal", "-shm"]:
        p = f"{DEMO_DB}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    init_db(DEMO_DB)
    print("\n[STEP 1] Initializing SQLite database with parameterised schema and indexes...")

    # Provision users
    cit_id = insert_user("Ananya Rao", "ananya@example.com", hash_password("Citizen123"), "citizen", db_path=DEMO_DB)
    off_id = insert_user("Inspector Verma", "verma@civictriage.gov.in", hash_password("Officer123"), "officer", db_path=DEMO_DB)
    print(f"Created Citizen: Ananya Rao (ID: {cit_id})")
    print(f"Created Officer: Inspector Verma (ID: {off_id})")

    # STEP 2: Grievance Submission (FR1)
    sample_complaint = "మా వీధి చివర 11 కేవీ కరెంట్ వైర్ తెగి నీటి గుంటలో పడింది! తీవ్రమైన మంటలు వస్తున్నాయి, ప్రాణాపాయం ఉంది!"
    print("\n[STEP 2] Citizen submits raw complaint (Telugu text):")
    print(f"  Input: \"{sample_complaint}\"")

    lang_code, lang_name = detect_language(sample_complaint)
    print(f"  Detected Language: {lang_name} ({lang_code})")

    # Immediate Save with status 'Received'
    g_id = insert_grievance_received(
        user_id=cit_id,
        ward="Ward 5",
        original_text=sample_complaint,
        detected_language=lang_code,
        db_path=DEMO_DB
    )
    print(f"  [FR1 SUCCESS] Grievance #{g_id} saved IMMEDIATELY with Status: 'Received'")

    # Verify citizen isolation
    cit_records = get_grievances_for_citizen(cit_id, db_path=DEMO_DB)
    print(f"  Citizen view shows {len(cit_records)} record with status: {cit_records[0]['status']}")

    # STEP 3: Classification & Keyword Escalation (FR3 & FR4)
    print("\n[STEP 3] Triggering AI triage engine (LLM classification + keyword escalation)...")
    res = process_grievance_sync(g_id, sample_complaint, lang_name, db_path=DEMO_DB)
    print(f"  Category        : {res['category']}")
    print(f"  Emotion         : {res['emotion']}")
    print(f"  Priority Level  : {res['priority']}")
    print(f"  English Summary : {res['english_summary']}")
    print(f"  Triage Reason   : {res['reason']}")
    print(f"  Updated Status  : {res['status']}")

    # STEP 4: Officer Queue Ranking (FR5)
    print("\n[STEP 4] Officer inspects ranked priority queue:")
    queue = get_officer_queue(db_path=DEMO_DB)
    print(f"  Items in queue: {len(queue)}")
    top_item = queue[0]
    print(f"  Top Priority Item: #{top_item['id']} | [{top_item['priority']}] {top_item['ward']} | Category: {top_item['category']}")
    print(f"  Reason: {top_item['reason']}")

    # STEP 5: Officer updates status and adds note (FR6)
    print("\n[STEP 5] Officer dispatches emergency team and logs status note:")
    update_grievance_status_and_note(
        grievance_id=g_id,
        officer_id=off_id,
        new_status="In Progress",
        note="Emergency power line maintenance crew dispatched to Ward 5. Feeder switched off.",
        db_path=DEMO_DB
    )
    print("  Status updated to: 'In Progress'")

    # STEP 6: Citizen checks updated status
    print("\n[STEP 6] Citizen checks their grievance history:")
    updated_cit_view = get_grievances_for_citizen(cit_id, db_path=DEMO_DB)
    print(f"  Current Status     : {updated_cit_view[0]['status']}")
    print(f"  Latest Officer Note: \"{updated_cit_view[0]['latest_note']}\"")

    # STEP 7: Insights & Reporting (FR7)
    print("\n[STEP 7] Generating municipal insights & metrics:")
    insights = get_insights_data(db_path=DEMO_DB)
    print(f"  Total Grievances Recorded: {len(insights)}")
    print(f"  High-Priority Emergencies: {sum(1 for i in insights if i['priority'] == 'Immediate')}")
    print("\n" + "=" * 70)
    print("  DEMO WALKTHROUGH COMPLETED SUCCESSFULLY END-TO-END!")
    print("=" * 70)

    # Cleanup demo db
    for ext in ["", "-wal", "-shm"]:
        p = f"{DEMO_DB}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


if __name__ == "__main__":
    run_demo()
