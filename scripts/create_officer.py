"""
CLI script to manually provision Municipal Officer accounts.
Citizens cannot self-register as officers; this script is the only administrative path.
Usage:
    python scripts/create_officer.py --name "Officer Sharma" --email "officer@ward4.gov.in" --password "OfficerPass123"
    or run without arguments for interactive prompt.
"""

import argparse
import sys
import os

# Add parent directory to path so core imports work cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import init_db, get_user_by_email, insert_user
from core.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create a Municipal Officer account for CivicTriage.")
    parser.add_argument("--name", type=str, help="Full name of the officer")
    parser.add_argument("--email", type=str, help="Email address of the officer")
    parser.add_argument("--password", type=str, help="Password for the officer account")
    parser.add_argument("--db", type=str, default=None, help="Optional database path")

    args = parser.parse_args()

    name = args.name
    email = args.email
    password = args.password
    db_path = args.db

    # Interactive input if flags not passed
    if not name:
        name = input("Enter Officer Full Name: ").strip()
    if not email:
        email = input("Enter Officer Email: ").strip()
    if not password:
        import getpass
        password = getpass.getpass("Enter Officer Password: ").strip()

    if not name:
        print("Error: Name cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if not email or "@" not in email:
        print("Error: A valid email address is required.", file=sys.stderr)
        sys.exit(1)
    if not password or len(password) < 6:
        print("Error: Password must be at least 6 characters long.", file=sys.stderr)
        sys.exit(1)

    init_db(db_path=db_path)

    clean_email = email.strip().lower()
    existing = get_user_by_email(clean_email, db_path=db_path)
    if existing:
        print(f"Error: A user account with email '{clean_email}' already exists (role: {existing['role']}).", file=sys.stderr)
        sys.exit(1)

    pw_hash = hash_password(password)
    user_id = insert_user(
        name=name.strip(),
        email=clean_email,
        password_hash=pw_hash,
        role="officer",
        db_path=db_path
    )

    print(f"Success! Officer account created successfully.")
    print(f"  User ID : {user_id}")
    print(f"  Name    : {name}")
    print(f"  Email   : {clean_email}")
    print(f"  Role    : officer")


if __name__ == "__main__":
    main()
