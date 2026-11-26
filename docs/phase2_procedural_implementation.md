# Job Portal and Application Tracking System (ATS)
## Phase 2: Procedural Implementation Specification

---

### 1. Phase 2 Objectives

Phase 2 builds the active procedural intelligence and business logic layer directly on top of the fixed, frozen Phase 1 database schema (`job_portal_ats`).

All logic is encapsulated within four separate SQL scripts:
1. `sql/functions.sql`: Algorithmic scoring functions and metrics.
2. `sql/procedures.sql`: ACID transactional workflows for user registration, job application, status updates, and interview scheduling.
3. `sql/triggers.sql`: Automated lifecycle auditing (`application_status_history`) and interview conflict detection.
4. `sql/sample_data.sql`: Comprehensive seed data populating all 12 tables without destructive statements.

> **Strict Schema Invariance Guarantee**:  
> No tables, columns, constraints, data types, or relationships from `sql/schema.sql` have been altered, added, or deleted. Phase 2 operates exclusively on the 12 existing Phase 1 tables.

---

### 2. Execution Order & Dependency Rationale

To maintain referential integrity and avoid compile-time dependency errors, execute the SQL files in this exact sequence:

1. **`sql/schema.sql` (Phase 1)**
   - Creates the `job_portal_ats` database and all 12 tables, primary keys, foreign keys, check constraints, and performance indexes.
2. **`sql/functions.sql` (Phase 2)**
   - Compiles stored functions (e.g. `fn_calculate_match_score`), which are referenced by downstream stored procedures (`sp_apply_job`) and seed data scripts.
3. **`sql/procedures.sql` (Phase 2)**
   - Compiles transactional stored procedures (`sp_register_candidate`, `sp_register_recruiter`, `sp_apply_job`, `sp_update_application_status`, `sp_schedule_interview`).
4. **`sql/triggers.sql` (Phase 2)**
   - Compiles table triggers on `applications` (`trg_applications_after_insert`, `trg_applications_after_update`) and `interviews` (`trg_interviews_before_insert`, `trg_interviews_before_update`).
5. **`sql/sample_data.sql` (Phase 2)**
   - Populates realistic seed data across all 12 tables. When seed applications and status updates are inserted, the triggers automatically generate genuine chronological audit logs in `application_status_history`.

---

### 3. Stored Functions (`sql/functions.sql`)

#### 3.1 `fn_calculate_match_score(p_job_id INT, p_candidate_id INT)`
- **Return Type**: `DECIMAL(5, 2)` (bounded strictly between `0.00` and `100.00`).
- **Description**: Calculates an ATS matching percentage between candidate competencies in `candidate_skills` and job opening requisitions in `job_skills`.
- **Calculation Formula**:
  1. **Job Requirement Weighting**:
     - Mandatory skills (`is_required = TRUE`): Weight $W_i = 2.00$.
     - Preferred/Optional skills (`is_required = FALSE`): Weight $W_i = 1.00$.
     - Total Possible Weight = $\sum W_i$. If no skills are defined for the job, returns `100.00`.
  2. **Candidate Competency Factor ($F_i \in [0.00, 1.00]$)**:
     If the candidate possesses skill $i$:
     - **Base Possession**: `0.60` (60% of skill weight for having the skill).
     - **Experience Factor**: Up to `0.20` (20%). If `min_years_experience = 0.0` or candidate meets/exceeds requirement, full `0.20`; otherwise prorated: $(\text{cand\_exp} / \text{req\_exp}) \times 0.20$.
     - **Proficiency Level Bonus**: Up to `0.20` (20%):
       - `'EXPERT'`: `+0.20`
       - `'ADVANCED'`: `+0.15`
       - `'INTERMEDIATE'`: `+0.10`
       - `'BEGINNER'`: `+0.05`
     - If candidate does *not* possess the skill, $F_i = 0.00$.
  3. **Total Earned Score**:
     $$\text{Earned Score} = \sum (W_i \times F_i)$$
  4. **Percentage Score**:
     $$\text{Final Score} = \text{ROUND}\left(\frac{\text{Earned Score}}{\text{Total Possible Weight}} \times 100.00, 2\right)$$

#### 3.2 Auxiliary Metric Functions
- **`fn_get_candidate_application_count(p_candidate_id INT) RETURNS INT`**:
  Returns the total number of applications submitted by a specific candidate.
- **`fn_get_job_applicant_count(p_job_id INT) RETURNS INT`**:
  Returns the total number of applications received by a specific job.

