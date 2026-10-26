"""
Automated Integration Tests for the CivicTriage FastAPI Web Application.
Tests API route logic directly without external httpx dependency.
"""

import asyncio
import os
import pytest
from fastapi import Response

from app import (
    GrievanceSubmissionRequest,
    LoginRequest,
    RegisterRequest,
    UpdateStatusRequest,
    api_get_citizen_grievances,
    api_get_grievance_detail,
    api_get_insights,
    api_get_officer_queue,
    api_get_wards,
    api_login,
    api_register,
    api_submit_grievance,
    api_system_health,
    api_update_grievance_status,
    serve_index,
    verify_token,
)
from core.auth import hash_password
from core.db import init_db, insert_user

TEST_DB = "test_civictriage_api.db"


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    os.environ["DATABASE_PATH"] = TEST_DB
    for ext in ["", "-wal", "-shm"]:
        p = f"{TEST_DB}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    init_db(TEST_DB)
    # Seed citizen & officer
    insert_user("Citizen Test", "citizen_test@example.com", hash_password("Citizen123"), "citizen", db_path=TEST_DB)
    insert_user("Officer Test", "officer_test@civictriage.gov.in", hash_password("Officer123"), "officer", db_path=TEST_DB)

    yield

    for ext in ["", "-wal", "-shm"]:
        p = f"{TEST_DB}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


def test_serve_index():
    res = asyncio.run(serve_index())
    assert res.status_code == 200
    assert "CivicTriage" in res.body.decode("utf-8")


def test_system_health():
    res = asyncio.run(api_system_health())
    assert "ollama_online" in res
    assert "model" in res


def test_wards_endpoint():
    res = asyncio.run(api_get_wards())
    assert "wards" in res
    assert len(res["wards"]) >= 15


def test_auth_login_and_token():
    resp_obj = Response()
    req = LoginRequest(email="citizen_test@example.com", password="Citizen123")
    res = asyncio.run(api_login(req, resp_obj))

    assert res["success"] is True
    assert "token" in res
    assert res["user"]["role"] == "citizen"

    # Verify token payload
    payload = verify_token(res["token"])
    assert payload is not None
    assert payload["role"] == "citizen"


def test_citizen_submission_and_queue():
    citizen_user = {"id": 1, "name": "Citizen Test", "email": "citizen_test@example.com", "role": "citizen"}

    # Submit grievance
    sub_req = GrievanceSubmissionRequest(
        ward="Ward 7",
        text="Sparking live wire snapped right outside school."
    )
    sub_res = asyncio.run(api_submit_grievance(sub_req, user=citizen_user))
    assert sub_res["success"] is True
    assert sub_res["status"] == "Received"
    g_id = sub_res["grievance_id"]

    # Verify citizen isolation
    cit_list = asyncio.run(api_get_citizen_grievances(user=citizen_user))
    assert cit_list["success"] is True
    assert any(g["id"] == g_id for g in cit_list["grievances"])

    # Officer queue retrieval
    officer_user = {"id": 2, "name": "Officer Test", "email": "officer_test@civictriage.gov.in", "role": "officer"}
    q_res = asyncio.run(api_get_officer_queue(user=officer_user))
    assert q_res["success"] is True
    assert len(q_res["items"]) >= 1

    # Officer detail
    detail = asyncio.run(api_get_grievance_detail(g_id, user=officer_user))
    assert detail["success"] is True
    assert detail["grievance"]["id"] == g_id

    # Officer update status
    upd_req = UpdateStatusRequest(status="In Progress", note="Repair crew dispatched to Ward 7.")
    upd_res = asyncio.run(api_update_grievance_status(g_id, upd_req, user=officer_user))
    assert upd_res["success"] is True

    # Check updated detail & note
    detail2 = asyncio.run(api_get_grievance_detail(g_id, user=officer_user))
    assert detail2["grievance"]["status"] == "In Progress"
    assert len(detail2["notes"]) >= 1
    assert "Repair crew dispatched" in detail2["notes"][-1]["note"]


def test_insights():
    officer_user = {"id": 2, "name": "Officer Test", "email": "officer_test@civictriage.gov.in", "role": "officer"}
    ins = asyncio.run(api_get_insights(user=officer_user))
    assert ins["success"] is True
    assert "metrics" in ins
    assert "distributions" in ins
    assert ins["metrics"]["total"] >= 1
