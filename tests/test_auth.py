"""
Authentication & Session Security Tests
Phase 4: Bcrypt Hashing, Login/Logout, Session Hardening & Failure Modes
"""

from app.db import get_db_connection
from app.security.auth import hash_password, verify_password, authenticate_user
from config import TestingConfig
from tests.conftest import TEST_PASSWORD, get_csrf_token, api_login


def test_bcrypt_hash_and_verify():
    """Passwords use Bcrypt with unique salts and verify in constant time."""
    h1 = hash_password(TEST_PASSWORD)
    h2 = hash_password(TEST_PASSWORD)
    assert h1.startswith("$2b$12$")
    assert h1 != h2
    assert h1 != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, h1) is True
    assert verify_password("WrongPassword@1", h1) is False
    assert verify_password("", h1) is False
    assert verify_password(TEST_PASSWORD, "not-a-valid-hash") is False


def test_valid_login_and_session_establishment(client, candidate_user):
    """AUTH-01: Valid credentials authenticate, set HttpOnly/SameSite cookies, and omit password_hash."""
    token = get_csrf_token(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": candidate_user["email"], "password": TEST_PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user"]["email"] == candidate_user["email"]
    assert body["user"]["role"] == "CANDIDATE"
    assert body["user"]["profile_id"] == candidate_user["candidate_id"]
    assert "password_hash" not in body["user"]
    assert "password" not in body["user"]

    # Verify session cookie security attributes
    set_cookie = "\n".join(resp.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie


def test_login_invalid_email(client):
    """Non-existent email is rejected with 401 and generic error message."""
    token = get_csrf_token(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@nonexistent-ats.local", "password": TEST_PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Invalid email or password."


def test_login_wrong_password(client, candidate_user):
    """AUTH-02: Wrong password is rejected with 401."""
    token = get_csrf_token(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": candidate_user["email"], "password": "Incorrect@999"},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Invalid email or password."


def test_login_empty_and_malformed_credentials(client):
    """Empty credentials and malformed emails are rejected with 400."""
    token = get_csrf_token(client)

    resp_empty = client.post(
        "/api/auth/login",
        json={"email": "", "password": ""},
        headers={"X-CSRF-Token": token},
    )
    assert resp_empty.status_code == 400

    resp_malformed = client.post(
        "/api/auth/login",
        json={"email": "not-an-email", "password": TEST_PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert resp_malformed.status_code == 400


def test_inactive_user_cannot_authenticate(candidate_user):
    """Deactivated user accounts are denied authentication."""
    conn = get_db_connection(TestingConfig)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET is_active = FALSE WHERE user_id = %s;", (candidate_user["user_id"],))
        conn.commit()
        assert authenticate_user(candidate_user["email"], TEST_PASSWORD, config=TestingConfig) is None
    finally:
        cur.execute("UPDATE users SET is_active = TRUE WHERE user_id = %s;", (candidate_user["user_id"],))
        conn.commit()
        cur.close()
        conn.close()


def test_logout_clears_session(client, candidate_user):
    """Logging out clears session state and revokes access to protected routes."""
    _, csrf_token = api_login(client, candidate_user["email"])

    me_before = client.get("/api/auth/me")
    assert me_before.status_code == 200

    logout_resp = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_resp.status_code == 200

    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 401


def test_unauthenticated_access_rejected(client):
    """Protected routes return 401 when accessed without a session."""
    for path in (
        "/api/auth/me",
        "/api/admin/dashboard",
        "/api/recruiter/jobs",
        "/api/candidate/applications",
    ):
        resp = client.get(path)
        assert resp.status_code == 401

