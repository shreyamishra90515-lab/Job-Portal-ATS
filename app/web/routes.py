"""
Job Portal and Application Tracking System (ATS)
Web UI Controller Routes (Phase 5: Bootstrap 5 Multi-Role SSR + Secure API Integration)
"""

from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
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
)
from app.security.validation import (
    ValidationError,
    validate_email,
    validate_enum,
    validate_pagination,
    validate_registration_candidate,
    validate_registration_recruiter,
    sanitize_text,
    WORKPLACE_TYPE_ENUMS,
    EMPLOYMENT_TYPE_ENUMS,
    APPLICATION_STATUS_ENUMS,
    ROUND_TYPE_ENUMS,
    INTERVIEW_STATUS_ENUMS,
    PROFICIENCY_ENUMS,
    JOB_STATUS_ENUMS,
)

web_bp = Blueprint("web", __name__)

_ROLE_HOME = {
    "ADMIN": "web.admin_dashboard",
    "RECRUITER": "web.recruiter_dashboard",
    "CANDIDATE": "web.candidate_dashboard",
}

_JOB_SORT_SQL = {
    "newest": "j.created_at DESC",
    "salary_desc": "COALESCE(j.salary_max, j.salary_min, 0) DESC, j.created_at DESC",
    "deadline_asc": "CASE WHEN j.deadline_date IS NULL THEN 1 ELSE 0 END ASC, j.deadline_date ASC, j.created_at DESC",
}


def _safe_next_url(next_url: str | None) -> str | None:
    """Allow only local relative redirect paths to prevent open redirect attacks."""
    if not next_url or not isinstance(next_url, str):
        return None
    cleaned = next_url.strip()
    if cleaned.startswith("/") and not cleaned.startswith("//") and "\\" not in cleaned:
        return cleaned
    return None


def _redirect_for_role(role: str | None):
    endpoint = _ROLE_HOME.get(role or "", "web.landing")
    return redirect(url_for(endpoint))


# -----------------------------------------------------------------------------
# 1. Public & Authentication Pages
# -----------------------------------------------------------------------------


@web_bp.route("/", methods=["GET"])
def landing():
    """Public ATS landing page with platform summary and featured active openings."""
    stats = execute_query(
        """
        SELECT
            (SELECT COUNT(*) FROM jobs WHERE status = 'ACTIVE') AS active_jobs,
            (SELECT COUNT(*) FROM recruiter_profiles) AS companies,
            (SELECT COUNT(*) FROM skills) AS tracked_skills,
            (SELECT COUNT(*) FROM candidate_profiles) AS candidates;
        """,
        fetch="one",
    )
    featured_jobs = execute_query(
        """
        SELECT j.job_id, j.title, rp.company_name, j.location, j.employment_type,
               j.workplace_type, j.salary_min, j.salary_max, j.deadline_date
        FROM jobs j
        INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
        WHERE j.status = 'ACTIVE'
        ORDER BY j.created_at DESC
        LIMIT 6;
        """,
        fetch="all",
    )
    return render_template("public/index.html", stats=stats, featured_jobs=featured_jobs)


