"""
Pytest Configuration and Isolated Database Fixtures
Phase 4: Reproducible Test Environment for Auth, RBAC, Security, Procedures & Integrity
"""

import uuid
import pytest
from app import create_app
from app.db import get_db_connection, execute_procedure
from app.security.auth import hash_password
from config import TestingConfig


TEST_PASSWORD = "TestUser@123!"


def _unique_email(prefix: str) -> str:
    return f"{prefix}.{uuid.uuid4().hex[:10]}@test-ats.local"


class TestResourceTracker:
    """Tracks test-created DB entities for deterministic FK-safe cleanup."""

    def __init__(self):
        self.interview_ids = []
        self.application_ids = []
        self.job_ids = []
        self.resume_ids = []
        self.candidate_ids = []
        self.recruiter_ids = []
        self.user_ids = []

    def cleanup(self):
        conn = get_db_connection(TestingConfig)
        cur = conn.cursor()
        try:
            if self.interview_ids:
                fmt = ",".join(["%s"] * len(self.interview_ids))
                cur.execute(f"DELETE FROM interviews WHERE interview_id IN ({fmt});", self.interview_ids)

            if self.application_ids:
                fmt = ",".join(["%s"] * len(self.application_ids))
                cur.execute(f"DELETE FROM interviews WHERE application_id IN ({fmt});", self.application_ids)
                cur.execute(f"DELETE FROM applications WHERE application_id IN ({fmt});", self.application_ids)

            if self.job_ids:
                fmt = ",".join(["%s"] * len(self.job_ids))
                cur.execute(
                    f"DELETE i FROM interviews i INNER JOIN applications a ON i.application_id = a.application_id WHERE a.job_id IN ({fmt});",
                    self.job_ids,
                )
                cur.execute(f"DELETE FROM applications WHERE job_id IN ({fmt});", self.job_ids)
                cur.execute(f"DELETE FROM jobs WHERE job_id IN ({fmt});", self.job_ids)

            if self.candidate_ids:
                fmt = ",".join(["%s"] * len(self.candidate_ids))
                cur.execute(
                    f"DELETE i FROM interviews i INNER JOIN applications a ON i.application_id = a.application_id WHERE a.candidate_id IN ({fmt});",
                    self.candidate_ids,
                )
                cur.execute(f"DELETE FROM applications WHERE candidate_id IN ({fmt});", self.candidate_ids)
                cur.execute(f"DELETE FROM resumes WHERE candidate_id IN ({fmt});", self.candidate_ids)
                cur.execute(f"DELETE FROM candidate_profiles WHERE candidate_id IN ({fmt});", self.candidate_ids)

            if self.recruiter_ids:
                fmt = ",".join(["%s"] * len(self.recruiter_ids))
                cur.execute(
                    f"DELETE i FROM interviews i INNER JOIN applications a ON i.application_id = a.application_id INNER JOIN jobs j ON a.job_id = j.job_id WHERE j.recruiter_id IN ({fmt});",
                    self.recruiter_ids,
                )
                cur.execute(
                    f"DELETE a FROM applications a INNER JOIN jobs j ON a.job_id = j.job_id WHERE j.recruiter_id IN ({fmt});",
                    self.recruiter_ids,
                )
                cur.execute(f"DELETE FROM jobs WHERE recruiter_id IN ({fmt});", self.recruiter_ids)
                cur.execute(f"DELETE FROM recruiter_profiles WHERE recruiter_id IN ({fmt});", self.recruiter_ids)

            if self.resume_ids:
                fmt = ",".join(["%s"] * len(self.resume_ids))
                cur.execute(f"DELETE FROM resumes WHERE resume_id IN ({fmt});", self.resume_ids)

            if self.user_ids:
                fmt = ",".join(["%s"] * len(self.user_ids))
                cur.execute(f"DELETE FROM users WHERE user_id IN ({fmt});", self.user_ids)

            conn.commit()
        finally:
            cur.close()
            conn.close()


@pytest.fixture(scope="session")
def app():
    """Create Flask application configured for testing."""
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    """Fresh Flask test client per test (isolated cookies/session)."""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def tracker():
    """Tracks DB rows created during a test and cleans them up afterwards."""
    t = TestResourceTracker()
    yield t
    t.cleanup()


@pytest.fixture()
def db_conn():
    """Direct MySQL connection for database/procedure/integrity tests."""
    conn = get_db_connection(TestingConfig)
    yield conn
    conn.close()


def get_csrf_token(client) -> str:
    """Fetch a valid session-bound CSRF token from the API."""
    resp = client.get("/api/auth/csrf-token")
    assert resp.status_code == 200
    return resp.get_json()["csrf_token"]


def api_login(client, email: str, password: str = TEST_PASSWORD) -> tuple[dict, str]:
    """Authenticate a Flask test client and return (response_json, rotated_csrf_token)."""
    token = get_csrf_token(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": token},
    )
    data = resp.get_json()
    assert resp.status_code == 200, f"Login failed: {data}"
    return data, data.get("csrf_token") or resp.headers.get("X-CSRF-Token")


