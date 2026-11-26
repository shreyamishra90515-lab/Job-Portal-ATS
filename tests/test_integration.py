"""
End-to-End Integration Workflow Tests
Phase 4: Full Candidate, Recruiter, Admin & Unauthorized Access Workflows via Flask Client
"""

from tests.conftest import TEST_PASSWORD, _unique_email, api_login, get_csrf_token


def test_workflow_candidate_and_recruiter_end_to_end(app, tracker):
    """
    Workflow 1 & 2:
    - Recruiter registers, logs in, creates a job
    - Candidate registers, logs in, updates profile, adds resume, browses job, applies
    - Recruiter views applicants, updates status, schedules interview, checks stats
    - Candidate sees updated application, status history, and scheduled interview
    """
    rec_client = app.test_client()
    cand_client = app.test_client()

    # 1. Recruiter registers & logs in
    rec_email = _unique_email("wfrec")
    csrf_r = get_csrf_token(rec_client)
    r_reg = rec_client.post(
        "/api/auth/register-recruiter",
        json={
            "email": rec_email,
            "password": TEST_PASSWORD,
            "first_name": "Elena",
            "last_name": "Hiring",
            "company_name": "CloudWorks Inc",
            "company_website": "https://cloudworks.example.com",
        },
        headers={"X-CSRF-Token": csrf_r},
    )
    assert r_reg.status_code == 201
    tracker.user_ids.append(r_reg.get_json()["user_id"])
    tracker.recruiter_ids.append(r_reg.get_json()["recruiter_id"])

    _, csrf_r = api_login(rec_client, rec_email)

    # Recruiter creates a job
    job_resp = rec_client.post(
        "/api/jobs",
        json={
            "title": "Integration Platform Engineer",
            "description": "Build secure distributed APIs.",
            "employment_type": "FULL_TIME",
            "workplace_type": "REMOTE",
            "location": "Remote",
            "min_experience_years": 2.0,
            "salary_min": 120000,
            "salary_max": 150000,
            "status": "ACTIVE",
            "deadline_date": "2027-12-31",
        },
        headers={"X-CSRF-Token": csrf_r},
    )
    assert job_resp.status_code == 201
    job_id = job_resp.get_json()["job_id"]
    tracker.job_ids.append(job_id)

    # 2. Candidate registers, updates profile, creates resume, browses & applies
    cand_email = _unique_email("wfcand")
    csrf_c = get_csrf_token(cand_client)
    c_reg = cand_client.post(
        "/api/auth/register-candidate",
        json={
            "email": cand_email,
            "password": TEST_PASSWORD,
            "first_name": "Aarav",
            "last_name": "Applicant",
            "years_of_experience": 4.0,
        },
        headers={"X-CSRF-Token": csrf_c},
    )
    assert c_reg.status_code == 201
    tracker.user_ids.append(c_reg.get_json()["user_id"])
    tracker.candidate_ids.append(c_reg.get_json()["candidate_id"])

    _, csrf_c = api_login(cand_client, cand_email)

    assert (
        cand_client.put(
            "/api/candidate/profile",
            json={"headline": "Senior Python Developer", "current_location": "San Jose, CA"},
            headers={"X-CSRF-Token": csrf_c},
        ).status_code
        == 200
    )

    res_resp = cand_client.post(
        "/api/candidate/resumes",
        json={"file_name": "aarav_integration_cv.pdf", "file_size_kb": 240, "is_primary": True},
        headers={"X-CSRF-Token": csrf_c},
    )
    assert res_resp.status_code == 201
    resume_id = res_resp.get_json()["resume_id"]
    tracker.resume_ids.append(resume_id)

    # Browse jobs
    browse = cand_client.get("/api/jobs/search", query_string={"title": "Integration Platform"})
    assert browse.status_code == 200
    assert any(j["job_id"] == job_id for j in browse.get_json()["jobs"])

    # Apply to job
    apply_resp = cand_client.post(
        f"/api/jobs/{job_id}/apply",
        json={"resume_id": resume_id, "cover_letter": "Excited to contribute!"},
        headers={"X-CSRF-Token": csrf_c},
    )
    assert apply_resp.status_code == 201
    app_id = apply_resp.get_json()["application_id"]
    tracker.application_ids.append(app_id)

    # Candidate sees application
    cand_apps = cand_client.get("/api/candidate/applications")
    assert cand_apps.status_code == 200
    assert any(a["application_id"] == app_id for a in cand_apps.get_json()["applications"])

    # 3. Recruiter views applicants, updates status, schedules interview, checks stats
    job_apps = rec_client.get(f"/api/jobs/{job_id}/applications")
    assert job_apps.status_code == 200
    assert any(a["application_id"] == app_id for a in job_apps.get_json()["applications"])

    status_resp = rec_client.post(
        f"/api/applications/{app_id}/status",
        json={"status": "SHORTLISTED", "change_notes": "Strong match"},
        headers={"X-CSRF-Token": csrf_r},
    )
    assert status_resp.status_code == 200

    int_resp = rec_client.post(
        "/api/interviews/schedule",
        json={
            "application_id": app_id,
            "interviewer_name": "Lead Architect",
            "round_number": 1,
            "round_type": "TECHNICAL",
            "scheduled_at": "2027-09-10 14:00:00",
            "duration_minutes": 60,
            "meeting_link": "https://meet.example.com/wf1",
            "location": "Online",
        },
        headers={"X-CSRF-Token": csrf_r},
    )
    assert int_resp.status_code == 201
    interview_id = int_resp.get_json()["interview_id"]
    tracker.interview_ids.append(interview_id)

    stats_resp = rec_client.get("/api/recruiter/statistics")
    assert stats_resp.status_code == 200
    assert any(s["job_id"] == job_id for s in stats_resp.get_json()["statistics"])

    # 4. Candidate observes updated status, audit history & scheduled interview
    hist_resp = cand_client.get(f"/api/applications/{app_id}/history")
    assert hist_resp.status_code == 200
    statuses = [h["new_status"] for h in hist_resp.get_json()["history"]]
    assert statuses == ["APPLIED", "SHORTLISTED", "INTERVIEW_SCHEDULED"]

    cand_ints = cand_client.get("/api/candidate/interviews")
    assert cand_ints.status_code == 200
    assert any(i["interview_id"] == interview_id for i in cand_ints.get_json()["interviews"])


