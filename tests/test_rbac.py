"""
Role-Based Access Control (RBAC) & Object-Level Authorization (IDOR) Tests
Phase 4: Strict Role Boundaries and Resource Ownership Enforcement
"""

from tests.conftest import api_login, get_csrf_token, TEST_PASSWORD


def test_candidate_blocked_from_admin_and_recruiter_routes(client, candidate_user):
    """RBAC-01: Candidate attempting admin or recruiter endpoints receives 403 Forbidden."""
    api_login(client, candidate_user["email"])

    for path in (
        "/api/admin/dashboard",
        "/api/admin/users",
        "/api/admin/applications",
        "/api/admin/interviews",
        "/api/admin/audit-history",
        "/api/admin/reports",
        "/api/recruiter/jobs",
        "/api/recruiter/interviews",
        "/api/recruiter/statistics",
    ):
        resp = client.get(path)
        assert resp.status_code == 403, f"Expected 403 for candidate on {path}, got {resp.status_code}"


def test_recruiter_blocked_from_admin_and_candidate_only_routes(client, recruiter_user, candidate_user):
    """Recruiter attempting admin endpoints or unrelated candidate private data receives 403."""
    _, csrf = api_login(client, recruiter_user["email"])

    for path in (
        "/api/admin/dashboard",
        "/api/admin/users",
        "/api/admin/reports",
        "/api/candidate/profile",
        "/api/candidate/resumes",
        "/api/candidate/interviews",
    ):
        resp = client.get(path)
        assert resp.status_code == 403, f"Expected 403 for recruiter on {path}, got {resp.status_code}"

    # RBAC-02: Recruiter cannot view candidate private profile when candidate has not applied to recruiter's job
    resp_cand = client.get(f"/api/candidates/{candidate_user['candidate_id']}")
    assert resp_cand.status_code == 403

    # Recruiter cannot access candidate resume directly
    resp_res = client.get(f"/api/resumes/{candidate_user['resume_id']}")
    assert resp_res.status_code == 403


def test_recruiter_cannot_modify_or_read_other_recruiter_job(
    client, recruiter_user, second_recruiter_job
):
    """Object-level ownership: Recruiter A cannot update or view applicants for Recruiter B's job."""
    _, csrf = api_login(client, recruiter_user["email"])

    resp_put = client.put(
        f"/api/jobs/{second_recruiter_job}",
        json={"title": "Hijacked Job Title"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp_put.status_code == 403

    resp_apps = client.get(f"/api/jobs/{second_recruiter_job}/applications")
    assert resp_apps.status_code == 403


def test_recruiter_cannot_modify_other_recruiter_application(
    client, second_recruiter_user, test_application
):
    """Object-level ownership: Recruiter B cannot view, update status, or schedule interviews for Recruiter A's application."""
    _, csrf = api_login(client, second_recruiter_user["email"])

    assert client.get(f"/api/applications/{test_application}").status_code == 403
    assert (
        client.post(
            f"/api/applications/{test_application}/status",
            json={"status": "SHORTLISTED", "change_notes": "Unauthorized"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/interviews/schedule",
            json={
                "application_id": test_application,
                "interviewer_name": "Mallory",
                "round_number": 1,
                "round_type": "TECHNICAL",
                "scheduled_at": "2027-03-01 10:00:00",
                "duration_minutes": 60,
            },
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )


def test_candidate_cannot_access_other_candidate_resources(
    client, second_candidate_user, candidate_user, test_application
):
    """IDOR defense: Candidate B cannot read/write Candidate A's profile, resume, or application."""
    _, csrf = api_login(client, second_candidate_user["email"])

    assert client.get(f"/api/candidates/{candidate_user['candidate_id']}").status_code == 403
    assert (
        client.put(
            f"/api/candidates/{candidate_user['candidate_id']}",
            json={"headline": "Tampered"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert client.get(f"/api/resumes/{candidate_user['resume_id']}").status_code == 403
    assert client.get(f"/api/applications/{test_application}").status_code == 403
    assert client.get(f"/api/applications/{test_application}/history").status_code == 403


def test_client_supplied_role_never_elevates_privileges(client, tracker):
    """Submitting role='ADMIN' during registration or login never grants ADMIN role."""
    token = get_csrf_token(client)
    reg_resp = client.post(
        "/api/auth/register-candidate",
        json={
            "email": "spoof.role@test-ats.local",
            "password": TEST_PASSWORD,
            "first_name": "Spoof",
            "last_name": "Attempt",
            "role": "ADMIN",
            "role_id": 1,
        },
        headers={"X-CSRF-Token": token},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.get_json()
    tracker.user_ids.append(reg_data["user_id"])
    tracker.candidate_ids.append(reg_data["candidate_id"])

    login_data, _ = api_login(client, "spoof.role@test-ats.local")
    assert login_data["user"]["role"] == "CANDIDATE"
    assert client.get("/api/admin/dashboard").status_code == 403