def _create_candidate(tracker: TestResourceTracker, prefix: str = "cand"):
    email = _unique_email(prefix)
    pw_hash = hash_password(TEST_PASSWORD)
    res = execute_procedure(
        "sp_register_candidate",
        (
            email,
            pw_hash,
            "Test",
            "Candidate",
            "+1-555-0100",
            "Backend Python Engineer",
            "Test summary",
            "Remote",
            3.5,
            "B.S. Computer Science",
            "https://linkedin.com/in/testcand",
            "https://example.com",
        ),
        out_param_names=("p_user_id", "p_candidate_id"),
        config=TestingConfig,
    )
    user_id = res["p_user_id"]
    cand_id = res["p_candidate_id"]
    tracker.user_ids.append(user_id)
    tracker.candidate_ids.append(cand_id)

    conn = get_db_connection(TestingConfig)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO resumes (candidate_id, file_name, file_path, file_size_kb, is_primary) VALUES (%s, %s, %s, %s, %s);",
            (cand_id, f"{prefix}_resume.pdf", f"/uploads/resumes/{prefix}_resume.pdf", 200, True),
        )
        resume_id = cur.lastrowid
        conn.commit()
        tracker.resume_ids.append(resume_id)
    finally:
        cur.close()
        conn.close()

    return {
        "user_id": user_id,
        "candidate_id": cand_id,
        "resume_id": resume_id,
        "email": email,
        "password": TEST_PASSWORD,
        "role": "CANDIDATE",
    }


def _create_recruiter(tracker: TestResourceTracker, prefix: str = "rec"):
    email = _unique_email(prefix)
    pw_hash = hash_password(TEST_PASSWORD)
    res = execute_procedure(
        "sp_register_recruiter",
        (
            email,
            pw_hash,
            "Test",
            "Recruiter",
            "+1-555-0200",
            f"Company {prefix}",
            "https://example.com",
            "Engineering",
            "Talent Partner",
            "San Francisco, CA",
        ),
        out_param_names=("p_user_id", "p_recruiter_id"),
        config=TestingConfig,
    )
    user_id = res["p_user_id"]
    rec_id = res["p_recruiter_id"]
    tracker.user_ids.append(user_id)
    tracker.recruiter_ids.append(rec_id)
    return {
        "user_id": user_id,
        "recruiter_id": rec_id,
        "email": email,
        "password": TEST_PASSWORD,
        "role": "RECRUITER",
    }


def _create_admin(tracker: TestResourceTracker, prefix: str = "admin"):
    email = _unique_email(prefix)
    pw_hash = hash_password(TEST_PASSWORD)
    conn = get_db_connection(TestingConfig)
    cur = conn.cursor()
    try:
        cur.execute("SELECT role_id FROM roles WHERE role_name = 'ADMIN';")
        role_row = cur.fetchone()
        cur.execute(
            """
            INSERT INTO users (role_id, email, password_hash, first_name, last_name, phone, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE);
            """,
            (role_row["role_id"], email, pw_hash, "Test", "Admin", "+1-555-0001"),
        )
        user_id = cur.lastrowid
        conn.commit()
        tracker.user_ids.append(user_id)
    finally:
        cur.close()
        conn.close()

    return {
        "user_id": user_id,
        "email": email,
        "password": TEST_PASSWORD,
        "role": "ADMIN",
    }


def _create_job(tracker: TestResourceTracker, recruiter_id: int, status: str = "ACTIVE", deadline: str = "2027-12-31"):
    conn = get_db_connection(TestingConfig)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO jobs (
                recruiter_id, title, description, employment_type, workplace_type,
                location, min_experience_years, salary_min, salary_max, status, deadline_date
            ) VALUES (%s, %s, %s, 'FULL_TIME', 'REMOTE', 'Remote', 2.0, 100000.00, 140000.00, %s, %s);
            """,
            (recruiter_id, "Security Test Engineer", "Build secure ATS systems.", status, deadline),
        )
        job_id = cur.lastrowid
        conn.commit()
        tracker.job_ids.append(job_id)
        return job_id
    finally:
        cur.close()
        conn.close()


@pytest.fixture()
def candidate_user(tracker):
    return _create_candidate(tracker, "cand1")


@pytest.fixture()
def second_candidate_user(tracker):
    return _create_candidate(tracker, "cand2")


@pytest.fixture()
def recruiter_user(tracker):
    return _create_recruiter(tracker, "rec1")


@pytest.fixture()
def second_recruiter_user(tracker):
    return _create_recruiter(tracker, "rec2")


@pytest.fixture()
def admin_user(tracker):
    return _create_admin(tracker, "admin1")


@pytest.fixture()
def test_job(tracker, recruiter_user):
    return _create_job(tracker, recruiter_user["recruiter_id"], status="ACTIVE")


@pytest.fixture()
def second_recruiter_job(tracker, second_recruiter_user):
    return _create_job(tracker, second_recruiter_user["recruiter_id"], status="ACTIVE")


@pytest.fixture()
def test_application(tracker, candidate_user, test_job):
    res = execute_procedure(
        "sp_apply_job",
        (test_job, candidate_user["candidate_id"], candidate_user["resume_id"], "Excited to apply."),
        out_param_names=("p_application_id",),
        config=TestingConfig,
    )
    app_id = res["p_application_id"]
    tracker.application_ids.append(app_id)
    return app_id