def test_workflow_admin_oversight(client, admin_user):
    """Workflow 3: Admin logs in and inspects dashboard, users, jobs, applications, interviews & reports."""
    api_login(client, admin_user["email"])

    assert client.get("/api/admin/dashboard").status_code == 200
    assert client.get("/api/admin/users").status_code == 200
    assert client.get("/api/admin/applications").status_code == 200
    assert client.get("/api/admin/interviews").status_code == 200
    assert client.get("/api/admin/audit-history").status_code == 200
    assert client.get("/api/admin/reports").status_code == 200
    assert client.get("/api/recruiter/jobs").status_code == 200
    assert client.get("/api/candidate/applications").status_code == 200


def test_workflow_unauthorized_boundaries(
    app, candidate_user, second_candidate_user, recruiter_user, test_application
):
    """Workflow 4: Cross-role and cross-owner unauthorized access is strictly blocked."""
    c1 = app.test_client()
    c2 = app.test_client()
    r1 = app.test_client()

    api_login(c1, candidate_user["email"])
    api_login(c2, second_candidate_user["email"])
    api_login(r1, recruiter_user["email"])

    # Candidate -> recruiter & admin resources
    assert c1.get("/api/recruiter/statistics").status_code == 403
    assert c1.get("/api/admin/reports").status_code == 403

    # Recruiter -> admin resource
    assert r1.get("/api/admin/users").status_code == 403

    # Candidate B -> Candidate A resource
    assert c2.get(f"/api/applications/{test_application}").status_code == 403
    assert c2.get(f"/api/candidates/{candidate_user['candidate_id']}").status_code == 403

