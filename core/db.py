"""
Database operations for CivicTriage.
Uses SQLite with strict parameterised queries and indexes for performance.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "civictriage.db")


def get_default_db_path() -> str:
    """Return the database path, automatically falling back to /tmp in read-only / serverless environments."""
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        return env_path
    # On Vercel, AWS Lambda, or serverless environments with read-only root, use /tmp
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/civictriage.db"

    # Check if local project directory is writable
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "civictriage.db")
    try:
        test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".__write_test__")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return local_path
    except (OSError, IOError):
        return "/tmp/civictriage.db"


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a thread-safe connection to the SQLite database with row factory enabled."""
    path = db_path or get_default_db_path()
    parent_dir = os.path.dirname(os.path.abspath(path))
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception:
            pass

    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # On serverless (Vercel/Lambda), avoid WAL mode as shared memory is restricted
    try:
        if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            conn.execute("PRAGMA journal_mode=DELETE;")
        else:
            conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _auto_seed_initial_data(conn: sqlite3.Connection) -> None:
    """Automatically seeds default demo accounts and sample grievances on fresh DB init."""
    import csv
    from core.auth import hash_password

    cursor = conn.cursor()
    # 1. Citizen Demo Account (citizen@example.com / Citizen123)
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ("Ramesh Sharma (Citizen)", "citizen@example.com", hash_password("Citizen123"), "citizen")
    )
    cit_id = cursor.lastrowid

    # 2. Officer Demo Account (officer@civictriage.gov.in / Officer123)
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ("Officer Priya Deshmukh", "officer@civictriage.gov.in", hash_password("Officer123"), "officer")
    )
    off_id = cursor.lastrowid

    # 3. Seed grievances from CSV if available
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "labelled_grievances.csv")
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    status = "Received" if count % 3 == 0 else "In Progress" if count % 3 == 1 else "Resolved"
                    cursor.execute(
                        """
                        INSERT INTO grievances (
                            user_id, ward, original_text, detected_language,
                            english_summary, emotion, priority, category, reason, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cit_id,
                            row.get("ward", "Ward 1"),
                            row.get("text", ""),
                            row.get("language", "en"),
                            row.get("gold_summary", ""),
                            row.get("gold_emotion", "Neutral"),
                            row.get("gold_priority", "Routine"),
                            row.get("gold_category", "Other"),
                            f"Gold standard labelled record. Triage priority: {row.get('gold_priority', 'Routine')}.",
                            status
                        )
                    )
                    g_id = cursor.lastrowid
                    if status in ("In Progress", "Resolved"):
                        cursor.execute(
                            """
                            INSERT INTO status_notes (grievance_id, officer_id, note)
                            VALUES (?, ?, ?)
                            """,
                            (g_id, off_id, "Standard inspection logged by ward officer.")
                        )
                    count += 1
            conn.commit()
        except Exception:
            pass


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables and indexes."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('citizen', 'officer')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Grievances table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grievances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        ward TEXT,
        original_text TEXT NOT NULL,
        detected_language TEXT,
        english_summary TEXT,
        emotion TEXT,
        priority TEXT,
        category TEXT,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'Received' CHECK(status IN ('Received', 'In Progress', 'Resolved', 'Needs Review')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Status notes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS status_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL,
        officer_id INTEGER NOT NULL,
        note TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (grievance_id) REFERENCES grievances(id) ON DELETE CASCADE,
        FOREIGN KEY (officer_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Indexes for sub-3s query performance on large datasets
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grievances_user_id ON grievances(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grievances_priority ON grievances(priority);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grievances_status ON grievances(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grievances_ward ON grievances(ward);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grievances_created_at ON grievances(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grievances_perf ON grievances(priority, status, ward, created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status_notes_grievance ON status_notes(grievance_id);")

    conn.commit()

    # Auto-seed demo accounts and initial grievances if default DB is newly initialized
    try:
        if db_path is None or db_path == DEFAULT_DB_PATH:
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            if user_count == 0:
                _auto_seed_initial_data(conn)
    except Exception:
        pass

    conn.close()


def insert_user(
    name: str,
    email: str,
    password_hash: str,
    role: str,
    db_path: Optional[str] = None
) -> int:
    """Insert a new user (citizen or officer) using parameterised queries."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (name.strip(), email.strip().lower(), password_hash, role)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user record by email."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user record by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def insert_grievance_received(
    user_id: int,
    ward: Optional[str],
    original_text: str,
    detected_language: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    """
    FR1: Save the grievance record IMMEDIATELY with status 'Received' before classification starts.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO grievances (
            user_id, ward, original_text, detected_language, status
        )
        VALUES (?, ?, ?, ?, 'Received')
        """,
        (user_id, ward.strip() if ward else "Unspecified", original_text.strip(), detected_language)
    )
    grievance_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return grievance_id


def update_grievance_classification(
    grievance_id: int,
    emotion: Optional[str],
    priority: Optional[str],
    category: Optional[str],
    english_summary: Optional[str],
    reason: Optional[str],
    status: str = "Received",
    db_path: Optional[str] = None
) -> None:
    """Update grievance record with LLM & rule classification outcomes."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE grievances
        SET emotion = ?,
            priority = ?,
            category = ?,
            english_summary = ?,
            reason = ?,
            status = ?
        WHERE id = ?
        """,
        (emotion, priority, category, english_summary, reason, status, grievance_id)
    )
    conn.commit()
    conn.close()


