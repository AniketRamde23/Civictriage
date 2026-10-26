"""
CivicTriage: Multilingual Civic Grievance Triage Web Application.
Production-grade FastAPI server powering the modern web interface and RESTful APIs.
"""

import csv
import io
import os
import secrets
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, HTTPException, Header, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field
import requests

from core.auth import authenticate_user, register_citizen
from core.background import submit_async_classification
from core.db import (
    get_all_wards,
    get_connection,
    get_grievance_by_id,
    get_grievances_for_citizen,
    get_insights_data,
    get_officer_queue,
    get_status_notes_for_grievance,
    get_user_by_id,
    init_db,
    insert_grievance_received,
    update_grievance_status_and_note,
)
from core.lang import detect_language

load_dotenv()

# Initialize Database tables and indexes safely
try:
    init_db()
except Exception as e:
    import logging
    logging.getLogger("CivicTriage").warning(f"Initial DB init warning: {e}")

SECRET_KEY = os.getenv("SECRET_KEY", "civic-triage-super-secret-key-2026-btech-capstone")
serializer = URLSafeTimedSerializer(SECRET_KEY)
TOKEN_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 days

app = FastAPI(
    title="CivicTriage Web Platform",
    description="Multilingual Civic Grievance Triage & Urgency Ranking System",
    version="2.0.0",
)

# Enable CORS for flexible integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Ensure database tables and demo data are initialized on worker startup."""
    try:
        init_db()
    except Exception as e:
        import logging
        logging.getLogger("CivicTriage").warning(f"Startup DB init warning: {e}")


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str
    password: str = Field(..., min_length=6)


class GrievanceSubmissionRequest(BaseModel):
    ward: str
    text: str = Field(..., min_length=5)


class UpdateStatusRequest(BaseModel):
    status: str
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth Helper & Dependency
# ---------------------------------------------------------------------------
def generate_token(user_id: int, role: str) -> str:
    """Generate signed URL-safe bearer token."""
    return serializer.dumps({"user_id": user_id, "role": role})


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify signed token and return payload."""
    try:
        data = serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        return data
    except (BadSignature, SignatureExpired):
        return None


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
) -> Dict[str, Any]:
    """Dependency to retrieve the currently authenticated user from Bearer header or cookie."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
    elif session_token:
        token = session_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
        )

    payload = verify_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please sign in again.",
        )

    user = get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    # Return clean dict without sensitive password_hash
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": str(user["created_at"]),
    }


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/auth/login")
async def api_login(req: LoginRequest, response: Response):
    """Authenticate citizen or municipal officer."""
    success, msg, user = authenticate_user(req.email, req.password)
    if not success or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=msg or "Invalid email or password",
        )

    token = generate_token(user["id"], user["role"])
    # Set cookie as well for native browser requests
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=TOKEN_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/api/auth/register")
async def api_register(req: RegisterRequest):
    """Self-registration exclusively for citizens."""
    success, msg = register_citizen(req.name, req.email, req.password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    return {"success": True, "message": msg}


@app.post("/api/auth/logout")
async def api_logout(response: Response):
    """Clear session token cookie."""
    response.delete_cookie(key="session_token")
    return {"success": True, "message": "Signed out successfully."}


@app.get("/api/auth/me")
async def api_get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Return profile details of the active user."""
    return {"success": True, "user": user}


# ---------------------------------------------------------------------------
# System Health & Metadata Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/system/health")
async def api_system_health():
    """Non-blocking health check of Ollama engine."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    online = False
    try:
        r = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=1.2)
        online = r.status_code == 200
    except Exception:
        online = False

    return {
        "ollama_online": online,
        "model": model_name,
        "status": "online" if online else "offline",
    }


@app.get("/api/wards")
async def api_get_wards():
    """Retrieve available municipal ward options."""
    existing = get_all_wards()
    defaults = [f"Ward {i}" for i in range(1, 16)]
    # Merge and preserve order
    combined = list(dict.fromkeys(defaults + [w for w in existing if w]))
    return {"wards": combined}


