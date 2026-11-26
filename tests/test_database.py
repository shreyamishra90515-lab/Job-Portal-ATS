"""
Database Layer, Parameterized Query & Transaction Rollback Tests
Phase 4: Secure DB Access, ACID Commit/Rollback, Error Concealment & Phase 3 Views
"""

import pytest
from app.db import (
    DatabaseSecurityError,
    execute_query,
    execute_procedure,
    get_db_cursor,
)
from config import TestingConfig


def test_transaction_commit_and_rollback(tracker):
    """Verify get_db_cursor commits on success and rolls back atomically on error."""
    with pytest.raises(DatabaseSecurityError):
        with get_db_cursor(commit=True, config=TestingConfig) as cur:
            cur.execute(
                """
                INSERT INTO skills (skill_name, category)
                VALUES (%s, %s);
                """,
                ("Phase4RollbackSkill_Tmp", "Testing"),
            )
            # Trigger duplicate PK/UK or invalid SQL inside same transaction
            cur.execute(
                """
                INSERT INTO skills (skill_name, category)
                VALUES (%s, %s);
                """,
                ("Phase4RollbackSkill_Tmp", "Testing"),
            )

    # Confirm the first insert was rolled back cleanly
    row = execute_query(
        "SELECT skill_id FROM skills WHERE skill_name = %s;",
        ("Phase4RollbackSkill_Tmp",),
        fetch="one",
        config=TestingConfig,
    )
    assert row is None


def test_disallowed_stored_procedure_blocked():
    """Only whitelisted Phase 2 procedures may be called via execute_procedure."""
    with pytest.raises(DatabaseSecurityError):
        execute_procedure("sp_drop_everything", (), config=TestingConfig)


def test_raw_sql_errors_concealed():
    """Raw MySQL schema errors are sanitized and never leak table/column metadata."""
    with pytest.raises(DatabaseSecurityError) as exc_info:
        execute_query(
            "SELECT * FROM non_existent_table_xyz;",
            fetch="all",
            config=TestingConfig,
        )
    assert "non_existent_table_xyz" not in exc_info.value.message
    assert "Database operation could not be completed safely." == exc_info.value.message


def test_phase3_views_accessible():
    """All 8 Phase 3 reporting views return valid structured results."""
    views = (
        "vw_candidate_application_dashboard",
        "vw_recruiter_job_performance",
        "vw_application_funnel",
        "vw_interview_schedule",
        "vw_job_skill_requirements",
        "vw_candidate_skill_profile",
        "vw_job_application_statistics",
        "vw_candidate_application_statistics",
    )
    for view_name in views:
        rows = execute_query(f"SELECT * FROM {view_name} LIMIT 5;", fetch="all", config=TestingConfig)
        assert isinstance(rows, list)