@web_bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Sign-in page delegating credential checks to Phase 4 Bcrypt auth layer."""
    current = get_current_user()
    if current:
        return _redirect_for_role(current.get("role"))

    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        next_param = _safe_next_url(request.form.get("next") or request.args.get("next"))

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/login.html", email=email, next_url=next_param), 400

        try:
            clean_email = validate_email(email)
        except ValidationError as ve:
            flash(ve.message, "danger")
            return render_template("auth/login.html", email=email, next_url=next_param), 400

        user_info = authenticate_user(clean_email, password)
        if not user_info:
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=clean_email, next_url=next_param), 401

        login_user(user_info)
        flash(f"Welcome back, {user_info['first_name']}!", "success")
        if next_param:
            return redirect(next_param)
        return _redirect_for_role(user_info.get("role"))

    return render_template(
        "auth/login.html",
        email="",
        next_url=_safe_next_url(request.args.get("next")),
    )


@web_bp.route("/register/candidate", methods=["GET", "POST"])
def register_candidate_page():
    """Candidate registration page calling Phase 2 sp_register_candidate."""
    if get_current_user():
        return _redirect_for_role(get_current_user().get("role"))

    if request.method == "POST":
        form_payload = {
            "email": request.form.get("email"),
            "password": request.form.get("password"),
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
            "phone": request.form.get("phone"),
            "headline": request.form.get("headline"),
            "summary": request.form.get("summary"),
            "current_location": request.form.get("current_location"),
            "years_of_experience": request.form.get("years_of_experience") or 0.0,
            "highest_education": request.form.get("highest_education"),
            "linkedin_url": request.form.get("linkedin_url"),
            "portfolio_url": request.form.get("portfolio_url"),
        }
        try:
            clean = validate_registration_candidate(form_payload)
            hashed_pwd = hash_password(clean["password"])
            execute_procedure(
                "sp_register_candidate",
                (
                    clean["email"],
                    hashed_pwd,
                    clean["first_name"],
                    clean["last_name"],
                    clean["phone"],
                    clean["headline"],
                    clean["summary"],
                    clean["current_location"],
                    clean["years_of_experience"],
                    clean["highest_education"],
                    clean["linkedin_url"],
                    clean["portfolio_url"],
                ),
                out_param_names=("p_user_id", "p_candidate_id"),
            )
            flash("Candidate account created! Please sign in.", "success")
            return redirect(url_for("web.login_page"))
        except (ValidationError, DatabaseSecurityError) as err:
            flash(err.message, "danger")
            safe_form = {k: v for k, v in form_payload.items() if k != "password"}
            return render_template("auth/register_candidate.html", form_data=safe_form), 400

    return render_template("auth/register_candidate.html", form_data={})


@web_bp.route("/register/recruiter", methods=["GET", "POST"])
def register_recruiter_page():
    """Recruiter registration page calling Phase 2 sp_register_recruiter."""
    if get_current_user():
        return _redirect_for_role(get_current_user().get("role"))

    if request.method == "POST":
        form_payload = {
            "email": request.form.get("email"),
            "password": request.form.get("password"),
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
            "phone": request.form.get("phone"),
            "company_name": request.form.get("company_name"),
            "company_website": request.form.get("company_website"),
            "department": request.form.get("department"),
            "designation": request.form.get("designation"),
            "office_location": request.form.get("office_location"),
        }
        try:
            clean = validate_registration_recruiter(form_payload)
            hashed_pwd = hash_password(clean["password"])
            execute_procedure(
                "sp_register_recruiter",
                (
                    clean["email"],
                    hashed_pwd,
                    clean["first_name"],
                    clean["last_name"],
                    clean["phone"],
                    clean["company_name"],
                    clean["company_website"],
                    clean["department"],
                    clean["designation"],
                    clean["office_location"],
                ),
                out_param_names=("p_user_id", "p_recruiter_id"),
            )
            flash("Recruiter account created! Please sign in.", "success")
            return redirect(url_for("web.login_page"))
        except (ValidationError, DatabaseSecurityError) as err:
            flash(err.message, "danger")
            safe_form = {k: v for k, v in form_payload.items() if k != "password"}
            return render_template("auth/register_recruiter.html", form_data=safe_form), 400

    return render_template("auth/register_recruiter.html", form_data={})


@web_bp.route("/logout", methods=["POST"])
@login_required
def logout_page():
    """Terminate authenticated web session via CSRF-protected POST."""
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("web.landing"))


# -----------------------------------------------------------------------------
# 2. Job Browsing & Detail Pages
# -----------------------------------------------------------------------------


@web_bp.route("/jobs", methods=["GET"])
def jobs_list_page():
    """Public job directory with search, filtering, sorting, and pagination."""
    raw_title = (request.args.get("title") or "").strip()
    title = sanitize_text(raw_title, max_length=150, field_name="title")
    workplace_raw = (request.args.get("workplace_type") or "").strip()
    employment_raw = (request.args.get("employment_type") or "").strip()
    sort_key = (request.args.get("sort") or "newest").strip()
    if sort_key not in _JOB_SORT_SQL:
        sort_key = "newest"

    try:
        page, per_page = validate_pagination(
            request.args.get("page"), request.args.get("per_page") or 9, max_per_page=50
        )
    except ValidationError:
        page, per_page = 1, 9

    where_clauses = ["j.status = 'ACTIVE'"]
    params = []

    if title:
        where_clauses.append("(j.title LIKE %s OR j.location LIKE %s OR rp.company_name LIKE %s)")
        like_pat = f"%{title}%"
        params.extend([like_pat, like_pat, like_pat])

    workplace = ""
    if workplace_raw:
        try:
            workplace = validate_enum(workplace_raw, WORKPLACE_TYPE_ENUMS, "workplace_type")
            where_clauses.append("j.workplace_type = %s")
            params.append(workplace)
        except ValidationError:
            flash("Invalid workplace filter ignored.", "warning")

    employment = ""
    if employment_raw:
        try:
            employment = validate_enum(employment_raw, EMPLOYMENT_TYPE_ENUMS, "employment_type")
            where_clauses.append("j.employment_type = %s")
            params.append(employment)
        except ValidationError:
            flash("Invalid employment filter ignored.", "warning")

    where_sql = " AND ".join(where_clauses)
    count_row = execute_query(
        f"""
        SELECT COUNT(*) AS total
        FROM jobs j
        INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
        WHERE {where_sql};
        """,
        params,
        fetch="one",
    )
    total = int((count_row or {}).get("total") or 0)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    jobs = execute_query(
        f"""
        SELECT j.job_id, j.recruiter_id, j.title, rp.company_name, j.location,
               j.employment_type, j.workplace_type, j.min_experience_years,
               j.salary_min, j.salary_max, j.status, j.deadline_date, j.created_at
        FROM jobs j
        INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
        WHERE {where_sql}
        ORDER BY {_JOB_SORT_SQL[sort_key]}
        LIMIT %s OFFSET %s;
        """,
        params + [per_page, offset],
        fetch="all",
    )

    return render_template(
        "jobs/list.html",
        jobs=jobs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        filters={
            "title": raw_title,
            "workplace_type": workplace,
            "employment_type": employment,
            "sort": sort_key,
        },
        workplace_options=sorted(WORKPLACE_TYPE_ENUMS),
        employment_options=sorted(EMPLOYMENT_TYPE_ENUMS),
    )


@web_bp.route("/jobs/<int:job_id>", methods=["GET"])
def job_detail_page(job_id: int):
    """Job detail page showing requirements, skills, company metadata, and candidate apply flow."""
    job = execute_query(
        """
        SELECT j.*, rp.company_name, rp.company_website, rp.office_location,
               rp.department, rp.designation
        FROM jobs j
        INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
        WHERE j.job_id = %s;
        """,
        (job_id,),
        fetch="one",
    )
    if not job:
        return render_template(
            "errors/error.html",
            code=404,
            title="Job Not Found",
            message="The requested job requisition does not exist.",
        ), 404

    user = get_current_user()
    if job["status"] == "DRAFT":
        if not user or not check_job_ownership(job_id, user):
            return render_template(
                "errors/error.html",
                code=403,
                title="Access Forbidden",
                message="Draft job requisitions are restricted to the owning recruiter or administrator.",
            ), 403

    skills = execute_query(
        """
        SELECT skill_id, skill_name, skill_category, is_required,
               requirement_type, min_years_experience
        FROM vw_job_skill_requirements
        WHERE job_id = %s
        ORDER BY is_required DESC, skill_name ASC;
        """,
        (job_id,),
        fetch="all",
    )

    existing_application = None
    candidate_resumes = []
    match_preview = None
    is_expired = bool(job.get("deadline_date") and job["deadline_date"] < date.today())
    can_apply = False

    if user and user.get("role") == "CANDIDATE" and user.get("profile_id"):
        cand_id = user["profile_id"]
        existing_application = execute_query(
            """
            SELECT application_id, current_status, match_score, applied_at
            FROM applications
            WHERE job_id = %s AND candidate_id = %s;
            """,
            (job_id, cand_id),
            fetch="one",
        )
        candidate_resumes = execute_query(
            """
            SELECT resume_id, file_name, file_size_kb, is_primary, uploaded_at
            FROM resumes
            WHERE candidate_id = %s
            ORDER BY is_primary DESC, uploaded_at DESC;
            """,
            (cand_id,),
            fetch="all",
        )
        score_row = execute_query(
            "SELECT fn_calculate_match_score(%s, %s) AS score;",
            (job_id, cand_id),
            fetch="one",
        )
        match_preview = score_row["score"] if score_row else None
        can_apply = (
            job["status"] == "ACTIVE"
            and not is_expired
            and existing_application is None
            and len(candidate_resumes) > 0
        )

    return render_template(
        "jobs/detail.html",
        job=job,
        skills=skills,
        existing_application=existing_application,
        candidate_resumes=candidate_resumes,
        match_preview=match_preview,
        is_expired=is_expired,
        can_apply=can_apply,
    )


# -----------------------------------------------------------------------------
# 3. Candidate Portal Pages (Strictly CANDIDATE Role)
# -----------------------------------------------------------------------------


@web_bp.route("/candidate/dashboard", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def candidate_dashboard():
    """Candidate KPIs powered by Phase 3 views."""
    user = get_current_user()
    cand_id = user["profile_id"]

    stats = execute_query(
        "SELECT * FROM vw_candidate_application_statistics WHERE candidate_id = %s;",
        (cand_id,),
        fetch="one",
    )
    recent_apps = execute_query(
        """
        SELECT * FROM vw_candidate_application_dashboard
        WHERE candidate_id = %s
        ORDER BY applied_at DESC
        LIMIT 5;
        """,
        (cand_id,),
        fetch="all",
    )
    upcoming_interviews = execute_query(
        """
        SELECT * FROM vw_interview_schedule
        WHERE candidate_id = %s AND interview_status IN ('SCHEDULED', 'RESCHEDULED')
        ORDER BY scheduled_at ASC
        LIMIT 5;
        """,
        (cand_id,),
        fetch="all",
    )
    return render_template(
        "candidate/dashboard.html",
        stats=stats,
        recent_apps=recent_apps,
        upcoming_interviews=upcoming_interviews,
    )


@web_bp.route("/candidate/profile", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def candidate_profile_page():
    """Candidate profile & skills management page."""
    user = get_current_user()
    cand_id = user["profile_id"]

    profile = execute_query(
        """
        SELECT cp.candidate_id, u.user_id, u.email, u.first_name, u.last_name, u.phone,
               cp.headline, cp.summary, cp.current_location, cp.years_of_experience,
               cp.highest_education, cp.linkedin_url, cp.portfolio_url
        FROM candidate_profiles cp
        INNER JOIN users u ON cp.user_id = u.user_id
        WHERE cp.candidate_id = %s;
        """,
        (cand_id,),
        fetch="one",
    )
    candidate_skills = execute_query(
        """
        SELECT skill_id, skill_name, skill_category, proficiency_level, skill_experience_years
        FROM vw_candidate_skill_profile
        WHERE candidate_id = %s
        ORDER BY skill_name ASC;
        """,
        (cand_id,),
        fetch="all",
    )
    all_skills = execute_query(
        "SELECT skill_id, skill_name, category FROM skills ORDER BY category ASC, skill_name ASC;",
        fetch="all",
    )
    return render_template(
        "candidate/profile.html",
        profile=profile,
        candidate_skills=candidate_skills,
        all_skills=all_skills,
        proficiency_levels=sorted(PROFICIENCY_ENUMS),
    )


@web_bp.route("/candidate/resumes", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def candidate_resumes_page():
    """Candidate resume library management page."""
    user = get_current_user()
    cand_id = user["profile_id"]
    resumes = execute_query(
        """
        SELECT r.resume_id, r.file_name, r.file_path, r.file_size_kb, r.is_primary, r.uploaded_at,
               (SELECT COUNT(*) FROM applications a WHERE a.resume_id = r.resume_id) AS used_in_apps
        FROM resumes r
        WHERE r.candidate_id = %s
        ORDER BY r.is_primary DESC, r.uploaded_at DESC;
        """,
        (cand_id,),
        fetch="all",
    )
    return render_template("candidate/resumes.html", resumes=resumes)


@web_bp.route("/candidate/applications", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def candidate_applications_page():
    """Candidate submitted applications and lifecycle status tracking."""
    user = get_current_user()
    apps = execute_query(
        """
        SELECT * FROM vw_candidate_application_dashboard
        WHERE candidate_id = %s
        ORDER BY applied_at DESC;
        """,
        (user["profile_id"],),
        fetch="all",
    )
    return render_template("candidate/applications.html", applications=apps)


@web_bp.route("/candidate/interviews", methods=["GET"])
@login_required
@role_required("CANDIDATE")
def candidate_interviews_page():
    """Candidate interview schedule view."""
    user = get_current_user()
    interviews = execute_query(
        """
        SELECT * FROM vw_interview_schedule
        WHERE candidate_id = %s
        ORDER BY scheduled_at DESC;
        """,
        (user["profile_id"],),
        fetch="all",
    )
    return render_template("candidate/interviews.html", interviews=interviews)


# -----------------------------------------------------------------------------
# 4. Recruiter Portal Pages (Strictly RECRUITER Role)
# -----------------------------------------------------------------------------


@web_bp.route("/recruiter/dashboard", methods=["GET"])
@login_required
@role_required("RECRUITER")
def recruiter_dashboard():
    """Recruiter performance KPIs, active pipeline, and upcoming interviews."""
    user = get_current_user()
    rec_id = user["profile_id"]

    job_perf = execute_query(
        """
        SELECT * FROM vw_recruiter_job_performance
        WHERE recruiter_id = %s
        ORDER BY job_id DESC;
        """,
        (rec_id,),
        fetch="all",
    )
    recent_apps = execute_query(
        """
        SELECT v.*
        FROM vw_candidate_application_dashboard v
        INNER JOIN jobs j ON v.job_id = j.job_id
        WHERE j.recruiter_id = %s
        ORDER BY v.applied_at DESC
        LIMIT 8;
        """,
        (rec_id,),
        fetch="all",
    )
    upcoming_interviews = execute_query(
        """
        SELECT v.*
        FROM vw_interview_schedule v
        INNER JOIN jobs j ON v.job_id = j.job_id
        WHERE j.recruiter_id = %s AND v.interview_status IN ('SCHEDULED', 'RESCHEDULED')
        ORDER BY v.scheduled_at ASC
        LIMIT 5;
        """,
        (rec_id,),
        fetch="all",
    )
    totals = {
        "total_jobs": len(job_perf),
        "active_jobs": sum(1 for j in job_perf if j["job_status"] == "ACTIVE"),
        "total_applications": sum(int(j["total_applications"] or 0) for j in job_perf),
        "total_interviews": sum(int(j["total_interviews"] or 0) for j in job_perf),
        "total_offers": sum(int(j["total_offers"] or 0) for j in job_perf),
    }
    return render_template(
        "recruiter/dashboard.html",
        totals=totals,
        job_perf=job_perf,
        recent_apps=recent_apps,
        upcoming_interviews=upcoming_interviews,
    )


@web_bp.route("/recruiter/profile", methods=["GET"])
@login_required
@role_required("RECRUITER")
def recruiter_profile_page():
    """Recruiter company & profile settings page."""
    user = get_current_user()
    profile = execute_query(
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
    return render_template("recruiter/profile.html", profile=profile)


@web_bp.route("/recruiter/jobs", methods=["GET"])
@login_required
@role_required("RECRUITER")
def recruiter_jobs_page():
    """Recruiter job management console (create, edit, skills, applicant links)."""
    user = get_current_user()
    rec_id = user["profile_id"]
    jobs = execute_query(
        """
        SELECT j.*,
               COALESCE(v.total_applications, 0) AS total_applications,
               v.avg_match_score,
               COALESCE(v.total_interviews, 0) AS total_interviews,
               COALESCE(v.total_offers, 0) AS total_offers
        FROM jobs j
        LEFT JOIN vw_recruiter_job_performance v ON j.job_id = v.job_id
        WHERE j.recruiter_id = %s
        ORDER BY j.created_at DESC;
        """,
        (rec_id,),
        fetch="all",
    )
    all_skills = execute_query(
        "SELECT skill_id, skill_name, category FROM skills ORDER BY category ASC, skill_name ASC;",
        fetch="all",
    )
    job_skills_rows = execute_query(
        """
        SELECT v.job_id, v.skill_id, v.skill_name, v.requirement_type, v.is_required, v.min_years_experience
        FROM vw_job_skill_requirements v
        INNER JOIN jobs j ON v.job_id = j.job_id
        WHERE j.recruiter_id = %s
        ORDER BY v.is_required DESC, v.skill_name ASC;
        """,
        (rec_id,),
        fetch="all",
    )
    skills_by_job = {}
    for row in job_skills_rows:
        skills_by_job.setdefault(row["job_id"], []).append(row)

    return render_template(
        "recruiter/jobs.html",
        jobs=jobs,
        all_skills=all_skills,
        skills_by_job=skills_by_job,
        employment_options=sorted(EMPLOYMENT_TYPE_ENUMS),
        workplace_options=sorted(WORKPLACE_TYPE_ENUMS),
        job_status_options=sorted(JOB_STATUS_ENUMS),
    )


@web_bp.route("/recruiter/jobs/<int:job_id>/applicants", methods=["GET"])
@login_required
@role_required("RECRUITER", "ADMIN")
def recruiter_job_applicants_page(job_id: int):
    """Applicant pipeline for an owned job with status update & interview scheduling controls."""
    user = get_current_user()
    if not check_job_ownership(job_id, user):
        return render_template(
            "errors/error.html",
            code=403,
            title="Access Forbidden",
            message="You are not authorized to view applicants for another recruiter's job.",
        ), 403

    job = execute_query(
        "SELECT * FROM jobs WHERE job_id = %s;",
        (job_id,),
        fetch="one",
    )
    if not job:
        return render_template(
            "errors/error.html",
            code=404,
            title="Job Not Found",
            message="The requested job requisition was not found.",
        ), 404

    applicants = execute_query(
        """
        SELECT v.*, a.cover_letter, cp.current_location, cp.highest_education,
               cp.linkedin_url, cp.portfolio_url
        FROM vw_candidate_application_dashboard v
        INNER JOIN applications a ON v.application_id = a.application_id
        INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
        WHERE v.job_id = %s
        ORDER BY v.match_score DESC, v.applied_at DESC;
        """,
        (job_id,),
        fetch="all",
    )
    return render_template(
        "recruiter/applicants.html",
        job=job,
        applicants=applicants,
        status_options=sorted(APPLICATION_STATUS_ENUMS),
        round_types=sorted(ROUND_TYPE_ENUMS),
    )


@web_bp.route("/recruiter/interviews", methods=["GET"])
@login_required
@role_required("RECRUITER")
def recruiter_interviews_page():
    """Recruiter interview schedule & evaluation management page."""
    user = get_current_user()
    interviews = execute_query(
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
    return render_template(
        "recruiter/interviews.html",
        interviews=interviews,
        interview_statuses=sorted(INTERVIEW_STATUS_ENUMS),
    )


# -----------------------------------------------------------------------------
# 5. Admin Portal Pages (Strictly ADMIN Role)
# -----------------------------------------------------------------------------


@web_bp.route("/admin/dashboard", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_dashboard():
    """System-wide executive overview powered by Phase 3 funnel view."""
    summary = execute_query(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM users WHERE is_active = TRUE) AS active_users,
            (SELECT COUNT(*) FROM candidate_profiles) AS total_candidates,
            (SELECT COUNT(*) FROM recruiter_profiles) AS total_recruiters,
            (SELECT COUNT(*) FROM jobs) AS total_jobs,
            (SELECT COUNT(*) FROM jobs WHERE status = 'ACTIVE') AS active_jobs,
            (SELECT COUNT(*) FROM applications) AS total_applications,
            (SELECT COUNT(*) FROM interviews) AS total_interviews;
        """,
        fetch="one",
    )
    funnel = execute_query(
        "SELECT * FROM vw_application_funnel ORDER BY stage_order ASC;",
        fetch="all",
    )
    recent_audit = execute_query(
        """
        SELECT h.history_id, h.application_id, j.title AS job_title,
               h.old_status, h.new_status, h.change_notes, h.changed_at,
               CONCAT(u.first_name, ' ', u.last_name) AS actor_name
        FROM application_status_history h
        INNER JOIN applications a ON h.application_id = a.application_id
        INNER JOIN jobs j ON a.job_id = j.job_id
        LEFT JOIN users u ON h.changed_by_user_id = u.user_id
        ORDER BY h.changed_at DESC, h.history_id DESC
        LIMIT 10;
        """,
        fetch="all",
    )
    return render_template(
        "admin/dashboard.html",
        summary=summary,
        funnel=funnel,
        recent_audit=recent_audit,
    )


