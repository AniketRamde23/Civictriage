"""
Authentication and password security module for CivicTriage.
Uses bcrypt for secure one-way password hashing.
"""

from typing import Any, Dict, Optional, Tuple
import bcrypt
from core.db import get_user_by_email, insert_user


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with a salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def register_citizen(
    name: str,
    email: str,
    password: str,
    db_path: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new citizen.
    Officers CANNOT self-register through this function.
    """
    clean_name = name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        return False, "Full name is required.", None
    if not clean_email or "@" not in clean_email:
        return False, "A valid email address is required.", None
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    existing = get_user_by_email(clean_email, db_path=db_path)
    if existing:
        return False, "An account with this email already exists.", None

    pw_hash = hash_password(password)
    user_id = insert_user(
        name=clean_name,
        email=clean_email,
        password_hash=pw_hash,
        role="citizen",
        db_path=db_path
    )

    user = get_user_by_email(clean_email, db_path=db_path)
    return True, "Citizen registered successfully.", user


def authenticate_user(
    email: str,
    password: str,
    db_path: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Authenticate either citizen or officer with email and password."""
    clean_email = email.strip().lower()
    if not clean_email or not password:
        return False, "Email and password are required.", None

    user = get_user_by_email(clean_email, db_path=db_path)
    if not user:
        return False, "Invalid email or password.", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid email or password.", None

    return True, "Login successful.", user
