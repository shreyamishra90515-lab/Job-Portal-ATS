# Job Portal and Application Tracking System (ATS)
## Phase 4: Security, RBAC & Testing Specification

---

### 1. Phase 4 Objective

Phase 4 establishes the **application security, authentication, Role-Based Access Control (RBAC), object-level authorization, input validation, CSRF defense, secure transaction handling, and automated testing layer** on top of the frozen Phase 1–3 MySQL 8.0+ database (`job_portal_ats`).

> **Strict Schema Invariance Guarantee**:  
> Phase 1 (`sql/schema.sql`), Phase 2 (`sql/functions.sql`, `sql/procedures.sql`, `sql/triggers.sql`, `sql/sample_data.sql`), and Phase 3 (`sql/queries.sql`, `sql/views.sql`) remain **100% unchanged**. No tables, columns, data types, keys, constraints, triggers, functions, or procedures were added, renamed, or altered.

---

### 2. Security Architecture

The security architecture follows a defense-in-depth separation between the **Python Flask application security layer** and the **MySQL 8.0+ relational integrity engine**:

- **MySQL 8.0+ Responsibilities**:
  - Relational constraints (`PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK`, `ENUM`)
  - Composite resume ownership FK (`fk_applications_resume_owner`)
  - Stored functions (`fn_calculate_match_score`, `fn_get_candidate_application_count`, `fn_get_job_applicant_count`)
  - Transactional stored procedures (`sp_register_candidate`, `sp_register_recruiter`, `sp_apply_job`, `sp_update_application_status`, `sp_schedule_interview`)
  - Audit and scheduling conflict triggers (`trg_applications_after_insert`, `trg_applications_after_update`, `trg_interviews_before_insert`, `trg_interviews_before_update`)
- **Python Flask Responsibilities**:
  - Password hashing and constant-time verification (`bcrypt`)
  - Session establishment, cookie hardening, and session-fixation prevention
  - Centralized RBAC decorators (`@login_required`, `@role_required`, `@roles_required`)
  - Object-level ownership verification (IDOR defense)
  - Server-side input validation and HTML escaping
  - CSRF token generation and verification (`Flask-WTF`)
  - Parameterized SQL queries (`PyMySQL`) and sanitized error responses

The three canonical roles (`ADMIN`, `RECRUITER`, `CANDIDATE`) are resolved strictly from the `roles` table via `users.role_id`.

---

### 3. Authentication Architecture

Authentication is implemented in `app/security/auth.py` and exposed through `app/api/routes.py`:

1. **Login (`POST /api/auth/login`)**:
   - Validates `email` and `password` presence and email syntax (`validate_email`).
   - Queries `users INNER JOIN roles` using a parameterized SQL statement (`WHERE u.email = %s`).
   - Performs constant-time password verification via `bcrypt.checkpw`.
   - Mitigates user-enumeration timing differences using a precomputed dummy Bcrypt check (`_DUMMY_BCRYPT_HASH`) when an email does not exist.
   - Verifies `users.is_active` is truthy.
   - Resolves the role-specific profile ID (`candidate_profiles.candidate_id` or `recruiter_profiles.recruiter_id`).
   - Establishes a fresh session via `login_user()` and returns user metadata (excluding `password_hash`) plus a rotated CSRF token.
2. **Logout (`POST /api/auth/logout`)**:
   - Protected by `@login_required` and CSRF validation; clears the server session cookie via `session.clear()`.
3. **Session Identity (`GET /api/auth/me`)**:
   - Returns the authenticated user's session summary without querying or exposing credentials.
4. **Registration (`POST /api/auth/register-candidate`, `POST /api/auth/register-recruiter`)**:
   - Validates all registration fields server-side, hashes the plaintext password with Bcrypt (`cost=12`), and delegates atomic user + profile creation to Phase 2 stored procedures `sp_register_candidate` and `sp_register_recruiter`.
   - Client-supplied `role` or `role_id` values in request payloads are ignored; the stored procedures bind the authoritative role inside MySQL.