---

### 4. Stored Procedures (`sql/procedures.sql`)

All stored procedures implement comprehensive error handling via:
```sql
DECLARE EXIT HANDLER FOR SQLEXCEPTION
BEGIN
    ROLLBACK;
    RESIGNAL;
END;
```
Validation failures trigger standard user-friendly errors using `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '...'`.

#### 4.1 `sp_register_candidate`
- **Purpose**: Atomically creates a user credential in `users` and a profile in `candidate_profiles`.
- **Parameters**:
  - `IN p_email VARCHAR(255)`
  - `IN p_password_hash VARCHAR(255)`
  - `IN p_first_name VARCHAR(100)`
  - `IN p_last_name VARCHAR(100)`
  - `IN p_phone VARCHAR(20)`
  - `IN p_headline VARCHAR(255)`
  - `IN p_summary TEXT`
  - `IN p_current_location VARCHAR(150)`
  - `IN p_years_of_experience DECIMAL(4, 1)`
  - `IN p_highest_education VARCHAR(100)`
  - `IN p_linkedin_url VARCHAR(255)`
  - `IN p_portfolio_url VARCHAR(255)`
  - `OUT p_user_id INT`
  - `OUT p_candidate_id INT`
- **Integrity Checks**:
  - Validates non-empty email, password hash, and names.
  - Rejects duplicate emails before attempting insertion.
  - Automatically binds to `role_id` where `role_name = 'CANDIDATE'`.
  - Transaction rolls back if either user or profile insertion fails.

#### 4.2 `sp_register_recruiter`
- **Purpose**: Atomically creates a user credential in `users` and an organization profile in `recruiter_profiles`.
- **Parameters**:
  - `IN p_email VARCHAR(255)`
  - `IN p_password_hash VARCHAR(255)`
  - `IN p_first_name VARCHAR(100)`
  - `IN p_last_name VARCHAR(100)`
  - `IN p_phone VARCHAR(20)`
  - `IN p_company_name VARCHAR(150)`
  - `IN p_company_website VARCHAR(255)`
  - `IN p_department VARCHAR(100)`
  - `IN p_designation VARCHAR(100)`
  - `IN p_office_location VARCHAR(150)`
  - `OUT p_user_id INT`
  - `OUT p_recruiter_id INT`
- **Integrity Checks**:
  - Validates mandatory company name.
  - Checks duplicate email.
  - Automatically binds to `role_id` where `role_name = 'RECRUITER'`.

#### 4.3 `sp_apply_job`
- **Purpose**: Submits an application for an active job, enforces candidate resume ownership, calculates the ATS match score, and sets initial status to `'APPLIED'`.
- **Parameters**:
  - `IN p_job_id INT`
  - `IN p_candidate_id INT`
  - `IN p_resume_id INT`
  - `IN p_cover_letter TEXT`
  - `OUT p_application_id INT`
- **Integrity Checks**:
  - Verifies candidate existence.
  - Verifies job existence, active status (`status = 'ACTIVE'`), and that `deadline_date` has not passed.
  - Prevents duplicate applications (`uq_job_candidate`).
  - **Resume Ownership**: Validates that `(resume_id, candidate_id)` exists in `resumes`.
  - Automatically calculates ATS match score via `fn_calculate_match_score`.
  - Triggers `trg_applications_after_insert` to log initial status history.

#### 4.4 `sp_update_application_status`
- **Purpose**: Updates an application's lifecycle stage, passing actor metadata to the status history trigger.
- **Parameters**:
  - `IN p_application_id INT`
  - `IN p_new_status VARCHAR(50)`
  - `IN p_changed_by_user_id INT`
  - `IN p_change_notes VARCHAR(500)`
- **Integrity Checks**:
  - Verifies application existence.
  - Validates `p_new_status` against the 8 valid ENUM values (`'APPLIED'`, `'UNDER_REVIEW'`, `'SHORTLISTED'`, `'INTERVIEW_SCHEDULED'`, `'INTERVIEWED'`, `'OFFERED'`, `'REJECTED'`, `'WITHDRAWN'`).
  - Ignores redundant updates if status is identical.
  - Sets session variables (`@app_status_changed_by_user_id`, `@app_status_change_notes`) so the `AFTER UPDATE` trigger captures who made the change and why.