# ---------------------------------------------------------------------------
# Citizen Grievance Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/grievances")
async def api_submit_grievance(
    req: GrievanceSubmissionRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Submit new civic grievance.
    1. Language detection (EN/HI/TE)
    2. Immediate persistence with status 'Received' (FR1)
    3. Asynchronous background classification worker
    """
    if user["role"] != "citizen":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only citizens can submit civic grievances.",
        )

    clean_text = req.text.strip()
    if len(clean_text) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grievance description must be at least 5 characters long.",
        )

    # Detect language
    lang_code, lang_name = detect_language(clean_text)

    # Persist immediately
    grievance_id = insert_grievance_received(
        user_id=user["id"],
        ward=req.ward.strip() or "Unspecified",
        original_text=clean_text,
        detected_language=lang_code,
    )

    # Queue background thread classification worker
    submit_async_classification(
        grievance_id=grievance_id,
        text=clean_text,
        detected_lang=lang_code,
    )

    return {
        "success": True,
        "grievance_id": grievance_id,
        "status": "Received",
        "detected_language": lang_name,
        "detected_code": lang_code,
        "message": "Grievance received and registered immediately. Automated triage is in progress.",
    }


@app.get("/api/citizen/grievances")
async def api_get_citizen_grievances(
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Enforce strict citizen data isolation: retrieve grievances for current user only."""
    if user["role"] != "citizen":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Citizen access required.",
        )
    records = get_grievances_for_citizen(user["id"])
    return {"success": True, "grievances": records}


# ---------------------------------------------------------------------------
# Officer Triage Queue Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/officer/queue")
async def api_get_officer_queue(
    priority: str = "All",
    category: str = "All",
    ward: str = "All",
    status_filter: str = "All",
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Retrieve ranked officer triage queue sorted strictly by urgency:
    Immediate > Soon > Routine, then age (oldest first).
    """
    if user["role"] not in ("officer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Municipal Officer or Administrator access required.",
        )

    # Safely extract default if called with FastAPI Query default object
    pri = getattr(priority, "default", priority)
    cat = getattr(category, "default", category)
    wrd = getattr(ward, "default", ward)
    stf = getattr(status_filter, "default", status_filter)

    records = get_officer_queue(
        priority_filter=pri,
        category_filter=cat,
        ward_filter=wrd,
        status_filter=stf,
    )

    total_count = len(records)
    high_count = sum(1 for r in records if r.get("priority") in ("High", "Immediate"))
    medium_count = sum(1 for r in records if r.get("priority") in ("Medium", "Soon"))
    low_count = sum(1 for r in records if r.get("priority") in ("Low", "Routine"))
    needs_review_count = sum(1 for r in records if r.get("status") == "Needs Review")

    return {
        "success": True,
        "metrics": {
            "total": total_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "immediate": high_count,
            "soon": medium_count,
            "routine": low_count,
            "needs_review": needs_review_count,
        },
        "items": records,
    }


@app.get("/api/officer/grievance/{grievance_id}")
async def api_get_grievance_detail(
    grievance_id: int,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve full details and status audit notes for a specific grievance."""
    if user["role"] != "officer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Municipal Officer access required.",
        )

    record = get_grievance_by_id(grievance_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grievance #{grievance_id} not found.",
        )

    notes = get_status_notes_for_grievance(grievance_id)
    return {
        "success": True,
        "grievance": record,
        "notes": notes,
    }


