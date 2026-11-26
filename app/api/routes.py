"""
Job Portal and Application Tracking System (ATS)
Secure API & Controller Routes
Phase 4: RBAC, Input Validation, CSRF, and Stored Procedure Integration
"""

from flask import Blueprint, request, jsonify
from app.db import execute_query, execute_procedure, DatabaseSecurityError
from app.security.auth import (
    authenticate_user,
    login_user,
    logout_user,
    get_current_user,
    hash_password,
)
from app.security.rbac import (
    login_required,
    role_required,
    check_job_ownership,
    check_application_ownership,
    check_resume_ownership,
    check_interview_access,
    check_candidate_profile_access,
)
from app.security.validation import (
    ValidationError,
    validate_email,
    validate_positive_int,
    validate_enum,
    validate_url,
    validate_datetime,
    validate_pagination,
    sanitize_text,
    validate_registration_candidate,
    validate_registration_recruiter,
    validate_job_payload,
    validate_candidate_profile_update,
    validate_resume_payload,
    validate_recruiter_profile_update,
    validate_interview_update,
    validate_decimal_range,
    APPLICATION_STATUS_ENUMS,
    ROUND_TYPE_ENUMS,
    WORKPLACE_TYPE_ENUMS,
    EMPLOYMENT_TYPE_ENUMS,
    PROFICIENCY_ENUMS,
)
from app.security.csrf import generate_csrf_token

api_bp = Blueprint("api", __name__, url_prefix="/api")


# -----------------------------------------------------------------------------
# 1. Authentication & Session Endpoints
# -----------------------------------------------------------------------------


@api_bp.route("/auth/csrf-token", methods=["GET"])
def get_csrf():
    """Retrieve session-bound CSRF token for secure state-changing requests."""
    token = generate_csrf_token()
    return jsonify({"csrf_token": token}), 200


@api_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Authenticate user with email and password.
    Enforces server-side validation, Bcrypt verification, and session regeneration.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        clean_email = validate_email(email)
    except ValidationError as ve:
        return jsonify({"error": ve.message}), 400

    user_info = authenticate_user(clean_email, password)
    if not user_info:
        return jsonify({"error": "Invalid email or password."}), 401

    rotated_csrf = login_user(user_info)
    return (
        jsonify(
            {
                "message": "Login successful.",
                "user": user_info,
                "csrf_token": rotated_csrf,
            }
        ),
        200,
    )


@api_bp.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    """Terminate authenticated session."""
    logout_user()
    return jsonify({"message": "Successfully logged out."}), 200


@api_bp.route("/auth/me", methods=["GET"])
@login_required
def current_user():
    """Return currently authenticated user identity and role."""
    user = get_current_user()
    return jsonify({"user": user}), 200


@api_bp.route("/auth/register-candidate", methods=["POST"])
def register_candidate():
    """
    Register a new candidate by validating input, hashing password with Bcrypt,
    and invoking Phase 2 stored procedure sp_register_candidate.
    """
    raw_data = request.get_json(silent=True) or {}
    try:
        clean_data = validate_registration_candidate(raw_data)
    except ValidationError as ve:
        return jsonify({"error": ve.message, "field": ve.field}), 400

    hashed_pwd = hash_password(clean_data["password"])

    try:
        out_params = execute_procedure(
            "sp_register_candidate",
            (
                clean_data["email"],
                hashed_pwd,
                clean_data["first_name"],
                clean_data["last_name"],
                clean_data["phone"],
                clean_data["headline"],
                clean_data["summary"],
                clean_data["current_location"],
                clean_data["years_of_experience"],
                clean_data["highest_education"],
                clean_data["linkedin_url"],
                clean_data["portfolio_url"],
            ),
            out_param_names=("p_user_id", "p_candidate_id"),
        )
        return (
            jsonify(
                {
                    "message": "Candidate registered successfully.",
                    "user_id": out_params.get("p_user_id"),
                    "candidate_id": out_params.get("p_candidate_id"),
                }
            ),
            201,
        )
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


@api_bp.route("/auth/register-recruiter", methods=["POST"])
def register_recruiter():
    """
    Register a new corporate recruiter by validating input, hashing password with Bcrypt,
    and invoking Phase 2 stored procedure sp_register_recruiter.
    """
    raw_data = request.get_json(silent=True) or {}
    try:
        clean_data = validate_registration_recruiter(raw_data)
    except ValidationError as ve:
        return jsonify({"error": ve.message, "field": ve.field}), 400

    hashed_pwd = hash_password(clean_data["password"])

    try:
        out_params = execute_procedure(
            "sp_register_recruiter",
            (
                clean_data["email"],
                hashed_pwd,
                clean_data["first_name"],
                clean_data["last_name"],
                clean_data["phone"],
                clean_data["company_name"],
                clean_data["company_website"],
                clean_data["department"],
                clean_data["designation"],
                clean_data["office_location"],
            ),
            out_param_names=("p_user_id", "p_recruiter_id"),
        )
        return (
            jsonify(
                {
                    "message": "Recruiter registered successfully.",
                    "user_id": out_params.get("p_user_id"),
                    "recruiter_id": out_params.get("p_recruiter_id"),
                }
            ),
            201,
        )
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


