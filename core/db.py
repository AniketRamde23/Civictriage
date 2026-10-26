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


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a thread-safe connection to the SQLite database with row factory enabled."""
    path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for concurrent reads and writes
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


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