@web_bp.route("/admin/users", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_users_page():
    """Administrative user directory (never selects or exposes password_hash)."""
    users = execute_query(
        """
        SELECT u.user_id, u.email, u.first_name, u.last_name, u.phone,
               u.is_active, r.role_name, u.created_at
        FROM users u
        INNER JOIN roles r ON u.role_id = r.role_id
        ORDER BY u.user_id ASC;
        """,
        fetch="all",
    )
    return render_template("admin/users.html", users=users)


@web_bp.route("/admin/jobs", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_jobs_page():
    """System-wide jobs overview using Phase 3 vw_recruiter_job_performance."""
    jobs = execute_query(
        "SELECT * FROM vw_recruiter_job_performance ORDER BY job_id DESC;",
        fetch="all",
    )
    return render_template("admin/jobs.html", jobs=jobs)


@web_bp.route("/admin/applications", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_applications_page():
    """System-wide applications overview using Phase 3 vw_candidate_application_dashboard."""
    applications = execute_query(
        "SELECT * FROM vw_candidate_application_dashboard ORDER BY applied_at DESC;",
        fetch="all",
    )
    return render_template("admin/applications.html", applications=applications)


@web_bp.route("/admin/interviews", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_interviews_page():
    """System-wide interviews overview using Phase 3 vw_interview_schedule."""
    interviews = execute_query(
        "SELECT * FROM vw_interview_schedule ORDER BY scheduled_at DESC;",
        fetch="all",
    )
    return render_template("admin/interviews.html", interviews=interviews)


@web_bp.route("/admin/audit-history", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_audit_history_page():
    """System-wide application status audit trail."""
    history = execute_query(
        """
        SELECT h.history_id, h.application_id, j.title AS job_title,
               CONCAT(uc.first_name, ' ', uc.last_name) AS candidate_name,
               h.old_status, h.new_status,
               CONCAT(ua.first_name, ' ', ua.last_name) AS actor_name,
               h.change_notes, h.changed_at
        FROM application_status_history h
        INNER JOIN applications a ON h.application_id = a.application_id
        INNER JOIN jobs j ON a.job_id = j.job_id
        INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
        INNER JOIN users uc ON cp.user_id = uc.user_id
        LEFT JOIN users ua ON h.changed_by_user_id = ua.user_id
        ORDER BY h.changed_at DESC, h.history_id DESC
        LIMIT 200;
        """,
        fetch="all",
    )
    return render_template("admin/audit_history.html", history=history)


@web_bp.route("/admin/reports", methods=["GET"])
@login_required
@role_required("ADMIN")
def admin_reports_page():
    """Executive reporting powered by Phase 3 analytical views."""
    funnel = execute_query("SELECT * FROM vw_application_funnel ORDER BY stage_order ASC;", fetch="all")
    job_stats = execute_query(
        "SELECT * FROM vw_job_application_statistics ORDER BY total_applications DESC;",
        fetch="all",
    )
    candidate_stats = execute_query(
        "SELECT * FROM vw_candidate_application_statistics ORDER BY total_applications DESC;",
        fetch="all",
    )
    return render_template(
        "admin/reports.html",
        funnel=funnel,
        job_stats=job_stats,
        candidate_stats=candidate_stats,
    )