def update_grievance_status_and_note(
    grievance_id: int,
    officer_id: int,
    new_status: str,
    note: Optional[str] = None,
    db_path: Optional[str] = None
) -> None:
    """FR6: Officer updates grievance status and adds a historical status note."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE grievances SET status = ? WHERE id = ?",
        (new_status, grievance_id)
    )

    if note and note.strip():
        cursor.execute(
            """
            INSERT INTO status_notes (grievance_id, officer_id, note)
            VALUES (?, ?, ?)
            """,
            (grievance_id, officer_id, note.strip())
        )

    conn.commit()
    conn.close()


def get_grievance_by_id(grievance_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get single grievance details."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_grievances_for_citizen(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Enforce strict citizen data isolation:
    Returns only grievances belonging to the specified citizen, ordered by created_at DESC,
    joined with the latest status note.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            g.*,
            (SELECT sn.note FROM status_notes sn WHERE sn.grievance_id = g.id ORDER BY sn.created_at DESC LIMIT 1) as latest_note,
            (SELECT sn.created_at FROM status_notes sn WHERE sn.grievance_id = g.id ORDER BY sn.created_at DESC LIMIT 1) as latest_note_at
        FROM grievances g
        WHERE g.user_id = ?
        ORDER BY g.created_at DESC
        """,
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_officer_queue(
    priority_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    ward_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    FR5: Officer queue sorted by priority (Immediate > Soon > Routine), then by age (oldest first).
    Includes filter parameters and returns full record info.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT 
            g.*,
            u.name as citizen_name,
            u.email as citizen_email,
            (SELECT sn.note FROM status_notes sn WHERE sn.grievance_id = g.id ORDER BY sn.created_at DESC LIMIT 1) as latest_note,
            (SELECT COUNT(*) FROM status_notes sn WHERE sn.grievance_id = g.id) as note_count
        FROM grievances g
        JOIN users u ON g.user_id = u.id
        WHERE 1=1
    """
    params: List[Any] = []

    if priority_filter and priority_filter != "All":
        query += " AND g.priority = ?"
        params.append(priority_filter)

    if category_filter and category_filter != "All":
        query += " AND g.category = ?"
        params.append(category_filter)

    if ward_filter and ward_filter != "All":
        query += " AND g.ward = ?"
        params.append(ward_filter)

    if status_filter and status_filter != "All":
        query += " AND g.status = ?"
        params.append(status_filter)

    # Sort order: Immediate > Soon > Routine > NULLs, then age (created_at ASC: oldest first)
    query += """
        ORDER BY 
            CASE g.priority
                WHEN 'High' THEN 1
                WHEN 'Immediate' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Soon' THEN 2
                WHEN 'Low' THEN 3
                WHEN 'Routine' THEN 3
                ELSE 4
            END ASC,
            g.created_at ASC
    """

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_status_notes_for_grievance(grievance_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve full audit trail of notes for a grievance."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            sn.id,
            sn.note,
            sn.created_at,
            u.name as officer_name,
            u.email as officer_email
        FROM status_notes sn
        JOIN users u ON sn.officer_id = u.id
        WHERE sn.grievance_id = ?
        ORDER BY sn.created_at ASC
        """,
        (grievance_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_wards(db_path: Optional[str] = None) -> List[str]:
    """Retrieve distinct ward names for filtering."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ward FROM grievances WHERE ward IS NOT NULL AND ward != '' ORDER BY ward")
    rows = cursor.fetchall()
    conn.close()
    return [r["ward"] for r in rows]


def get_insights_data(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve data for analytics and CSV export."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            id,
            ward,
            detected_language,
            category,
            priority,
            emotion,
            status,
            created_at,
            english_summary,
            reason
        FROM grievances
        ORDER BY created_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
