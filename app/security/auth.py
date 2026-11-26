"""
Job Portal and Application Tracking System (ATS)
Authentication & Password Security Service
Phase 4: Bcrypt Hashing, Session Establishment & Credential Protection
"""

import bcrypt
from flask import session
from app.db import execute_query
from app.security.csrf import generate_csrf_token

# Precomputed dummy Bcrypt hash used solely to equalize response timing on unknown emails.
# Contains no real or usable password.
_DUMMY_BCRYPT_HASH = bcrypt.hashpw(b"ats-timing-mitigation-sentinel", bcrypt.gensalt(rounds=12))


def hash_password(password: str) -> str:
    """
    Securely hash a plaintext password using Bcrypt with a workload cost of 12.
    Never store or log plaintext passwords.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password exceeds Bcrypt 72-byte maximum length.")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(encoded, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored Bcrypt hash using constant-time comparison.
    """
    if not password or not stored_hash or not isinstance(password, str) or not isinstance(stored_hash, str):
        return False
    try:
        encoded_pw = password.encode("utf-8")
        if len(encoded_pw) > 72:
            return False
        return bcrypt.checkpw(encoded_pw, stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def authenticate_user(email: str, password: str, config=None) -> dict | None:
    """
    Authenticate user credentials against the database.
    - Uses parameterized SQL (immune to SQL injection).
    - Verifies Bcrypt password hash in constant time.
    - Resolves authoritative role and candidate/recruiter profile ID from DB.
    - Never returns the password hash.
    """
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        return None

    sql = """
        SELECT
            u.user_id,
            u.role_id,
            u.email,
            u.password_hash,
            u.first_name,
            u.last_name,
            u.is_active,
            r.role_name
        FROM users u
        INNER JOIN roles r ON u.role_id = r.role_id
        WHERE u.email = %s;
    """
    user_record = execute_query(sql, (email.strip().lower(),), fetch="one", config=config)

    if not user_record:
        # Mitigate user enumeration timing side-channels
        bcrypt.checkpw(b"invalid_timing_mitigation", _DUMMY_BCRYPT_HASH)
        return None

    stored_hash = user_record.get("password_hash")
    password_valid = verify_password(password, stored_hash)

    if not password_valid or not user_record.get("is_active"):
        return None

    user_id = user_record["user_id"]
    role_name = user_record["role_name"]
    profile_id = None

    if role_name == "CANDIDATE":
        cand_row = execute_query(
            "SELECT candidate_id FROM candidate_profiles WHERE user_id = %s;",
            (user_id,),
            fetch="one",
            config=config,
        )
        if cand_row:
            profile_id = cand_row["candidate_id"]
    elif role_name == "RECRUITER":
        rec_row = execute_query(
            "SELECT recruiter_id FROM recruiter_profiles WHERE user_id = %s;",
            (user_id,),
            fetch="one",
            config=config,
        )
        if rec_row:
            profile_id = rec_row["recruiter_id"]

    return {
        "user_id": user_id,
        "email": user_record["email"],
        "first_name": user_record["first_name"],
        "last_name": user_record["last_name"],
        "role": role_name,
        "profile_id": profile_id,
    }


def login_user(user_data: dict) -> str:
    """
    Establish a secure authenticated session.
    Clears prior session state to prevent session fixation and rotates CSRF token.
    Only stores minimum authoritative identity data (never passwords or hashes).
    """
    session.clear()

    session["user_id"] = user_data["user_id"]
    session["role"] = user_data["role"]
    session["email"] = user_data["email"]
    session["first_name"] = user_data["first_name"]
    session["last_name"] = user_data["last_name"]
    session["profile_id"] = user_data.get("profile_id")
    session.permanent = True

    return generate_csrf_token()


def logout_user():
    """Terminate the authenticated session and purge all session state."""
    session.clear()


def get_current_user() -> dict | None:
    """Return identity summary of currently authenticated user from session."""
    if "user_id" not in session:
        return None
    return {
        "user_id": session.get("user_id"),
        "role": session.get("role"),
        "email": session.get("email"),
        "first_name": session.get("first_name"),
        "last_name": session.get("last_name"),
        "profile_id": session.get("profile_id"),
    }