@app.post("/api/officer/grievance/{grievance_id}/status")
async def api_update_grievance_status(
    grievance_id: int,
    req: UpdateStatusRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Officer updates grievance status and adds a historical status note."""
    if user["role"] not in ("officer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Municipal Officer or Administrator access required.",
        )

    allowed_statuses = {"Received", "In Progress", "Needs Review", "Resolved"}
    if req.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(allowed_statuses)}",
        )

    record = get_grievance_by_id(grievance_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grievance #{grievance_id} not found.",
        )

    update_grievance_status_and_note(
        grievance_id=grievance_id,
        officer_id=user["id"],
        new_status=req.status,
        note=req.note,
    )

    return {
        "success": True,
        "message": f"Grievance #{grievance_id} status updated to '{req.status}'.",
    }


# ---------------------------------------------------------------------------
# Insights & Analytics Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/insights")
async def api_get_insights(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve computed analytics, distributions, and summary metrics."""
    data = get_insights_data()

    total_records = len(data)
    high_count = sum(1 for r in data if r.get("priority") in ("High", "Immediate"))
    medium_count = sum(1 for r in data if r.get("priority") in ("Medium", "Soon"))
    low_count = sum(1 for r in data if r.get("priority") in ("Low", "Routine"))
    resolved_count = sum(1 for r in data if r.get("status") == "Resolved")
    in_progress_count = sum(1 for r in data if r.get("status") == "In Progress")

    # Wards aggregation
    ward_counts: Dict[str, int] = {}
    cat_counts: Dict[str, int] = {}
    pri_counts: Dict[str, int] = {}
    lang_counts: Dict[str, int] = {}

    for r in data:
        w = r.get("ward") or "Unspecified"
        ward_counts[w] = ward_counts.get(w, 0) + 1

        c = r.get("category") or "Other"
        cat_counts[c] = cat_counts.get(c, 0) + 1

        raw_pri = r.get("priority") or "Unassigned"
        if raw_pri in ("High", "Immediate"):
            norm_pri = "High"
        elif raw_pri in ("Medium", "Soon"):
            norm_pri = "Medium"
        elif raw_pri in ("Low", "Routine"):
            norm_pri = "Low"
        else:
            norm_pri = raw_pri
        pri_counts[norm_pri] = pri_counts.get(norm_pri, 0) + 1

        l = r.get("detected_language") or "en"
        lang_counts[l] = lang_counts.get(l, 0) + 1

    return {
        "success": True,
        "metrics": {
            "total": total_records,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "immediate": high_count,
            "soon": medium_count,
            "routine": low_count,
            "resolved": resolved_count,
            "in_progress": in_progress_count,
            "active_wards": len(ward_counts),
        },
        "distributions": {
            "categories": cat_counts,
            "priorities": pri_counts,
            "wards": ward_counts,
            "languages": lang_counts,
        },
        "recent": data[:20],
    }


@app.get("/api/insights/export")
async def api_export_csv(user: Dict[str, Any] = Depends(get_current_user)):
    """Export all grievance records to CSV."""
    data = get_insights_data()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Grievance ID",
        "Ward",
        "Detected Language",
        "Category",
        "Priority",
        "Emotion",
        "Status",
        "Created At",
        "English Summary",
        "Reasoning",
    ])

    for r in data:
        writer.writerow([
            r.get("id"),
            r.get("ward"),
            r.get("detected_language"),
            r.get("category"),
            r.get("priority"),
            r.get("emotion"),
            r.get("status"),
            r.get("created_at"),
            r.get("english_summary"),
            r.get("reason"),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=civictriage_grievances.csv"},
    )


# ---------------------------------------------------------------------------
# Static Web App & Fallback Frontend Routes
# ---------------------------------------------------------------------------
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return 204 No Content for favicon to prevent 500 or SPA catch-all errors."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the modern web interface."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>CivicTriage Web Platform</h1><p>Static index.html not found.</p>")


# Fallback for client-side navigation
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def catch_all(full_path: str):
    """Route all web requests to the SPA index page."""
    # Ignore API routes
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Endpoint not found")
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>CivicTriage Web Platform</h1>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"[CivicTriage] Starting Web Server on http://127.0.0.1:{port}")
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)