---

### 4. Password Security

- **Algorithm**: `bcrypt` (`bcrypt==5.0.0`, workload factor `12` rounds via `bcrypt.gensalt(rounds=12)`).
- **Policy (`validate_password`)**: Requires 8–72 bytes (respecting Bcrypt's 72-byte ceiling), at least one uppercase letter, one lowercase letter, one digit, and one special character.
- **Zero Plaintext Storage / Exposure**:
  - Plaintext passwords are never stored in the database, never logged, never placed in URLs, and never stored in Flask sessions.
  - `password_hash` is never returned in any API response (`/api/auth/login`, `/api/auth/me`, `/api/admin/users`, etc.).
  - No hardcoded passwords or seed backdoors exist in application source code.

---

### 5. Session Security

Configured in `config.py` (`Config`, `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`):

- `SESSION_COOKIE_NAME = "ats_session"`
- `SESSION_COOKIE_HTTPONLY = True` — blocks client-side JavaScript access to session cookies.
- `SESSION_COOKIE_SAMESITE = "Lax"` (`"Strict"` in `ProductionConfig`) — mitigates cross-site request forgery.
- `SESSION_COOKIE_SECURE = True` in `ProductionConfig` (HTTPS-only cookie transmission).
- `PERMANENT_SESSION_LIFETIME = timedelta(hours=2)` — bounds session validity.
- **Session Fixation Defense**: `login_user()` calls `session.clear()` before populating authenticated session keys and rotates the session CSRF token.
- **Minimum Session Payload**: Only `user_id`, `role`, `email`, `first_name`, `last_name`, and `profile_id` are stored in the signed session cookie.
- **Environment Secrets**: `SECRET_KEY`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, and `DATABASE_PASSWORD` are loaded via `python-dotenv` from `.env` (excluded from Git via `.gitignore`; template documented in `.env.example`). `ProductionConfig` refuses to start if `SECRET_KEY` is unset.

---

### 6. RBAC Matrix

The following permissions reflect the exact endpoints implemented in `app/api/routes.py` and `app/security/rbac.py`:

| Feature / Endpoint | Admin | Recruiter | Candidate |
|---|---:|---:|---:|
| Login / Logout / Current User (`/api/auth/*`) | ✓ | ✓ | ✓ |
| Browse & Search Active Jobs (`GET /api/jobs`, `/api/jobs/search`) | ✓ | ✓ | ✓ |
| View Non-Draft Job Detail (`GET /api/jobs/<id>`) | ✓ | ✓ | ✓ |
| View Draft Job Detail (`GET /api/jobs/<id>` where `DRAFT`) | ✓ | Own only | ✗ |
| Admin Dashboard (`GET /api/admin/dashboard`) | ✓ | ✗ | ✗ |
| Manage / List Users (`GET /api/admin/users`) | ✓ | ✗ | ✗ |
| View All Applications (`GET /api/admin/applications`) | ✓ | ✗ | ✗ |
| View All Interviews (`GET /api/admin/interviews`) | ✓ | ✗ | ✗ |
| View System Audit History (`GET /api/admin/audit-history`) | ✓ | ✗ | ✗ |
| View Executive Reports (`GET /api/admin/reports`) | ✓ | ✗ | ✗ |
| Create Job (`POST /api/jobs`) | ✓ | ✓ | ✗ |
| Modify Own Job (`PUT /api/jobs/<id>`) | ✓ | ✓ | ✗ |
| Modify Another Recruiter's Job (`PUT /api/jobs/<id>`) | ✓ | ✗ | ✗ |
| View Recruiter Jobs & Stats (`GET /api/recruiter/jobs`, `/api/recruiter/statistics`) | ✓ | Own only | ✗ |
| View Applicants for Job (`GET /api/jobs/<id>/applications`) | ✓ | Own jobs | ✗ |
| Manage Own Candidate Profile (`GET/PUT /api/candidate/profile`, `/api/candidates/<id>`) | ✓ | Read if applicant | Own only |
| Manage Own Resumes (`GET/POST /api/candidate/resumes`, `GET /api/resumes/<id>`) | ✓ | ✗ | Own only |
| Apply for Job (`POST /api/jobs/<id>/apply`) | ✗ | ✗ | ✓ |
| View Own Applications (`GET /api/candidate/applications`) | ✓ (all) | ✗ | Own only |
| View Application Detail & History (`GET /api/applications/<id>`, `.../history`) | ✓ | Own jobs | Own only |
| Update Application Status (`POST /api/applications/<id>/status`) | ✓ | Own jobs | ✗ |
| Schedule Interview (`POST /api/interviews/schedule`) | ✓ | Own jobs | ✗ |
| View Interviews (`GET /api/interviews/<id>`, `/api/recruiter/interviews`, `/api/candidate/interviews`) | ✓ | Own jobs | Own only |

---

### 7. Object-Level Authorization (IDOR Defense)

Role decorators alone cannot prevent Insecure Direct Object Reference (IDOR) vulnerabilities. `app/security/rbac.py` enforces resource-ownership checks using database-backed queries:

- `check_job_ownership(job_id, current_user)`: Ensures `jobs.recruiter_id == current_user["profile_id"]` for recruiters (`ADMIN` allowed).
- `check_application_ownership(application_id, current_user)`: Joins `applications` and `jobs` to ensure candidates only access their own applications (`applications.candidate_id == profile_id`) and recruiters only access applications for jobs they own (`jobs.recruiter_id == profile_id`).
- `check_resume_ownership(resume_id, current_user)`: Ensures `resumes.candidate_id == current_user["profile_id"]` for candidates (`ADMIN` allowed).
- `check_interview_access(interview_id, current_user)`: Joins `interviews -> applications -> jobs` to restrict interview records to the applying candidate, the owning recruiter, or `ADMIN`.
- `check_candidate_profile_access(candidate_id, current_user, write=False)`: Restricts profile writes strictly to the owning candidate or `ADMIN`; restricts recruiter reads strictly to candidates who have applied to that recruiter's jobs.

---

### 8. SQL Injection Prevention

All database reads and writes in `app/db.py`, `app/security/auth.py`, `app/security/rbac.py`, and `app/api/routes.py` use parameterized queries via `PyMySQL` placeholders (`%s`) or `cursor.callproc()`.

- Dynamic search filters in `GET /api/jobs/search` append static SQL clause fragments while binding user values exclusively through `params` lists.
- Stored procedure names passed to `execute_procedure()` are checked against an explicit `ALLOWED_PROCEDURES` whitelist.
- No string formatting (`f"..."`, `%`, `.format()`, or `+`) injects user input into SQL statements.

---

### 9. Input Validation

Implemented in `app/security/validation.py`:

- **Email (`validate_email`)**: Length <= 255, RFC-aligned regex check, lowercased and trimmed.
- **Password (`validate_password`)**: 8–72 bytes, uppercase + lowercase + digit + special character.
- **Phone (`validate_phone`)**: Validated against `^[+]?[0-9\s\-().]{7,20}$`.
- **URLs (`validate_url`)**: Enforces `http`/`https` scheme and valid `netloc`; blocks `javascript:` and `data:` URIs and whitespace.
- **Numeric & Salary Bounds (`validate_positive_int`, `validate_decimal_range`, `validate_salary_range`)**: Enforces positive IDs/durations, non-negative experience (`0.0–60.0`), and `salary_max >= salary_min`.
- **Dates & Datetimes (`validate_date`, `validate_datetime`)**: Strict `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS` / ISO parsing.
- **ENUM Whitelists (`validate_enum`)**: Validates `employment_type`, `workplace_type`, `job_status`, `application_status`, and `round_type` against Phase 1 ENUM sets.
- **Pagination (`validate_pagination`)**: Bounds `page >= 1` and `1 <= per_page <= 100`.
- **Text & Path Sanitization (`sanitize_text`, `validate_resume_payload`)**: Strips null bytes, enforces max lengths, HTML-escapes text (`html.escape`) to neutralize stored/reflected XSS, and rejects `..`, `/`, `\` path traversal and non-document extensions on resume filenames.

---

### 10. CSRF Protection

Implemented in `app/security/csrf.py` using `Flask-WTF` (`generate_csrf`, `validate_csrf`):

- Every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`) is intercepted in `@app.before_request` and validated against the session-bound token signed with `SECRET_KEY` and bounded by `WTF_CSRF_TIME_LIMIT = 3600`.
- Accepted token locations: `X-CSRF-Token` header, `X-CSRFToken` header, `csrf_token` form field, or `csrf_token` JSON key.
- Safe idempotent methods (`GET`, `HEAD`, `OPTIONS`, `TRACE`) are exempt and perform zero state mutations.
- Successful authentication rotates the CSRF token and returns it in the `X-CSRF-Token` response header and login payload.

