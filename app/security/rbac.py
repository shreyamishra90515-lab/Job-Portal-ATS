"""
Job Portal and Application Tracking System (ATS)
Role-Based Access Control (RBAC) & Object-Level Authorization
Phase 4: Permission Enforcement, Insecure Direct Object Reference (IDOR) Defense
"""

from functools import wraps
from flask import session, jsonify, abort, request
from app.db import execute_query


def login_required(view_func):
    """
    Ensure the request originates from an active authenticated session.
    Returns 401 Unauthorized if no active user session exists.
    """

    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            abort(401, description="Authentication required. Please log in.")
        return view_func(*args, **kwargs)

    return decorated_view


def role_required(*allowed_roles):
    """
    Enforce role-based access control.
    Authoritative role is retrieved strictly from the database-backed session,
    never trusted from client-supplied request parameters, body, or headers.
    Returns 403 Forbidden on authorization failure.
    """

    def decorator(view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required."}), 401
                abort(401, description="Authentication required.")

            user_role = session.get("role")
            if user_role not in allowed_roles:
                if request.is_json or request.path.startswith("/api/"):
                    return (
                        jsonify(
                            {
                                "error": f"Access forbidden. Required role(s): {', '.join(allowed_roles)}."
                            }
                        ),
                        403,
                    )
                abort(
                    403,
                    description=f"Access forbidden. Required role(s): {', '.join(allowed_roles)}.",
                )

            return view_func(*args, **kwargs)

        return decorated_view

    return decorator


# Alias supporting plural naming convention
roles_required = role_required


# -----------------------------------------------------------------------------
# Object-Level Authorization Checks (Defense Against IDOR)
# -----------------------------------------------------------------------------


def check_job_ownership(job_id: int, current_user: dict, config=None) -> bool:
    """
    Verify if the authenticated user has authorization to manage a job requisition.
    - ADMIN: Granted access.
    - RECRUITER: Granted access ONLY IF jobs.recruiter_id matches current_user['profile_id'].
    - CANDIDATE / Others: Denied.
    """
    if not current_user or "role" not in current_user:
        return False

    if current_user["role"] == "ADMIN":
        return True

    if current_user["role"] == "RECRUITER":
        recruiter_id = current_user.get("profile_id")
        if not recruiter_id:
            return False
        row = execute_query(
            "SELECT recruiter_id FROM jobs WHERE job_id = %s;",
            (job_id,),
            fetch="one",
            config=config,
        )
        return bool(row and row["recruiter_id"] == recruiter_id)

    return False


def check_application_ownership(application_id: int, current_user: dict, config=None) -> bool:
    """
    Verify if the authenticated user has authorization to access an application.
    - ADMIN: Granted access.
    - CANDIDATE: Granted access ONLY IF application.candidate_id == profile_id.
    - RECRUITER: Granted access ONLY IF job.recruiter_id == profile_id.
    """
    if not current_user or "role" not in current_user:
        return False

    if current_user["role"] == "ADMIN":
        return True

    row = execute_query(
        """
        SELECT a.candidate_id, j.recruiter_id
        FROM applications a
        INNER JOIN jobs j ON a.job_id = j.job_id
        WHERE a.application_id = %s;
        """,
        (application_id,),
        fetch="one",
        config=config,
    )
    if not row:
        return False

    if current_user["role"] == "CANDIDATE":
        return row["candidate_id"] == current_user.get("profile_id")

    if current_user["role"] == "RECRUITER":
        return row["recruiter_id"] == current_user.get("profile_id")

    return False


def check_resume_ownership(resume_id: int, current_user: dict, config=None) -> bool:
    """
    Verify if the authenticated user owns (or administers) the specified resume document.
    - ADMIN: Granted access.
    - CANDIDATE: Granted access ONLY IF resume.candidate_id == profile_id.
    - RECRUITER: Denied direct arbitrary ownership access.
    """
    if not current_user or "role" not in current_user:
        return False

    if current_user["role"] == "ADMIN":
        return True

    if current_user["role"] == "CANDIDATE":
        cand_id = current_user.get("profile_id")
        row = execute_query(
            "SELECT candidate_id FROM resumes WHERE resume_id = %s;",
            (resume_id,),
            fetch="one",
            config=config,
        )
        return bool(row and row["candidate_id"] == cand_id)

    return False


def check_interview_access(interview_id: int, current_user: dict, config=None) -> bool:
    """
    Verify if the authenticated user has legitimate access to an interview record.
    - ADMIN: Granted access.
    - CANDIDATE: Granted access ONLY if interview belongs to their application.
    - RECRUITER: Granted access ONLY if interview belongs to a job they manage.
    """
    if not current_user or "role" not in current_user:
        return False

    if current_user["role"] == "ADMIN":
        return True

    row = execute_query(
        """
        SELECT a.candidate_id, j.recruiter_id
        FROM interviews i
        INNER JOIN applications a ON i.application_id = a.application_id
        INNER JOIN jobs j ON a.job_id = j.job_id
        WHERE i.interview_id = %s;
        """,
        (interview_id,),
        fetch="one",
        config=config,
    )
    if not row:
        return False

    if current_user["role"] == "CANDIDATE":
        return row["candidate_id"] == current_user.get("profile_id")

    if current_user["role"] == "RECRUITER":
        return row["recruiter_id"] == current_user.get("profile_id")

    return False


def check_candidate_profile_access(
    candidate_id: int, current_user: dict, write: bool = False, config=None
) -> bool:
    """
    Verify access to a candidate profile record.
    - ADMIN: Allowed read/write.
    - CANDIDATE: Allowed read/write ONLY for own candidate_id.
    - RECRUITER: Never allowed write; read allowed ONLY if candidate applied to one of recruiter's jobs.
    """
    if not current_user or "role" not in current_user:
        return False

    role = current_user["role"]
    if role == "ADMIN":
        return True

    if role == "CANDIDATE":
        return current_user.get("profile_id") == candidate_id

    if role == "RECRUITER" and not write:
        recruiter_id = current_user.get("profile_id")
        if not recruiter_id:
            return False
        row = execute_query(
            """
            SELECT 1 AS authorized
            FROM applications a
            INNER JOIN jobs j ON a.job_id = j.job_id
            WHERE a.candidate_id = %s AND j.recruiter_id = %s
            LIMIT 1;
            """,
            (candidate_id, recruiter_id),
            fetch="one",
            config=config,
        )
        return bool(row)

    return False
