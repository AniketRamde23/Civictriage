"""
Tests for authentication, password hashing, role enforcement, and citizen data isolation.
"""

import os
import pytest
from core.db import init_db, insert_grievance_received, get_grievances_for_citizen, insert_user
from core.auth import hash_password, verify_password, register_citizen, authenticate_user

TEST_DB = "test_auth_suite.db"


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


def test_password_hashing():
    raw_password = "SuperSecretPassword123"
    hashed = hash_password(raw_password)

    # Hash should never be equal to raw password and start with bcrypt marker
    assert hashed != raw_password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_citizen_registration_and_auth():
    # Successful registration
    success, msg, user = register_citizen(
        name="Sunita Rao",
        email="sunita@example.com",
        password="ValidPassword123",
        db_path=TEST_DB
    )
    assert success is True
    assert user["role"] == "citizen"
    assert user["email"] == "sunita@example.com"

    # Reject duplicate email
    dup_success, dup_msg, _ = register_citizen(
        name="Sunita Rao Duplicate",
        email="sunita@example.com",
        password="AnotherPassword123",
        db_path=TEST_DB
    )
    assert dup_success is False
    assert "already exists" in dup_msg

    # Authenticate successfully
    auth_ok, _, auth_user = authenticate_user("sunita@example.com", "ValidPassword123", db_path=TEST_DB)
    assert auth_ok is True
    assert auth_user["id"] == user["id"]

    # Reject wrong password
    bad_auth, bad_msg, _ = authenticate_user("sunita@example.com", "WrongPassword", db_path=TEST_DB)
    assert bad_auth is False


def test_officer_role_and_citizen_isolation():
    # Create Officer manually (simulating scripts/create_officer.py)
    officer_id = insert_user(
        name="Officer Deshmukh",
        email="officer@ward1.gov.in",
        password_hash=hash_password("OfficerPass123"),
        role="officer",
        db_path=TEST_DB
    )
    assert officer_id > 0

    # Create two distinct citizens
    _, _, citizen_a = register_citizen("Citizen A", "a@example.com", "PassA123", db_path=TEST_DB)
    _, _, citizen_b = register_citizen("Citizen B", "b@example.com", "PassB123", db_path=TEST_DB)

    # Citizen A submits 2 grievances
    g1 = insert_grievance_received(citizen_a["id"], "Ward 1", "Pothole in front of gate", "en", db_path=TEST_DB)
    g2 = insert_grievance_received(citizen_a["id"], "Ward 1", "Drainage overflowing", "en", db_path=TEST_DB)

    # Citizen B submits 1 grievance
    g3 = insert_grievance_received(citizen_b["id"], "Ward 2", "Streetlight not working", "en", db_path=TEST_DB)

    # Enforce data isolation: Citizen A should ONLY see g1 and g2, never g3
    records_a = get_grievances_for_citizen(citizen_a["id"], db_path=TEST_DB)
    assert len(records_a) == 2
    ids_a = {r["id"] for r in records_a}
    assert ids_a == {g1, g2}
    assert g3 not in ids_a

    # Citizen B should ONLY see g3
    records_b = get_grievances_for_citizen(citizen_b["id"], db_path=TEST_DB)
    assert len(records_b) == 1
    assert records_b[0]["id"] == g3
