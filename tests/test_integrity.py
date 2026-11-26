"""
Database Integrity & Phase 1/Phase 2 Invariant Tests
Phase 4: Direct DDL/Trigger Constraint Verification
"""

import pytest
import pymysql
from config import TestingConfig
from app.db import get_db_connection


def test_db_enforces_resume_ownership_composite_fk(db_conn, candidate_user, second_candidate_user, test_job):
    """DB-02: Composite FK fk_applications_resume_owner blocks applying with another candidate's resume."""
    cur = db_conn.cursor()
    try:
        with pytest.raises(pymysql.MySQLError):
            cur.execute(
                """
                INSERT INTO applications (job_id, candidate_id, resume_id, current_status, match_score)
                VALUES (%s, %s, %s, 'APPLIED', 50.00);
                """,
                (test_job, candidate_user["candidate_id"], second_candidate_user["resume_id"]),
            )
        db_conn.rollback()
    finally:
        cur.close()


def test_db_enforces_unique_job_candidate_application(db_conn, candidate_user, test_job, test_application):
    """DB-01: Unique key uq_job_candidate rejects duplicate direct INSERTs."""
    cur = db_conn.cursor()
    try:
        with pytest.raises(pymysql.IntegrityError):
            cur.execute(
                """
                INSERT INTO applications (job_id, candidate_id, resume_id, current_status, match_score)
                VALUES (%s, %s, %s, 'APPLIED', 75.00);
                """,
                (test_job, candidate_user["candidate_id"], candidate_user["resume_id"]),
            )
        db_conn.rollback()
    finally:
        cur.close()


def test_db_enforces_match_score_check_constraint(db_conn, candidate_user, test_job):
    """CHECK constraint chk_app_match_score rejects scores < 0.00 or > 100.00."""
    cur = db_conn.cursor()
    try:
        for invalid_score in (-0.01, 100.01):
            with pytest.raises(pymysql.MySQLError):
                cur.execute(
                    """
                    INSERT INTO applications (job_id, candidate_id, resume_id, current_status, match_score)
                    VALUES (%s, %s, %s, 'APPLIED', %s);
                    """,
                    (test_job, candidate_user["candidate_id"], candidate_user["resume_id"], invalid_score),
                )
            db_conn.rollback()
    finally:
        cur.close()


def test_db_rejects_invalid_application_status_enum(db_conn, test_application):
    """Invalid ENUM value for current_status is rejected by MySQL."""
    cur = db_conn.cursor()
    try:
        with pytest.raises(pymysql.MySQLError):
            cur.execute(
                "UPDATE applications SET current_status = 'FAKE_STAGE' WHERE application_id = %s;",
                (test_application,),
            )
        db_conn.rollback()
    finally:
        cur.close()


def test_trigger_logs_only_actual_status_transitions(db_conn, test_application):
    """trg_applications_after_update logs only when current_status actually changes."""
    cur = db_conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM application_status_history WHERE application_id = %s;",
            (test_application,),
        )
        before = cur.fetchone()["cnt"]

        # Non-status update (cover_letter) must NOT create a duplicate history row
        cur.execute(
            "UPDATE applications SET cover_letter = 'Edited cover letter' WHERE application_id = %s;",
            (test_application,),
        )
        db_conn.commit()

        cur.execute(
            "SELECT COUNT(*) AS cnt FROM application_status_history WHERE application_id = %s;",
            (test_application,),
        )
        after_non_status = cur.fetchone()["cnt"]
        assert after_non_status == before

        # Status transition MUST create history row
        cur.execute(
            "UPDATE applications SET current_status = 'UNDER_REVIEW' WHERE application_id = %s;",
            (test_application,),
        )
        db_conn.commit()

        cur.execute(
            "SELECT COUNT(*) AS cnt FROM application_status_history WHERE application_id = %s;",
            (test_application,),
        )
        assert cur.fetchone()["cnt"] == before + 1
    finally:
        cur.close()


def test_interview_trigger_conflict_and_cancelled_exemption(
    tracker, candidate_user, second_candidate_user, test_job, test_application
):
    """DB-03: Trigger rejects overlapping active interviews, but ignores CANCELLED interviews and allows exact boundary."""
    conn = get_db_connection(TestingConfig)
    cur = conn.cursor()
    try:
        # Insert cancelled interview at 09:00 - 10:00
        cur.execute(
            """
            INSERT INTO interviews (application_id, interviewer_name, round_number, round_type, scheduled_at, duration_minutes, status)
            VALUES (%s, 'Trigger Reviewer', 1, 'SCREENING', '2027-08-01 09:00:00', 60, 'CANCELLED');
            """,
            (test_application,),
        )
        cancelled_id = cur.lastrowid
        tracker.interview_ids.append(cancelled_id)

        # Scheduling active interview in same slot (09:00 - 10:00) succeeds because prior is CANCELLED
        cur.execute(
            """
            INSERT INTO interviews (application_id, interviewer_name, round_number, round_type, scheduled_at, duration_minutes, status)
            VALUES (%s, 'Trigger Reviewer', 2, 'TECHNICAL', '2027-08-01 09:00:00', 60, 'SCHEDULED');
            """,
            (test_application,),
        )
        active_id = cur.lastrowid
        tracker.interview_ids.append(active_id)
        conn.commit()

        # Overlapping active interview (09:30 - 10:30) rejected by trg_interviews_before_insert
        with pytest.raises(pymysql.MySQLError):
            cur.execute(
                """
                INSERT INTO interviews (application_id, interviewer_name, round_number, round_type, scheduled_at, duration_minutes, status)
                VALUES (%s, 'Trigger Reviewer', 3, 'HR', '2027-08-01 09:30:00', 60, 'SCHEDULED');
                """,
                (test_application,),
            )
        conn.rollback()

        # Exact boundary (10:00 - 11:00) allowed
        cur.execute(
            """
            INSERT INTO interviews (application_id, interviewer_name, round_number, round_type, scheduled_at, duration_minutes, status)
            VALUES (%s, 'Trigger Reviewer', 3, 'HR', '2027-08-01 10:00:00', 60, 'SCHEDULED');
            """,
            (test_application,),
        )
        boundary_id = cur.lastrowid
        tracker.interview_ids.append(boundary_id)
        conn.commit()
    finally:
        cur.close()
        conn.close()