#### 4.5 `sp_schedule_interview`
- **Purpose**: Schedules an interview round, checks for calendar collisions, and advances the application status to `'INTERVIEW_SCHEDULED'`.
- **Parameters**:
  - `IN p_application_id INT`
  - `IN p_interviewer_name VARCHAR(150)`
  - `IN p_round_number INT`
  - `IN p_round_type VARCHAR(50)`
  - `IN p_scheduled_at DATETIME`
  - `IN p_duration_minutes INT`
  - `IN p_meeting_link VARCHAR(500)`
  - `IN p_location VARCHAR(150)`
  - `OUT p_interview_id INT`
- **Integrity Checks**:
  - Prevents scheduling for terminal application states (`'REJECTED'`, `'WITHDRAWN'`).
  - Detects time slot overlaps for the same interviewer across all active interviews.
  - Validates positive duration and valid round type.
  - Automatically updates the application status to `'INTERVIEW_SCHEDULED'` within the same transaction.

---

### 5. Database Triggers (`sql/triggers.sql`)

#### 5.1 Automated Status Tracking Triggers
- **`trg_applications_after_insert`**:
  Fires upon every `INSERT ON applications`. Automatically creates an initial audit log in `application_status_history`:
  - `old_status = NULL`
  - `new_status = NEW.current_status` (typically `'APPLIED'`)
  - `changed_by_user_id = @app_status_changed_by_user_id` (or `NULL` if direct system insert)
  - `change_notes = COALESCE(@app_status_change_notes, 'Initial application submitted')`
  - `changed_at = CURRENT_TIMESTAMP`
- **`trg_applications_after_update`**:
  Fires upon every `UPDATE ON applications`. Compares `OLD.current_status` and `NEW.current_status`:
  - If identical, **no record is created**.
  - If different, automatically logs:
    - `old_status = OLD.current_status`
    - `new_status = NEW.current_status`
    - `changed_by_user_id = @app_status_changed_by_user_id`
    - `change_notes = COALESCE(@app_status_change_notes, ...)`
    - `changed_at = CURRENT_TIMESTAMP`

#### 5.2 Interview Validation Triggers
- **`trg_interviews_before_insert` & `trg_interviews_before_update`**:
  Enforce scheduling integrity at the storage engine tier using existing fields:
  1. Checks parent application existence and rejects scheduling if `current_status IN ('REJECTED', 'WITHDRAWN')`.
  2. Enforces `duration_minutes > 0`.
  3. Checks for overlapping active interviews (`status IN ('SCHEDULED', 'RESCHEDULED')`) for the same interviewer during the requested time window.
     - Same interviewer + overlapping active interview → rejected
     - Different interviewer + overlapping time → allowed
     - Same application + different interviewers + overlapping time → allowed
     - Same interviewer + different applications + overlapping time → rejected
     - An interview ending exactly when another begins is not considered an overlap

---

### 6. Sample Data Coverage (`sql/sample_data.sql`)

The dataset populates all 12 tables with enterprise-grade consistency:
- **Roles**: 3 roles (ADMIN, RECRUITER, CANDIDATE).
- **Users**: 14 users (2 admins, 4 recruiters from Google, AWS, Microsoft, and Stripe, 8 candidates).
- **Profiles**: 4 recruiter profiles and 8 candidate profiles with complete education, URLs, and experience data.
- **Skills**: 20 canonical skills categorized across Programming, Database, Cloud/DevOps, and Web.
- **Candidate Skills**: 40+ proficiency mappings with specific years of experience.
- **Jobs**: 6 job postings (5 active, 1 closed legacy role) with salary ranges and deadlines.
- **Job Skills**: Mandatory and preferred skill requirements with minimum experience thresholds.
- **Resumes**: 11 uploaded resume documents with primary designations.
- **Applications**: 12 applications spanning all stages (`APPLIED`, `UNDER_REVIEW`, `SHORTLISTED`, `INTERVIEW_SCHEDULED`, `INTERVIEWED`, `OFFERED`, `REJECTED`, `WITHDRAWN`).
- **Interviews**: 8 interview rounds (technical, screening, managerial, final) with notes, ratings (1–5), and meeting links.
- **Audit History**: Automatically generated through triggers during application creation and state transitions.

---

### 7. Testing & Verification Examples

