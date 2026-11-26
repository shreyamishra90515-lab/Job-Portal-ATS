"""
Security Penetration & Defense Tests
Phase 4: SQL Injection, XSS Escaping, CSRF Enforcement & Error Sanitization
"""

import pytest
from tests.conftest import api_login, get_csrf_token, TEST_PASSWORD


@pytest.mark.parametrize(
    "payload",
    [
        "' OR '1'='1",
        "' OR 1=1 --",
        "admin'--",
        "' UNION SELECT 1,2,3,4,5,6,7,8 --",
    ],
)
def test_sqli_login_bypass_rejected(client, payload):
    """SQL-01: Malicious SQL injection payloads never bypass authentication."""
    token = get_csrf_token(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": payload, "password": "' OR '1'='1"},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code in (400, 401)
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        "' OR '1'='1",
        "'; DROP TABLE jobs; --",
        "' UNION SELECT user_id, email, password_hash, 1, 1, 1, 1 FROM users --",
    ],
)
def test_sqli_job_search_parameterized(client, payload):
    """Parameterized job search safely handles SQLi strings without error or injection."""
    resp = client.get("/api/jobs/search", query_string={"title": payload})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "jobs" in body
    assert isinstance(body["jobs"], list)


def test_xss_input_escaped_on_storage_and_output(client, candidate_user):
    """XSS-01: Script tags submitted to profile update are HTML-escaped before storage."""
    _, csrf = api_login(client, candidate_user["email"])
    xss_payload = "<script>alert('XSS')</script>"

    resp = client.put(
        "/api/candidate/profile",
        json={"headline": xss_payload},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    prof_resp = client.get("/api/candidate/profile")
    assert prof_resp.status_code == 200
    stored_headline = prof_resp.get_json()["profile"]["headline"]
    assert "<script>" not in stored_headline
    assert "&lt;script&gt;" in stored_headline


def test_csrf_missing_and_invalid_tokens_rejected(client, candidate_user):
    """CSRF-01: State-changing POST/PUT requests without a valid CSRF token are rejected (400)."""
    # Missing CSRF token on login POST
    resp_no_session_csrf = client.post(
        "/api/auth/login",
        json={"email": candidate_user["email"], "password": TEST_PASSWORD},
    )
    assert resp_no_session_csrf.status_code == 400

    # Log in legitimately, then send state-changing PUT without CSRF token
    _, csrf = api_login(client, candidate_user["email"])
    resp_missing_header = client.put(
        "/api/candidate/profile",
        json={"headline": "Updated Without CSRF"},
    )
    assert resp_missing_header.status_code == 400

    # Invalid CSRF token rejected
    resp_bad_token = client.put(
        "/api/candidate/profile",
        json={"headline": "Updated With Bad CSRF"},
        headers={"X-CSRF-Token": "forged-invalid-csrf-token"},
    )
    assert resp_bad_token.status_code == 400

    # Valid rotated CSRF token succeeds
    resp_ok = client.put(
        "/api/candidate/profile",
        json={"headline": "Valid CSRF Update"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp_ok.status_code == 200


def test_security_headers_and_sanitized_errors(client, admin_user):
    """Verify security headers and confirm error responses conceal SQL/stack traces/passwords."""
    api_login(client, admin_user["email"])

    resp_users = client.get("/api/admin/users")
    assert resp_users.status_code == 200
    assert resp_users.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp_users.headers.get("X-Frame-Options") == "DENY"
    for user in resp_users.get_json()["users"]:
        assert "password_hash" not in user

    resp_404 = client.get("/api/nonexistent-endpoint")
    assert resp_404.status_code == 404
    err_text = resp_404.get_data(as_text=True)
    assert "Traceback" not in err_text
    assert "SELECT" not in err_text