# -----------------------------------------------------------------------------
# 2. Admin RBAC Endpoints (Strictly ADMIN Role)
# -----------------------------------------------------------------------------


@api_bp.route("/admin/dashboard", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_dashboard():
    """System-wide metrics reserved strictly for ADMIN role."""
    funnel = execute_query("SELECT * FROM vw_application_funnel ORDER BY stage_order ASC;", fetch="all")
    counts = execute_query(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM candidate_profiles) AS total_candidates,
            (SELECT COUNT(*) FROM recruiter_profiles) AS total_recruiters,
            (SELECT COUNT(*) FROM jobs) AS total_jobs,
            (SELECT COUNT(*) FROM applications) AS total_applications,
            (SELECT COUNT(*) FROM interviews) AS total_interviews;
        """,
        fetch="one",
    )
    return jsonify({"role": "ADMIN", "summary": counts, "application_funnel": funnel}), 200


@api_bp.route("/admin/users", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_users():
    """List users for administrative inspection (never exposing password_hash)."""
    page, per_page = validate_pagination(request.args.get("page"), request.args.get("per_page"))
    offset = (page - 1) * per_page
    users = execute_query(
        """
        SELECT u.user_id, u.email, u.first_name, u.last_name, u.phone,
               u.is_active, r.role_name, u.created_at
        FROM users u
        INNER JOIN roles r ON u.role_id = r.role_id
        ORDER BY u.user_id ASC
        LIMIT %s OFFSET %s;
        """,
        (per_page, offset),
        fetch="all",
    )
    return jsonify({"users": users, "page": page, "per_page": per_page}), 200


@api_bp.route("/admin/applications", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_applications():
    """Inspect all applications system-wide."""
    apps = execute_query(
        "SELECT * FROM vw_candidate_application_dashboard ORDER BY applied_at DESC;",
        fetch="all",
    )
    return jsonify({"applications": apps, "count": len(apps)}), 200


@api_bp.route("/admin/interviews", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_interviews():
    """Inspect all interviews system-wide."""
    interviews = execute_query(
        "SELECT * FROM vw_interview_schedule ORDER BY scheduled_at DESC;",
        fetch="all",
    )
    return jsonify({"interviews": interviews, "count": len(interviews)}), 200


@api_bp.route("/admin/audit-history", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_audit_history():
    """Inspect application status audit trail."""
    history = execute_query(
        """
        SELECT h.history_id, h.application_id, h.old_status, h.new_status,
               h.changed_by_user_id, h.change_notes, h.changed_at
        FROM application_status_history h
        ORDER BY h.changed_at DESC, h.history_id DESC
        LIMIT 100;
        """,
        fetch="all",
    )
    return jsonify({"audit_history": history, "count": len(history)}), 200


@api_bp.route("/admin/reports", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_reports():
    """Administrative reporting views from Phase 3."""
    job_stats = execute_query(
        "SELECT * FROM vw_job_application_statistics ORDER BY total_applications DESC;",
        fetch="all",
    )
    cand_stats = execute_query(
        "SELECT * FROM vw_candidate_application_statistics ORDER BY total_applications DESC;",
        fetch="all",
    )
    return jsonify({"job_statistics": job_stats, "candidate_statistics": cand_stats}), 200


# -----------------------------------------------------------------------------
# 3. Recruiter Endpoints (Scoped to Authenticated Recruiter or ADMIN)
# -----------------------------------------------------------------------------


@api_bp.route("/recruiter/jobs", methods=["GET"])
@login_required
@role_required("RECRUITER", "ADMIN")
def recruiter_jobs():
    """Retrieve jobs published by the authenticated recruiter."""
    user = get_current_user()
    if user["role"] == "ADMIN":
        jobs = execute_query("SELECT * FROM jobs ORDER BY created_at DESC;", fetch="all")
    else:
        jobs = execute_query(
            "SELECT * FROM jobs WHERE recruiter_id = %s ORDER BY created_at DESC;",
            (user["profile_id"],),
            fetch="all",
        )
    return jsonify({"jobs": jobs}), 200


@api_bp.route("/recruiter/interviews", methods=["GET"])
@login_required
@role_required("RECRUITER", "ADMIN")
def recruiter_interviews():
    """Retrieve interviews associated with the authenticated recruiter's jobs."""
    user = get_current_user()
    if user["role"] == "ADMIN":
        rows = execute_query("SELECT * FROM vw_interview_schedule ORDER BY scheduled_at DESC;", fetch="all")
    else:
        rows = execute_query(
            """
            SELECT v.*
            FROM vw_interview_schedule v
            INNER JOIN jobs j ON v.job_id = j.job_id
            WHERE j.recruiter_id = %s
            ORDER BY v.scheduled_at DESC;
            """,
            (user["profile_id"],),
            fetch="all",
        )
    return jsonify({"interviews": rows}), 200


@api_bp.route("/recruiter/statistics", methods=["GET"])
@login_required
@role_required("RECRUITER", "ADMIN")
def recruiter_statistics():
    """Retrieve recruitment analytics scoped to the authenticated recruiter's jobs."""
    user = get_current_user()
    if user["role"] == "ADMIN":
        stats = execute_query(
            "SELECT * FROM vw_recruiter_job_performance ORDER BY job_id DESC;",
            fetch="all",
        )
    else:
        stats = execute_query(
            "SELECT * FROM vw_recruiter_job_performance WHERE recruiter_id = %s ORDER BY job_id DESC;",
            (user["profile_id"],),
            fetch="all",
        )
    return jsonify({"statistics": stats}), 200


# -----------------------------------------------------------------------------
# 4. Candidate Endpoints (Scoped to Authenticated Candidate)
# -----------------------------------------------------------------------------


@api_bp.route("/candidate/profile", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def get_own_candidate_profile():
    """Retrieve the authenticated candidate's own profile."""
    user = get_current_user()
    row = execute_query(
        """
        SELECT cp.candidate_id, u.user_id, u.email, u.first_name, u.last_name, u.phone,
               cp.headline, cp.summary, cp.current_location, cp.years_of_experience,
               cp.highest_education, cp.linkedin_url, cp.portfolio_url
        FROM candidate_profiles cp
        INNER JOIN users u ON cp.user_id = u.user_id
        WHERE cp.candidate_id = %s;
        """,
        (user["profile_id"],),
        fetch="one",
    )
    if not row:
        return jsonify({"error": "Candidate profile not found."}), 404
    return jsonify({"profile": row}), 200


@api_bp.route("/candidate/profile", methods=["PUT"])
@login_required
@role_required("CANDIDATE")
def update_own_candidate_profile():
    """Update the authenticated candidate's own profile."""
    user = get_current_user()
    raw_data = request.get_json(silent=True) or {}
    clean_data = validate_candidate_profile_update(raw_data)

    if "phone" in clean_data:
        execute_query(
            "UPDATE users SET phone = %s WHERE user_id = %s;",
            (clean_data.pop("phone"), user["user_id"]),
            commit=True,
        )

    if clean_data:
        set_clause = ", ".join(f"{col} = %s" for col in clean_data.keys())
        params = list(clean_data.values()) + [user["profile_id"]]
        execute_query(
            f"UPDATE candidate_profiles SET {set_clause} WHERE candidate_id = %s;",
            params,
            commit=True,
        )

    return jsonify({"message": "Candidate profile updated successfully."}), 200


@api_bp.route("/candidates/<int:candidate_id>", methods=["GET"])
@login_required
def get_candidate_profile(candidate_id: int):
    """
    Retrieve a candidate profile by ID with object-level authorization.
    - Candidate can only view own profile (never another candidate's private data).
    - Recruiter can only view candidates who applied to their jobs.
    - Admin can view any candidate profile.
    """
    user = get_current_user()
    if not check_candidate_profile_access(candidate_id, user, write=False):
        return (
            jsonify({"error": "Forbidden: You do not have permission to view this candidate profile."}),
            403,
        )

    row = execute_query(
        """
        SELECT cp.candidate_id, u.email, u.first_name, u.last_name, u.phone,
               cp.headline, cp.summary, cp.current_location, cp.years_of_experience,
               cp.highest_education, cp.linkedin_url, cp.portfolio_url
        FROM candidate_profiles cp
        INNER JOIN users u ON cp.user_id = u.user_id
        WHERE cp.candidate_id = %s;
        """,
        (candidate_id,),
        fetch="one",
    )
    if not row:
        return jsonify({"error": "Candidate profile not found."}), 404
    return jsonify({"profile": row}), 200


@api_bp.route("/candidates/<int:candidate_id>", methods=["PUT"])
@login_required
def update_candidate_profile_by_id(candidate_id: int):
    """Update a candidate profile by ID enforcing strict ownership."""
    user = get_current_user()
    if not check_candidate_profile_access(candidate_id, user, write=True):
        return (
            jsonify({"error": "Forbidden: You are not authorized to modify this candidate profile."}),
            403,
        )

    raw_data = request.get_json(silent=True) or {}
    clean_data = validate_candidate_profile_update(raw_data)

    if "phone" in clean_data:
        phone_val = clean_data.pop("phone")
        execute_query(
            """
            UPDATE users u
            INNER JOIN candidate_profiles cp ON cp.user_id = u.user_id
            SET u.phone = %s
            WHERE cp.candidate_id = %s;
            """,
            (phone_val, candidate_id),
            commit=True,
        )

    if clean_data:
        set_clause = ", ".join(f"{col} = %s" for col in clean_data.keys())
        params = list(clean_data.values()) + [candidate_id]
        execute_query(
            f"UPDATE candidate_profiles SET {set_clause} WHERE candidate_id = %s;",
            params,
            commit=True,
        )

    return jsonify({"message": "Candidate profile updated successfully."}), 200


@api_bp.route("/candidate/resumes", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def list_own_resumes():
    """List resumes owned by the authenticated candidate."""
    user = get_current_user()
    resumes = execute_query(
        """
        SELECT resume_id, candidate_id, file_name, file_size_kb, is_primary, uploaded_at
        FROM resumes
        WHERE candidate_id = %s
        ORDER BY is_primary DESC, uploaded_at DESC;
        """,
        (user["profile_id"],),
        fetch="all",
    )
    return jsonify({"resumes": resumes}), 200


@api_bp.route("/candidate/resumes", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def create_own_resume():
    """Register a resume metadata entry for the authenticated candidate."""
    user = get_current_user()
    raw_data = request.get_json(silent=True) or {}
    clean_data = validate_resume_payload(raw_data)

    resume_id = execute_query(
        """
        INSERT INTO resumes (candidate_id, file_name, file_path, file_size_kb, is_primary)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (
            user["profile_id"],
            clean_data["file_name"],
            clean_data["file_path"],
            clean_data["file_size_kb"],
            clean_data["is_primary"],
        ),
        fetch="lastrowid",
        commit=True,
    )
    return (
        jsonify({"message": "Resume added successfully.", "resume_id": resume_id}),
        201,
    )


@api_bp.route("/candidate/applications", methods=["GET"])
@login_required
@role_required("CANDIDATE", "ADMIN")
def candidate_applications():
    """Retrieve applications submitted by the authenticated candidate."""
    user = get_current_user()
    if user["role"] == "ADMIN":
        apps = execute_query(
            "SELECT * FROM vw_candidate_application_dashboard ORDER BY applied_at DESC;",
            fetch="all",
        )
    else:
        apps = execute_query(
            """
            SELECT * FROM vw_candidate_application_dashboard
            WHERE candidate_id = %s
            ORDER BY applied_at DESC;
            """,
            (user["profile_id"],),
            fetch="all",
        )
    return jsonify({"applications": apps}), 200


@api_bp.route("/candidate/interviews", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def candidate_interviews():
    """Retrieve interviews scheduled for the authenticated candidate."""
    user = get_current_user()
    interviews = execute_query(
        "SELECT * FROM vw_interview_schedule WHERE candidate_id = %s ORDER BY scheduled_at DESC;",
        (user["profile_id"],),
        fetch="all",
    )
    return jsonify({"interviews": interviews}), 200


# -----------------------------------------------------------------------------
# 5. Jobs & Object-Level Authorization (IDOR Protected) Routes
# -----------------------------------------------------------------------------


@api_bp.route("/jobs", methods=["GET"])
def list_jobs():
    """Browse active job openings with validated pagination."""
    page, per_page = validate_pagination(request.args.get("page"), request.args.get("per_page"))
    offset = (page - 1) * per_page
    jobs = execute_query(
        """
        SELECT job_id, recruiter_id, title, location, employment_type, workplace_type,
               min_experience_years, salary_min, salary_max, status, deadline_date, created_at
        FROM jobs
        WHERE status = 'ACTIVE'
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s;
        """,
        (per_page, offset),
        fetch="all",
    )
    return jsonify({"jobs": jobs, "page": page, "per_page": per_page, "count": len(jobs)}), 200


@api_bp.route("/jobs", methods=["POST"])
@login_required
@role_required("RECRUITER", "ADMIN")
def create_job():
    """Create a new job requisition owned by the authenticated recruiter."""
    user = get_current_user()
    raw_data = request.get_json(silent=True) or {}
    clean_data = validate_job_payload(raw_data, partial=False)

    if user["role"] == "ADMIN":
        recruiter_id = validate_positive_int(raw_data.get("recruiter_id"), "recruiter_id")
    else:
        recruiter_id = user.get("profile_id")
        if not recruiter_id:
            return jsonify({"error": "Recruiter profile not found."}), 403

    job_id = execute_query(
        """
        INSERT INTO jobs (
            recruiter_id, title, description, employment_type, workplace_type,
            location, min_experience_years, salary_min, salary_max, status, deadline_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            recruiter_id,
            clean_data["title"],
            clean_data["description"],
            clean_data["employment_type"],
            clean_data["workplace_type"],
            clean_data["location"],
            clean_data["min_experience_years"],
            clean_data["salary_min"],
            clean_data["salary_max"],
            clean_data["status"],
            clean_data["deadline_date"],
        ),
        fetch="lastrowid",
        commit=True,
    )
    return jsonify({"message": "Job created successfully.", "job_id": job_id}), 201


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id: int):
    """Retrieve details for a specific job requisition (DRAFT restricted to owner/admin)."""
    job = execute_query("SELECT * FROM jobs WHERE job_id = %s;", (job_id,), fetch="one")
    if not job:
        return jsonify({"error": "Job not found."}), 404

    if job["status"] == "DRAFT":
        user = get_current_user()
        if not user or not check_job_ownership(job_id, user):
            return jsonify({"error": "Forbidden: Draft job is restricted."}), 403

    return jsonify({"job": job}), 200


@api_bp.route("/jobs/<int:job_id>", methods=["PUT"])
@login_required
@role_required("RECRUITER", "ADMIN")
def update_job(job_id: int):
    """
    Modify a job posting.
    Enforces object-level ownership: recruiter cannot modify another recruiter's job.
    """
    user = get_current_user()
    if not check_job_ownership(job_id, user):
        return (
            jsonify({"error": "Forbidden: You are not authorized to modify this job requisition."}),
            403,
        )

    data = request.get_json(silent=True) or {}
    clean_data = validate_job_payload(data, partial=True)

    set_clause = ", ".join(f"{col} = %s" for col in clean_data.keys())
    params = list(clean_data.values()) + [job_id]
    execute_query(f"UPDATE jobs SET {set_clause} WHERE job_id = %s;", params, commit=True)
    return jsonify({"message": "Job updated successfully.", "job_id": job_id}), 200


@api_bp.route("/jobs/<int:job_id>/applications", methods=["GET"])
@login_required
@role_required("RECRUITER", "ADMIN")
def get_job_applications(job_id: int):
    """View applicants for a specific job owned by the authenticated recruiter."""
    user = get_current_user()
    if not check_job_ownership(job_id, user):
        return (
            jsonify({"error": "Forbidden: You are not authorized to view applicants for this job."}),
            403,
        )

    apps = execute_query(
        """
        SELECT * FROM vw_candidate_application_dashboard
        WHERE job_id = %s
        ORDER BY match_score DESC, applied_at DESC;
        """,
        (job_id,),
        fetch="all",
    )
    return jsonify({"applications": apps, "count": len(apps)}), 200


@api_bp.route("/applications/<int:app_id>", methods=["GET"])
@login_required
def get_application(app_id: int):
    """
    Retrieve application details with object-level authorization.
    """
    user = get_current_user()
    if not check_application_ownership(app_id, user):
        return (
            jsonify({"error": "Forbidden: You do not have permission to view this application."}),
            403,
        )

    app_data = execute_query(
        "SELECT * FROM vw_candidate_application_dashboard WHERE application_id = %s;",
        (app_id,),
        fetch="one",
    )
    if not app_data:
        return jsonify({"error": "Application not found."}), 404
    return jsonify({"application": app_data}), 200


@api_bp.route("/applications/<int:app_id>/history", methods=["GET"])
@login_required
def get_application_history(app_id: int):
    """Retrieve status audit trail for an application with object-level authorization."""
    user = get_current_user()
    if not check_application_ownership(app_id, user):
        return (
            jsonify({"error": "Forbidden: You do not have permission to view this application history."}),
            403,
        )

    history = execute_query(
        """
        SELECT history_id, application_id, old_status, new_status,
               changed_by_user_id, change_notes, changed_at
        FROM application_status_history
        WHERE application_id = %s
        ORDER BY changed_at ASC, history_id ASC;
        """,
        (app_id,),
        fetch="all",
    )
    return jsonify({"history": history}), 200


@api_bp.route("/resumes/<int:resume_id>", methods=["GET"])
@login_required
def get_resume(resume_id: int):
    """
    Retrieve resume metadata enforcing candidate resume ownership.
    """
    user = get_current_user()
    if not check_resume_ownership(resume_id, user):
        return (
            jsonify({"error": "Forbidden: You do not have permission to access this resume."}),
            403,
        )

    resume = execute_query(
        "SELECT resume_id, candidate_id, file_name, file_size_kb, is_primary, uploaded_at FROM resumes WHERE resume_id = %s;",
        (resume_id,),
        fetch="one",
    )
    if not resume:
        return jsonify({"error": "Resume not found."}), 404
    return jsonify({"resume": resume}), 200


@api_bp.route("/interviews/<int:interview_id>", methods=["GET"])
@login_required
def get_interview(interview_id: int):
    """
    Retrieve interview details enforcing interview access boundaries.
    """
    user = get_current_user()
    if not check_interview_access(interview_id, user):
        return (
            jsonify({"error": "Forbidden: You do not have permission to view this interview."}),
            403,
        )

    interview = execute_query(
        "SELECT * FROM vw_interview_schedule WHERE interview_id = %s;",
        (interview_id,),
        fetch="one",
    )
    if not interview:
        return jsonify({"error": "Interview not found."}), 404
    return jsonify({"interview": interview}), 200


# -----------------------------------------------------------------------------
# 6. Procedure-Invoking Business Workflow Routes
# -----------------------------------------------------------------------------


@api_bp.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def apply_job(job_id: int):
    """
    Candidate job submission invoking Phase 2 stored procedure sp_apply_job.
    """
    user = get_current_user()
    candidate_id = user["profile_id"]
    data = request.get_json(silent=True) or {}

    try:
        resume_id = validate_positive_int(data.get("resume_id"), "resume_id")
    except ValidationError as ve:
        return jsonify({"error": ve.message}), 400

    cover_letter = sanitize_text(data.get("cover_letter", ""), max_length=2000, field_name="cover_letter")

    try:
        out_params = execute_procedure(
            "sp_apply_job",
            (job_id, candidate_id, resume_id, cover_letter),
            out_param_names=("p_application_id",),
        )
        return (
            jsonify(
                {
                    "message": "Application submitted successfully.",
                    "application_id": out_params.get("p_application_id"),
                }
            ),
            201,
        )
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


@api_bp.route("/applications/<int:app_id>/status", methods=["POST"])
@login_required
@role_required("RECRUITER", "ADMIN")
def update_application_status(app_id: int):
    """
    Update application status invoking Phase 2 stored procedure sp_update_application_status.
    """
    user = get_current_user()
    if not check_application_ownership(app_id, user):
        return jsonify({"error": "Forbidden: You are not authorized to update this application."}), 403

    data = request.get_json(silent=True) or {}
    try:
        new_status = validate_enum(data.get("status"), APPLICATION_STATUS_ENUMS, "status")
    except ValidationError as ve:
        return jsonify({"error": ve.message}), 400

    change_notes = sanitize_text(data.get("change_notes", ""), max_length=500, field_name="change_notes")

    try:
        execute_procedure(
            "sp_update_application_status",
            (app_id, new_status, user["user_id"], change_notes),
        )
        return jsonify({"message": f"Application status updated to {new_status}."}), 200
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


@api_bp.route("/interviews/schedule", methods=["POST"])
@login_required
@role_required("RECRUITER", "ADMIN")
def schedule_interview():
    """
    Schedule an interview invoking Phase 2 stored procedure sp_schedule_interview.
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    try:
        app_id = validate_positive_int(data.get("application_id"), "application_id")
        interviewer_name = sanitize_text(
            data.get("interviewer_name"), max_length=150, field_name="interviewer_name", required=True
        )
        round_number = validate_positive_int(data.get("round_number", 1), "round_number")
        round_type = validate_enum(data.get("round_type", "TECHNICAL"), ROUND_TYPE_ENUMS, "round_type")
        scheduled_at = validate_datetime(data.get("scheduled_at"), "scheduled_at", required=True)
        duration_minutes = validate_positive_int(data.get("duration_minutes", 60), "duration_minutes", max_val=480)
        meeting_link = validate_url(data.get("meeting_link"), field_name="meeting_link", max_length=500)
        location = sanitize_text(data.get("location", "Online"), max_length=150, field_name="location")
    except ValidationError as ve:
        return jsonify({"error": ve.message}), 400

    if not check_application_ownership(app_id, user):
        return (
            jsonify({"error": "Forbidden: You are not authorized to schedule interviews for this application."}),
            403,
        )

    try:
        out_params = execute_procedure(
            "sp_schedule_interview",
            (
                app_id,
                interviewer_name,
                round_number,
                round_type,
                scheduled_at,
                duration_minutes,
                meeting_link,
                location,
            ),
            out_param_names=("p_interview_id",),
        )
        return (
            jsonify(
                {
                    "message": "Interview scheduled successfully.",
                    "interview_id": out_params.get("p_interview_id"),
                }
            ),
            201,
        )
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


# -----------------------------------------------------------------------------
# 7. Parameterized Search & SQL Injection Defense Endpoint
# -----------------------------------------------------------------------------


@api_bp.route("/jobs/search", methods=["GET"])
def search_jobs():
    """
    Search job listings with multiple validated, parameterized dynamic filters.
    """
    title = sanitize_text(request.args.get("title", ""), max_length=150, field_name="title")
    workplace_raw = request.args.get("workplace_type", "").strip()
    employment_raw = request.args.get("employment_type", "").strip()
    page, per_page = validate_pagination(request.args.get("page"), request.args.get("per_page"))
    offset = (page - 1) * per_page

    query = (
        "SELECT job_id, title, location, employment_type, workplace_type, "
        "salary_min, salary_max FROM jobs WHERE status = 'ACTIVE'"
    )
    params = []

    if title:
        query += " AND title LIKE %s"
        params.append(f"%{title}%")

    if workplace_raw:
        workplace = validate_enum(workplace_raw, WORKPLACE_TYPE_ENUMS, "workplace_type")
        query += " AND workplace_type = %s"
        params.append(workplace)

    if employment_raw:
        employment = validate_enum(employment_raw, EMPLOYMENT_TYPE_ENUMS, "employment_type")
        query += " AND employment_type = %s"
        params.append(employment)

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s;"
    params.extend([per_page, offset])

    jobs = execute_query(query, params, fetch="all")
    return jsonify({"jobs": jobs, "count": len(jobs), "page": page, "per_page": per_page}), 200


# -----------------------------------------------------------------------------
# 8. Phase 5 UI-Supporting Skill, Resume, Profile & Interview Endpoints
# -----------------------------------------------------------------------------


@api_bp.route("/skills", methods=["GET"])
def list_skills():
    """Return canonical master skill catalog."""
    skills = execute_query(
        "SELECT skill_id, skill_name, category FROM skills ORDER BY category ASC, skill_name ASC;",
        fetch="all",
    )
    return jsonify({"skills": skills}), 200


@api_bp.route("/candidate/skills", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def upsert_candidate_skill():
    """Add or update a skill on the authenticated candidate's own profile."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    skill_id = validate_positive_int(data.get("skill_id"), "skill_id")
    proficiency = validate_enum(
        data.get("proficiency_level", "INTERMEDIATE"), PROFICIENCY_ENUMS, "proficiency_level"
    )
    years_exp = float(
        validate_decimal_range(data.get("years_of_experience", 0.0), "years_of_experience", min_val=0.0, max_val=60.0)
    )

    execute_query(
        """
        INSERT INTO candidate_skills (candidate_id, skill_id, proficiency_level, years_of_experience)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            proficiency_level = VALUES(proficiency_level),
            years_of_experience = VALUES(years_of_experience);
        """,
        (user["profile_id"], skill_id, proficiency, years_exp),
        commit=True,
    )
    return jsonify({"message": "Skill saved to your profile."}), 200


@api_bp.route("/candidate/skills/<int:skill_id>", methods=["DELETE"])
@login_required
@role_required("CANDIDATE")
def delete_candidate_skill(skill_id: int):
    """Remove a skill from the authenticated candidate's own profile."""
    user = get_current_user()
    execute_query(
        "DELETE FROM candidate_skills WHERE candidate_id = %s AND skill_id = %s;",
        (user["profile_id"], skill_id),
        commit=True,
    )
    return jsonify({"message": "Skill removed from your profile."}), 200


@api_bp.route("/resumes/<int:resume_id>/primary", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def set_primary_resume(resume_id: int):
    """Set one of the candidate's own resumes as primary."""
    user = get_current_user()
    if not check_resume_ownership(resume_id, user):
        return jsonify({"error": "Forbidden: You do not own this resume."}), 403

    execute_query(
        "UPDATE resumes SET is_primary = FALSE WHERE candidate_id = %s;",
        (user["profile_id"],),
        commit=True,
    )
    execute_query(
        "UPDATE resumes SET is_primary = TRUE WHERE resume_id = %s AND candidate_id = %s;",
        (resume_id, user["profile_id"]),
        commit=True,
    )
    return jsonify({"message": "Primary resume updated."}), 200


@api_bp.route("/resumes/<int:resume_id>", methods=["DELETE"])
@login_required
@role_required("CANDIDATE", "ADMIN")
def delete_resume(resume_id: int):
    """Delete a resume owned by the authenticated candidate (fails safely if attached to an application)."""
    user = get_current_user()
    if not check_resume_ownership(resume_id, user):
        return jsonify({"error": "Forbidden: You do not own this resume."}), 403

    try:
        execute_query("DELETE FROM resumes WHERE resume_id = %s;", (resume_id,), commit=True)
        return jsonify({"message": "Resume removed."}), 200
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


@api_bp.route("/candidate/applications/<int:app_id>/withdraw", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def withdraw_own_application(app_id: int):
    """Allow an authenticated candidate to withdraw their own application via sp_update_application_status."""
    user = get_current_user()
    if not check_application_ownership(app_id, user):
        return jsonify({"error": "Forbidden: You do not own this application."}), 403

    try:
        execute_procedure(
            "sp_update_application_status",
            (app_id, "WITHDRAWN", user["user_id"], "Withdrawn by candidate via web portal"),
        )
        return jsonify({"message": "Application withdrawn successfully."}), 200
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400


@api_bp.route("/recruiter/profile", methods=["GET", "PUT"])
@login_required
@role_required("RECRUITER")
def recruiter_profile_api():
    """Retrieve or update the authenticated recruiter's own corporate profile."""
    user = get_current_user()
    if request.method == "GET":
        row = execute_query(
            """
            SELECT rp.recruiter_id, u.user_id, u.email, u.first_name, u.last_name, u.phone,
                   rp.company_name, rp.company_website, rp.department, rp.designation, rp.office_location
            FROM recruiter_profiles rp
            INNER JOIN users u ON rp.user_id = u.user_id
            WHERE rp.recruiter_id = %s;
            """,
            (user["profile_id"],),
            fetch="one",
        )
        return jsonify({"profile": row}), 200

    raw_data = request.get_json(silent=True) or {}
    clean_data = validate_recruiter_profile_update(raw_data)

    if "phone" in clean_data:
        execute_query(
            "UPDATE users SET phone = %s WHERE user_id = %s;",
            (clean_data.pop("phone"), user["user_id"]),
            commit=True,
        )

    if clean_data:
        set_clause = ", ".join(f"{col} = %s" for col in clean_data.keys())
        params = list(clean_data.values()) + [user["profile_id"]]
        execute_query(
            f"UPDATE recruiter_profiles SET {set_clause} WHERE recruiter_id = %s;",
            params,
            commit=True,
        )

    return jsonify({"message": "Recruiter profile updated successfully."}), 200


@api_bp.route("/jobs/<int:job_id>/skills", methods=["POST"])
@login_required
@role_required("RECRUITER", "ADMIN")
def upsert_job_skill(job_id: int):
    """Add or update a skill requirement on a recruiter's own job."""
    user = get_current_user()
    if not check_job_ownership(job_id, user):
        return jsonify({"error": "Forbidden: You are not authorized to modify this job."}), 403

    data = request.get_json(silent=True) or {}
    skill_id = validate_positive_int(data.get("skill_id"), "skill_id")
    is_required = bool(data.get("is_required", True))
    min_years = float(
        validate_decimal_range(data.get("min_years_experience", 0.0), "min_years_experience", min_val=0.0, max_val=60.0)
    )

    execute_query(
        """
        INSERT INTO job_skills (job_id, skill_id, is_required, min_years_experience)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            is_required = VALUES(is_required),
            min_years_experience = VALUES(min_years_experience);
        """,
        (job_id, skill_id, is_required, min_years),
        commit=True,
    )
    return jsonify({"message": "Job skill requirement saved."}), 200


@api_bp.route("/jobs/<int:job_id>/skills/<int:skill_id>", methods=["DELETE"])
@login_required
@role_required("RECRUITER", "ADMIN")
def delete_job_skill(job_id: int, skill_id: int):
    """Remove a skill requirement from a recruiter's own job."""
    user = get_current_user()
    if not check_job_ownership(job_id, user):
        return jsonify({"error": "Forbidden: You are not authorized to modify this job."}), 403

    execute_query(
        "DELETE FROM job_skills WHERE job_id = %s AND skill_id = %s;",
        (job_id, skill_id),
        commit=True,
    )
    return jsonify({"message": "Job skill requirement removed."}), 200


@api_bp.route("/interviews/<int:interview_id>", methods=["PUT"])
@login_required
@role_required("RECRUITER", "ADMIN")
def update_interview(interview_id: int):
    """Update interview evaluation feedback, rating, or status (enforces trg_interviews_before_update)."""
    user = get_current_user()
    if not check_interview_access(interview_id, user):
        return jsonify({"error": "Forbidden: You are not authorized to update this interview."}), 403

    data = request.get_json(silent=True) or {}
    clean_data = validate_interview_update(data)

    set_clause = ", ".join(f"{col} = %s" for col in clean_data.keys())
    params = list(clean_data.values()) + [interview_id]
    try:
        execute_query(f"UPDATE interviews SET {set_clause} WHERE interview_id = %s;", params, commit=True)
        return jsonify({"message": "Interview updated successfully."}), 200
    except DatabaseSecurityError as dse:
        return jsonify({"error": dse.message}), 400

