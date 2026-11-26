"""
Phase 2 Stored Procedure Tests
Phase 4: Verifying sp_register_candidate, sp_register_recruiter, sp_apply_job,
         sp_update_application_status, and sp_schedule_interview without modifying them.
"""

import pytest
from app.db import DatabaseSecurityError, execute_procedure, execute_query
from app.security.auth import hash_password
from config import TestingConfig
from tests.conftest import TEST_PASSWORD, _unique_email, _create_job


def test_sp_register_candidate_success_duplicate_and_rollback(tracker):
    """Test sp_register_candidate registration, role binding, duplicate rejection & rollback."""
    email = _unique_email("spcand")
    out = execute_procedure(
        "sp_register_candidate",
        (
            email,
            hash_password(TEST_PASSWORD),
            "Alice",
            "Tester",
            "+1-555-0111",
            "Data Engineer",
            "Summary",
            "Austin, TX",
            4.0,
            "B.S.",
            "https://linkedin.com/in/alice",
            "https://alice.dev",
        ),
        out_param_names=("p_user_id", "p_candidate_id"),
        config=TestingConfig,
    )
    user_id = out["p_user_id"]
    cand_id = out["p_candidate_id"]
    assert user_id > 0 and cand_id > 0
    tracker.user_ids.append(user_id)
    tracker.candidate_ids.append(cand_id)

    role_row = execute_query(
        "SELECT r.role_name FROM users u INNER JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = %s;",
        (user_id,),
        fetch="one",
        config=TestingConfig,
    )
    assert role_row["role_name"] == "CANDIDATE"

    # Duplicate email rejected
    with pytest.raises(DatabaseSecurityError) as dup_err:
        execute_procedure(
            "sp_register_candidate",
            (email, hash_password(TEST_PASSWORD), "Dup", "User", "", "", "", "", 1.0, "", "", ""),
            out_param_names=("p_user_id", "p_candidate_id"),
            config=TestingConfig,
        )
    assert "Duplicate Error" in dup_err.value.message

    # Negative experience rolls back cleanly
    bad_email = _unique_email("badcand")
    with pytest.raises(DatabaseSecurityError):
        execute_procedure(
            "sp_register_candidate",
            (bad_email, hash_password(TEST_PASSWORD), "Bad", "Exp", "", "", "", "", -1.0, "", "", ""),
            out_param_names=("p_user_id", "p_candidate_id"),
            config=TestingConfig,
        )
    assert (
        execute_query("SELECT user_id FROM users WHERE email = %s;", (bad_email,), fetch="one", config=TestingConfig)
        is None
    )


def test_sp_register_recruiter_success_duplicate_and_rollback(tracker):
    """Test sp_register_recruiter registration, role binding, duplicate rejection & rollback."""
    email = _unique_email("sprec")
    out = execute_procedure(
        "sp_register_recruiter",
        (
            email,
            hash_password(TEST_PASSWORD),
            "Bob",
            "Recruiter",
            "+1-555-0222",
            "Acme Corp",
            "https://acme.example.com",
            "Talent",
            "Lead Recruiter",
            "NYC",
        ),
        out_param_names=("p_user_id", "p_recruiter_id"),
        config=TestingConfig,
    )
    user_id = out["p_user_id"]
    rec_id = out["p_recruiter_id"]
    assert user_id > 0 and rec_id > 0
    tracker.user_ids.append(user_id)
    tracker.recruiter_ids.append(rec_id)

    role_row = execute_query(
        "SELECT r.role_name FROM users u INNER JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = %s;",
        (user_id,),
        fetch="one",
        config=TestingConfig,
    )
    assert role_row["role_name"] == "RECRUITER"

    # Duplicate email rejected
    with pytest.raises(DatabaseSecurityError):
        execute_procedure(
            "sp_register_recruiter",
            (email, hash_password(TEST_PASSWORD), "Dup", "Rec", "", "Acme", "", "", "", ""),
            out_param_names=("p_user_id", "p_recruiter_id"),
            config=TestingConfig,
        )

    # Missing company name rolls back cleanly
    bad_email = _unique_email("badrec")
    with pytest.raises(DatabaseSecurityError):
        execute_procedure(
            "sp_register_recruiter",
            (bad_email, hash_password(TEST_PASSWORD), "Bad", "Rec", "", "", "", "", "", ""),
            out_param_names=("p_user_id", "p_recruiter_id"),
            config=TestingConfig,
        )
    assert (
        execute_query("SELECT user_id FROM users WHERE email = %s;", (bad_email,), fetch="one", config=TestingConfig)
        is None
    )