---

### 11. Error Handling

Centralized JSON error handlers in `app/__init__.py` and sanitized DB wrappers in `app/db.py`:

- HTTP errors `400`, `401`, `403`, `404`, `405`, and `500` return structured JSON `{"error": "..."}` payloads.
- Security response headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Content-Security-Policy`, and `Cache-Control: no-store` on `/api/auth/*`) are applied globally.
- `_sanitize_mysql_error()` logs technical details server-side via Python `logging` while translating raw MySQL exceptions into safe messages (preserving controlled `SQLSTATE '45000'` business errors while concealing internal schema/table names for codes like `1146` or `1054`).

---

### 12. Transaction Handling

- Connections open with `autocommit=False`.
- `get_db_cursor(commit=...)` and `execute_procedure(...)` wrap operations in explicit `try / commit / except -> rollback / finally -> close`.
- Multi-table business workflows (`sp_register_candidate`, `sp_register_recruiter`, `sp_apply_job`, `sp_update_application_status`, `sp_schedule_interview`) execute via Phase 2 MySQL stored procedures with `DECLARE EXIT HANDLER FOR SQLEXCEPTION ROLLBACK; RESIGNAL;`, and `execute_procedure()` properly binds `IN` + `OUT` arguments and retrieves `PyMySQL` `@_<proc>_<idx>` output variables.

---

### 13. Database Privilege Strategy

`sql/security.sql` defines least-privilege MySQL accounts without altering any frozen schema tables:

- **`'ats_app_user'@'localhost'`**: Granted `SELECT`, `INSERT`, `UPDATE`, and `EXECUTE` on `job_portal_ats.*`, plus `DELETE` scoped solely to `resumes`, `candidate_skills`, and `job_skills`. Explicitly denied `DROP`, `ALTER`, `CREATE`, `INDEX`, `REFERENCES`, `TRIGGER`, `SUPER`, and `GRANT OPTION`.
- **`'ats_report_user'@'localhost'`**: Granted read-only `SELECT` strictly on the 8 Phase 3 reporting views.

---

### 14. Testing Architecture

The automated test suite uses `pytest` (`9.2.0`) and `pytest-cov` (`7.1.0`) under `tests/`:

- `tests/conftest.py`: Configures `TestingConfig` (`create_app("testing")`), isolated Flask test clients, direct MySQL verification connections, and `TestResourceTracker` for deterministic FK-safe cleanup after every test.
- All test users are dynamically provisioned with unique UUID emails and real Bcrypt hashes so tests are 100% reproducible and leave zero test artifacts in `job_portal_ats`.

---

### 15. Unit Testing

Covered across `tests/test_auth.py`, `tests/test_validation.py`, and `tests/test_database.py`:

- Bcrypt salting, cost factor (`$2b$12$`), and constant-time verification
- Server-side validation of email, password complexity/length, phone, URL schemes, numeric ranges, salary ordering, dates/datetimes, ENUMs, pagination, XSS escaping, and resume filename path traversal
- Whitelist enforcement on `execute_procedure()` and error message concealment in `app/db.py`

---

### 16. Integration Testing

Covered in `tests/test_integration.py`:

- **Workflow 1 & 2 (Candidate + Recruiter)**: Recruiter registers, logs in, creates job -> Candidate registers, logs in, updates profile, adds resume, searches jobs, applies -> Recruiter views applicants, updates status, schedules interview, views statistics -> Candidate verifies status history and scheduled interview.
- **Workflow 3 (Admin)**: Admin authenticates and accesses `/api/admin/dashboard`, `/users`, `/applications`, `/interviews`, `/audit-history`, and `/reports`.
- **Workflow 4 (Unauthorized Access)**: Verifies cross-role and cross-candidate access attempts return `403 Forbidden`.

---

### 17. Security Testing

Covered in `tests/test_auth.py`, `tests/test_rbac.py`, and `tests/test_security.py`:

- Login with valid, invalid email, wrong password, empty/malformed credentials, and deactivated account
- Logout session invalidation and unauthenticated `401` enforcement
- Role escalation prevention (ignoring client-supplied `"role": "ADMIN"`)
- IDOR prevention across jobs, applications, resumes, interviews, and candidate profiles
- SQL injection payloads (`' OR '1'='1`, `' OR 1=1 --`, `admin'--`, `UNION SELECT`, `DROP TABLE`) on login and job search
- Stored/reflected XSS escaping (`<script>alert('XSS')</script>`)
- Missing and forged CSRF token rejection (`400`)

---

### 18. Database Integrity Testing

Covered in `tests/test_integrity.py` and `tests/test_procedures.py`:

- `fk_applications_resume_owner` composite FK blocking cross-candidate resume usage
- `uq_job_candidate` blocking duplicate applications
- `chk_app_match_score` enforcing `[0.00, 100.00]` bounds
- ENUM rejection on invalid `applications.current_status`
- `trg_applications_after_insert` and `trg_applications_after_update` logging only actual status transitions
- `trg_interviews_before_insert` rejecting overlapping active interviews while permitting `CANCELLED` slots, different interviewers, and exact end/start boundaries
- All 5 Phase 2 stored procedures verified under valid, duplicate, invalid-state, expired-deadline, and rollback failure scenarios

---

### 19–21. Test Cases, Expected Results & Actual Results (Test Report)

Executed on **2026-11-25** using `.venv/bin/pytest -v --cov=app --cov-report=term-missing` against live MySQL 8.0+ (`job_portal_ats`):

- **Total Tests**: 49
- **Passed**: 49
- **Failed**: 0
- **Skipped**: 0
- **Errors**: 0
- **Code Coverage (`app/`)**: 79% (789 / 1,002 statements covered; 100% on `app/api/__init__.py` and `app/security/__init__.py`, 92% on `app/security/auth.py`, 89% on `app/security/csrf.py`, 81% on `app/security/validation.py`)

| Test ID | Category | Test | Expected | Actual | Result |
|---|---|---|---|---|---|
| AUTH-01 | Authentication | Valid login (`test_valid_login_and_session_establishment`) | 200 OK, HttpOnly & SameSite=Lax cookie, no `password_hash` | 200 OK, `HttpOnly` and `SameSite=Lax` present, `password_hash` omitted | PASS |
| AUTH-02 | Authentication | Wrong password (`test_login_wrong_password`) | 401 Unauthorized | 401 Unauthorized (`Invalid email or password.`) | PASS |
| AUTH-03 | Authentication | Empty / malformed / inactive (`test_login_empty_and_malformed_credentials`, `test_inactive_user_cannot_authenticate`) | 400 / 401 / denied | 400 on malformed/empty, `None` for inactive account | PASS |
| AUTH-04 | Session | Logout & unauthenticated access (`test_logout_clears_session`, `test_unauthenticated_access_rejected`) | Session cleared; 401 after logout | 200 on logout, 401 on subsequent `/api/auth/me` & protected routes | PASS |
| RBAC-01 | Authorization | Candidate → Admin/Recruiter (`test_candidate_blocked_from_admin_and_recruiter_routes`) | 403 Forbidden | 403 Forbidden across all 9 admin/recruiter endpoints | PASS |
| RBAC-02 | Authorization | Recruiter → Candidate private data (`test_recruiter_blocked_from_admin_and_candidate_only_routes`) | 403 Forbidden | 403 Forbidden on `/api/candidates/<id>` & `/api/resumes/<id>` | PASS |
| RBAC-03 | IDOR / Ownership | Recruiter A → Recruiter B job/application (`test_recruiter_cannot_modify_or_read_other_recruiter_job`, `test_recruiter_cannot_modify_other_recruiter_application`) | 403 Forbidden | 403 Forbidden on PUT job, GET applicants, status update, interview schedule | PASS |
| RBAC-04 | IDOR / Ownership | Candidate B → Candidate A resources (`test_candidate_cannot_access_other_candidate_resources`) | 403 Forbidden | 403 Forbidden on profile, resume, application, and history | PASS |
| RBAC-05 | Privilege Escalation | Client-supplied `role: ADMIN` (`test_client_supplied_role_never_elevates_privileges`) | Registered as CANDIDATE; admin blocked (403) | Role assigned `CANDIDATE`; `/api/admin/dashboard` returned 403 | PASS |
| SQL-01 | Security | SQL injection login (`test_sqli_login_bypass_rejected` - 4 payloads) | Rejected (400/401); no session | All 4 payloads rejected; `/api/auth/me` returned 401 | PASS |
| SQL-02 | Security | SQL injection job search (`test_sqli_job_search_parameterized` - 3 payloads) | Parameterized safe 200 response, no injection | 200 OK empty/normal list; `jobs` table intact | PASS |
| XSS-01 | Security | Script input (`test_xss_input_escaped_on_storage_and_output`) | Escaped (`&lt;script&gt;`) | Stored and returned as `&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;` | PASS |
| CSRF-01 | Security | Missing / forged CSRF token (`test_csrf_missing_and_invalid_tokens_rejected`) | 400 Rejected | 400 Rejected without/invalid token; 200 with valid rotated token | PASS |
| DB-01 | Integrity | Duplicate application (`test_db_enforces_unique_job_candidate_application`, `test_sp_apply_job_rules`) | Rejected | `IntegrityError` / `DatabaseSecurityError` raised | PASS |
| DB-02 | Integrity | Wrong resume owner (`test_db_enforces_resume_ownership_composite_fk`, `test_sp_apply_job_rules`) | Rejected | `MySQLError` (FK) / `DatabaseSecurityError` raised | PASS |
| DB-03 | Integrity | Interview conflict & boundaries (`test_interview_trigger_conflict_and_cancelled_exemption`, `test_sp_schedule_interview_conflicts_and_boundaries`) | Overlap rejected; cancelled & boundary allowed | Overlap rejected; cancelled slot, different interviewer, and exact boundary succeeded | PASS |
| PROC-01 | Procedures | All 5 Phase 2 procedures (`tests/test_procedures.py`) | Atomic commit/rollback & rules enforced | All 5 procedure test suites passed | PASS |
| INT-01 | Integration | Candidate, Recruiter, Admin & Boundary workflows (`tests/test_integration.py`) | End-to-end workflows succeed & unauthorized blocked | All 3 integration workflow tests passed | PASS |

Post-test database state check confirmed `job_portal_ats` retained exact baseline seed counts (`roles: 3`, `users: 14`, `candidate_profiles: 8`, `recruiter_profiles: 4`, `skills: 20`, `candidate_skills: 39`, `jobs: 6`, `job_skills: 23`, `resumes: 11`, `applications: 12`, `interviews: 8`, `application_status_history: 33`) with zero leftover test rows.

---

### 22. Known Limitations

1. **Frozen Phase 2 Seed Hash**: `sql/sample_data.sql` (frozen in Phase 2) populates sample `users.password_hash` with a synthetic placeholder string (`$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y`) that is not a mathematically valid Bcrypt digest for `Password@123`. In accordance with strict security rules (no hardcoded passwords or bypasses in source code), `app/security/auth.py` enforces pure `bcrypt.checkpw()`, so seed accounts require an explicit password reset or newly registered Bcrypt accounts to log in.
2. **Local Development DB Account**: `.env` in local development uses `root` to simplify setup and automated test fixture teardown; `sql/security.sql` provides the production least-privilege `ats_app_user` and `ats_report_user` accounts.
3. **In-Memory Rate Limiting / Account Lockout**: Repeated failed login throttling is not yet configured at the reverse-proxy or Flask-Limiter tier because Phase 1 schema is frozen (no failed-attempt counter columns on `users`).
4. **No Full Frontend UI (Scope Boundary)**: Phase 4 provides hardened API controllers and security middleware only; Bootstrap 5 templates and interactive charts are deferred to Phase 5.

---

### 23. Security Recommendations

1. Execute `sql/security.sql` with strong generated passwords and switch runtime `.env` `DATABASE_USER` from `root` to `ats_app_user`.
2. Deploy behind HTTPS with `FLASK_ENV=production` (`SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_SAMESITE='Strict'`, and a 256-bit random `SECRET_KEY`).
3. Add Flask-Limiter or reverse-proxy rate limiting on `/api/auth/login` and `/api/auth/register-*` prior to public exposure.
4. Implement real file-upload scanning, size/MIME verification, and non-public object storage for resume files in Phase 5.

---

### 24. Manual Security Review & Completion Checklist

#### Manual Security Review Summary
- [x] **Plaintext passwords**: None stored, logged, or returned; removed legacy hardcoded seed fallback from `app/security/auth.py`.
- [x] **Password hashes**: Bcrypt (`rounds=12`) via `bcrypt`; hashes excluded from all API responses and sessions.
- [x] **Hard-coded secrets**: Removed static fallback key in `config.py`; runtime uses env vars or ephemeral CSPRNG (`secrets.token_hex(32)`), and `ProductionConfig` requires `SECRET_KEY`.
- [x] **SQL injection**: 100% parameterized `PyMySQL` queries and whitelisted `callproc()` execution.
- [x] **XSS**: `sanitize_text()` escapes HTML entities on input; dangerous URL schemes (`javascript:`, `data:`) blocked by `validate_url()`.
- [x] **CSRF**: Enforced via `Flask-WTF` (`generate_csrf` / `validate_csrf`) on all `POST`/`PUT`/`PATCH`/`DELETE` routes.
- [x] **Broken access control / IDOR / Privilege escalation**: Enforced via `@login_required`, `@role_required`, DB-authoritative session roles, and 5 object-level ownership helpers.
- [x] **Insecure sessions**: `HttpOnly=True`, `SameSite=Lax`/`Strict`, `Secure=True` in production, 2-hour lifetime, session cleared + CSRF rotated on login.
- [x] **Sensitive error messages**: Raw MySQL exceptions, SQL statements, stack traces, and paths concealed behind sanitized JSON error handlers.
- [x] **Unsafe file handling / redirects / unvalidated input**: Resume filenames validated against traversal and restricted to `.pdf`/`.doc`/`.docx`; no open redirects; comprehensive server-side validation.

#### Phase 4 Completion Checklist
- [x] Existing Phase 1–3 files inspected and schema kept 100% frozen
- [x] RBAC, authentication, Bcrypt password security, and hardened sessions implemented
- [x] Object-level ownership authorization implemented across jobs, applications, resumes, interviews, and candidate profiles
- [x] Parameterized SQL, input validation, Flask-WTF CSRF, and sanitized error handlers implemented
- [x] Least-privilege DB user strategy documented in `sql/security.sql`
- [x] Comprehensive `pytest` suite executed (49/49 passing, 79% coverage)
- [x] Phase 4 specification and test report documented in `docs/phase4_security_rbac_testing.md`