#### 7.1 Testing Stored Functions
```sql
USE job_portal_ats;

-- 1. Calculate ATS Match Score for Candidate 1 applying to Job 1 (Senior Cloud Python)
SELECT 
    c.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.job_id,
    j.title AS job_title,
    fn_calculate_match_score(j.job_id, c.candidate_id) AS ats_match_percentage
FROM candidate_profiles c
JOIN users u ON c.user_id = u.user_id
CROSS JOIN jobs j
WHERE c.candidate_id = 1 AND j.job_id = 1;

-- 2. Check Candidate Application Count
SELECT fn_get_candidate_application_count(1) AS total_applications_by_candidate_1;

-- 3. Check Job Applicant Count
SELECT fn_get_job_applicant_count(1) AS total_applicants_for_job_1;
```

#### 7.2 Testing Candidate Registration Procedure
```sql
-- Register a new test candidate
CALL sp_register_candidate(
    'test.candidate@university.edu',
    '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y',
    'Jordan',
    'Taylor',
    '+1-555-0999',
    'Junior Data Analyst',
    'Motivated recent graduate proficient in SQL, Python, and Tableau.',
    'San Francisco, CA',
    1.0,
    'B.S. in Statistics',
    'https://linkedin.com/in/jordantaylor',
    'https://github.com/jordantaylor',
    @new_user_id,
    @new_candidate_id
);

SELECT @new_user_id AS created_user_id, @new_candidate_id AS created_candidate_id;
```

#### 7.3 Testing Recruiter Registration Procedure
```sql
CALL sp_register_recruiter(
    'test.recruiter@meta.com',
    '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y',
    'Rachel',
    'Green',
    '+1-650-555-0888',
    'Meta Platforms Inc.',
    'https://about.meta.com',
    'AI Infrastructure',
    'Senior Technical Recruiter',
    'Menlo Park, CA',
    @rec_user_id,
    @rec_recruiter_id
);

SELECT @rec_user_id AS created_user_id, @rec_recruiter_id AS created_recruiter_id;
```

#### 7.4 Testing Job Application Procedure
```sql
-- Submit an application for Job 5 using Candidate 1's Resume 1
CALL sp_apply_job(
    5,                  -- Job ID (Associate Software Developer)
    1,                  -- Candidate ID (Aarav Patel)
    1,                  -- Resume ID (owned by Candidate 1)
    'Interested in contributing to Google Cloud early career mentorship programs.',
    @new_app_id
);

SELECT @new_app_id AS generated_application_id;
```

#### 7.5 Testing Resume Ownership Rejection (Security Test)
```sql
-- Attempting to apply with Candidate 1 specifying Candidate 2's Resume (ID 3)
-- This MUST fail with: "Integrity Error: Resume does not belong to the candidate or does not exist."
CALL sp_apply_job(
    5,                  -- Job ID
    1,                  -- Candidate 1
    3,                  -- Resume 3 (Belongs to Candidate 2)
    'Malicious application attempt',
    @fail_app_id
);
```

#### 7.6 Testing Application Status Update & Trigger Verification
```sql
-- Recruiter updates status of an application
CALL sp_update_application_status(
    6,                  -- Application ID
    'SHORTLISTED',      -- New Status
    3,                  -- Elena Rostova (User ID 3)
    'Selected for initial technical screening phone call'
);

-- Verify that the trigger automatically logged this event into application_status_history
SELECT 
    h.history_id,
    h.application_id,
    h.old_status,
    h.new_status,
    u.email AS changed_by_email,
    h.change_notes,
    h.changed_at
FROM application_status_history h
LEFT JOIN users u ON h.changed_by_user_id = u.user_id
WHERE h.application_id = 6
ORDER BY h.changed_at DESC;
```

#### 7.7 Testing Interview Scheduling & Conflict Detection
```sql
-- Schedule a round
CALL sp_schedule_interview(
    4,                                      -- Application ID
    'Elena Rostova',                        -- Interviewer
    1,                                      -- Round 1
    'TECHNICAL',                            -- Round Type
    '2026-12-15 10:00:00',                  -- Date & Time
    60,                                     -- Duration in minutes
    'https://meet.google.com/test-meet',    -- Link
    'Online Hangout',                       -- Location
    @new_interview_id
);

-- Attempting to schedule an overlapping interview for Elena Rostova at 10:30 on the same date:
-- MUST fail with: "Scheduling Conflict: Interviewer already has an active interview in this time slot."
CALL sp_schedule_interview(
    6,
    'Elena Rostova',
    1,
    'TECHNICAL',
    '2026-12-15 10:30:00',                  -- 30 min into the previous 60 min interview
    45,
    'https://meet.google.com/conflict',
    'Online',
    @fail_interview_id
);
```