def test_sp_apply_job_rules(tracker, candidate_user, second_candidate_user, recruiter_user, test_job):
    """Test sp_apply_job: valid apply, match_score, APPLIED status, duplicate, wrong resume, inactive & expired job."""
    # Valid application
    out = execute_procedure(
        "sp_apply_job",
        (test_job, candidate_user["candidate_id"], candidate_user["resume_id"], "Cover letter"),
        out_param_names=("p_application_id",),
        config=TestingConfig,
    )
    app_id = out["p_application_id"]
    tracker.application_ids.append(app_id)

    app_row = execute_query(
        "SELECT current_status, match_score FROM applications WHERE application_id = %s;",
        (app_id,),
        fetch="one",
        config=TestingConfig,
    )
    assert app_row["current_status"] == "APPLIED"
    assert 0.0 <= float(app_row["match_score"]) <= 100.0

    # Duplicate application rejected
    with pytest.raises(DatabaseSecurityError) as dup_exc:
        execute_procedure(
            "sp_apply_job",
            (test_job, candidate_user["candidate_id"], candidate_user["resume_id"], "Second try"),
            out_param_names=("p_application_id",),
            config=TestingConfig,
        )
    assert "already applied" in dup_exc.value.message

    # Invalid resume ownership rejected
    with pytest.raises(DatabaseSecurityError) as res_exc:
        execute_procedure(
            "sp_apply_job",
            (test_job, second_candidate_user["candidate_id"], candidate_user["resume_id"], "Stolen resume"),
            out_param_names=("p_application_id",),
            config=TestingConfig,
        )
    assert "Resume does not belong" in res_exc.value.message

    # Inactive job rejected
    closed_job = _create_job(tracker, recruiter_user["recruiter_id"], status="CLOSED")
    with pytest.raises(DatabaseSecurityError) as closed_exc:
        execute_procedure(
            "sp_apply_job",
            (closed_job, candidate_user["candidate_id"], candidate_user["resume_id"], "Closed"),
            out_param_names=("p_application_id",),
            config=TestingConfig,
        )
    assert "not accepting applications" in closed_exc.value.message

    # Expired job rejected
    expired_job = _create_job(tracker, recruiter_user["recruiter_id"], status="ACTIVE", deadline="2020-01-01")
    with pytest.raises(DatabaseSecurityError) as exp_exc:
        execute_procedure(
            "sp_apply_job",
            (expired_job, candidate_user["candidate_id"], candidate_user["resume_id"], "Expired"),
            out_param_names=("p_application_id",),
            config=TestingConfig,
        )
    assert "deadline" in exp_exc.value.message.lower()


def test_sp_update_application_status_and_audit_trail(recruiter_user, test_application):
    """Test sp_update_application_status transitions, history logging, and invalid state rejection."""
    execute_procedure(
        "sp_update_application_status",
        (test_application, "SHORTLISTED", recruiter_user["user_id"], "Passed initial screen"),
        config=TestingConfig,
    )

    history = execute_query(
        """
        SELECT old_status, new_status, changed_by_user_id, change_notes
        FROM application_status_history
        WHERE application_id = %s
        ORDER BY history_id ASC;
        """,
        (test_application,),
        fetch="all",
        config=TestingConfig,
    )
    assert len(history) == 2
    assert history[0]["old_status"] is None and history[0]["new_status"] == "APPLIED"
    assert history[1]["old_status"] == "APPLIED" and history[1]["new_status"] == "SHORTLISTED"
    assert history[1]["changed_by_user_id"] == recruiter_user["user_id"]

    # Invalid ENUM value rejected
    with pytest.raises(DatabaseSecurityError):
        execute_procedure(
            "sp_update_application_status",
            (test_application, "INVALID_ENUM", recruiter_user["user_id"], "Bad"),
            config=TestingConfig,
        )


