"""
Seed script for CivicTriage.
1. Creates default demo users:
   - Citizen: citizen@example.com (Password: Citizen123)
   - Officer: officer@civictriage.gov.in (Password: Officer123)
2. Seeds grievances from data/labelled_grievances.csv.
3. Supports --perf 500 flag to benchmark queue loading latency (<3 seconds with 500+ records).
Usage:
    python scripts/seed_sample_data.py
    python scripts/seed_sample_data.py --perf 500
"""

import argparse
import csv
import os
import random
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import (
    init_db,
    get_user_by_email,
    insert_user,
    insert_grievance_received,
    update_grievance_classification,
    update_grievance_status_and_note,
    get_officer_queue
)
from core.auth import hash_password

DATA_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "labelled_grievances.csv")


def seed_demo_users(db_path=None):
    """Seed standard demo accounts."""
    init_db(db_path)

    # 1. Citizen
    cit_email = "citizen@example.com"
    citizen = get_user_by_email(cit_email, db_path)
    if not citizen:
        cit_id = insert_user(
            name="Ramesh Sharma (Citizen)",
            email=cit_email,
            password_hash=hash_password("Citizen123"),
            role="citizen",
            db_path=db_path
        )
        print(f"Created demo citizen: {cit_email} (ID: {cit_id})")
    else:
        cit_id = citizen["id"]
        print(f"Demo citizen already exists: {cit_email} (ID: {cit_id})")

    # 2. Officer
    off_email = "officer@civictriage.gov.in"
    officer = get_user_by_email(off_email, db_path)
    if not officer:
        off_id = insert_user(
            name="Officer Priya Deshmukh",
            email=off_email,
            password_hash=hash_password("Officer123"),
            role="officer",
            db_path=db_path
        )
        print(f"Created demo officer: {off_email} (ID: {off_id})")
    else:
        off_id = officer["id"]
        print(f"Demo officer already exists: {off_email} (ID: {off_id})")

    return cit_id, off_id


def seed_labelled_csv(cit_id, off_id, db_path=None):
    """Load the 60 labelled samples into the database."""
    if not os.path.exists(DATA_CSV_PATH):
        print(f"Error: {DATA_CSV_PATH} not found.")
        return 0

    count = 0
    with open(DATA_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            g_id = insert_grievance_received(
                user_id=cit_id,
                ward=row["ward"],
                original_text=row["text"],
                detected_language=row["language"],
                db_path=db_path
            )
            update_grievance_classification(
                grievance_id=g_id,
                emotion=row["gold_emotion"],
                priority=row["gold_priority"],
                category=row["gold_category"],
                english_summary=row["gold_summary"],
                reason=f"Gold standard labelled record. Triage priority: {row['gold_priority']}.",
                status="Received" if count % 3 == 0 else "In Progress" if count % 3 == 1 else "Resolved",
                db_path=db_path
            )
            if count % 3 != 0:
                update_grievance_status_and_note(
                    grievance_id=g_id,
                    officer_id=off_id,
                    new_status="In Progress" if count % 3 == 1 else "Resolved",
                    note="Standard inspection logged by ward officer.",
                    db_path=db_path
                )
            count += 1

    print(f"Successfully seeded {count} labelled grievances from CSV.")
    return count


def seed_synthetic_records(count, cit_id, db_path=None):
    """Generate synthetic records to benchmark queue performance."""
    categories = ["Water", "Roads", "Sanitation", "Electricity", "Other"]
    priorities = ["Immediate", "Soon", "Routine"]
    emotions = ["Angry", "Anxious", "Sad", "Neutral"]
    statuses = ["Received", "In Progress", "Resolved", "Needs Review"]
    wards = [f"Ward {i}" for i in range(1, 21)]

    print(f"Generating {count} synthetic records...")
    start_time = time.time()
    for i in range(count):
        cat = random.choice(categories)
        pri = random.choice(priorities)
        emo = random.choice(emotions)
        st = random.choice(statuses)
        w = random.choice(wards)

        g_id = insert_grievance_received(
            user_id=cit_id,
            ward=w,
            original_text=f"Synthetic grievance record #{i+1} concerning {cat} issues in {w}.",
            detected_language="en",
            db_path=db_path
        )
        update_grievance_classification(
            grievance_id=g_id,
            emotion=emo,
            priority=pri,
            category=cat,
            english_summary=f"Automated issue summary #{i+1}",
            reason=f"Automated priority rationale for synthetic record #{i+1}.",
            status=st,
            db_path=db_path
        )

    duration = time.time() - start_time
    print(f"Inserted {count} records in {duration:.2f} seconds.")


def benchmark_queue_latency(db_path=None):
    """Measure officer queue query response time."""
    start = time.time()
    queue = get_officer_queue(db_path=db_path)
    elapsed = time.time() - start
    print("\n--- Queue Performance Benchmark ---")
    print(f"Total records in queue : {len(queue)}")
    print(f"Query Execution Time   : {elapsed * 1000:.2f} ms ({elapsed:.4f} seconds)")
    if elapsed < 3.0:
        print("PERFORMANCE TARGET MET: Officer queue loaded in < 3.0 seconds!")
    else:
        print("PERFORMANCE WARNING: Officer queue exceeded 3.0s target.")


def main():
    parser = argparse.ArgumentParser(description="Seed demo data and run performance benchmarks.")
    parser.add_argument("--perf", type=int, default=0, help="Generate N synthetic records and benchmark latency")
    parser.add_argument("--db", type=str, default=None, help="Optional DB path")
    args = parser.parse_args()

    cit_id, off_id = seed_demo_users(args.db)
    seed_labelled_csv(cit_id, off_id, args.db)

    if args.perf > 0:
        seed_synthetic_records(args.perf, cit_id, args.db)

    benchmark_queue_latency(args.db)


if __name__ == "__main__":
    main()