def test_sp_schedule_interview_conflicts_and_boundaries(
    tracker, recruiter_user, second_candidate_user, test_job, test_application
):
    """Test sp_schedule_interview: valid, invalid app state, overlap, different interviewer, exact boundary & duration."""
    # Second application for second candidate on same job
    out2 = execute_procedure(
        "sp_apply_job",
        (test_job, second_candidate_user["candidate_id"], second_candidate_user["resume_id"], "App 2"),
        out_param_names=("p_application_id",),
        config=TestingConfig,
    )
    app2_id = out2["p_application_id"]
    tracker.application_ids.append(app2_id)

    # Valid interview 10:00 - 11:00 with Interviewer X
    int1 = execute_procedure(
        "sp_schedule_interview",
        (test_application, "Interviewer X", 1, "TECHNICAL", "2027-06-15 10:00:00", 60, "https://meet.example.com/1", "Online"),
        out_param_names=("p_interview_id",),
        config=TestingConfig,
    )
    tracker.interview_ids.append(int1["p_interview_id"])

    # Application automatically advances to INTERVIEW_SCHEDULED
    app_row = execute_query(
        "SELECT current_status FROM applications WHERE application_id = %s;",
        (test_application,),
        fetch="one",
        config=TestingConfig,
    )
    assert app_row["current_status"] == "INTERVIEW_SCHEDULED"

    # Overlapping same interviewer (10:30 - 11:30) -> rejected
    with pytest.raises(DatabaseSecurityError) as clash_exc:
        execute_procedure(
            "sp_schedule_interview",
            (app2_id, "Interviewer X", 1, "TECHNICAL", "2027-06-15 10:30:00", 60, "https://meet.example.com/2", "Online"),
            out_param_names=("p_interview_id",),
            config=TestingConfig,
        )
    assert "Conflict" in clash_exc.value.message

    # Overlapping different interviewer (10:30 - 11:30) -> allowed
    int2 = execute_procedure(
        "sp_schedule_interview",
        (app2_id, "Interviewer Y", 1, "TECHNICAL", "2027-06-15 10:30:00", 60, "https://meet.example.com/3", "Online"),
        out_param_names=("p_interview_id",),
        config=TestingConfig,
    )
    tracker.interview_ids.append(int2["p_interview_id"])

    # Exact end/start boundary (11:00 - 12:00 with Interviewer X) -> allowed
    int3 = execute_procedure(
        "sp_schedule_interview",
        (app2_id, "Interviewer X", 2, "HR", "2027-06-15 11:00:00", 60, "https://meet.example.com/4", "Online"),
        out_param_names=("p_interview_id",),
        config=TestingConfig,
    )
    tracker.interview_ids.append(int3["p_interview_id"])

    # Invalid duration (0) -> rejected
    with pytest.raises(DatabaseSecurityError):
        execute_procedure(
            "sp_schedule_interview",
            (app2_id, "Interviewer Z", 1, "HR", "2027-06-16 09:00:00", 0, "", "Online"),
            out_param_names=("p_interview_id",),
            config=TestingConfig,
        )

    # Reject application then attempt interview -> rejected
    execute_procedure(
        "sp_update_application_status",
        (app2_id, "REJECTED", recruiter_user["user_id"], "Not moving forward"),
        config=TestingConfig,
    )
    with pytest.raises(DatabaseSecurityError):
        execute_procedure(
            "sp_schedule_interview",
            (app2_id, "Interviewer Z", 3, "FINAL", "2027-06-17 09:00:00", 60, "", "Online"),
            out_param_names=("p_interview_id",),
            config=TestingConfig,
        )

