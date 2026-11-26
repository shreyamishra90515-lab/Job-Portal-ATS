-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: queries.sql (Phase 3: Queries, Reports & Analytical Layer)
-- Description: Comprehensive query suite demonstrating basic SELECT, relational
--              joins, grouping/aggregations, subqueries, advanced analytical
--              CTEs and window functions, date/time calculations, ATS reports,
--              and procedural data integrity testing.
-- Prerequisites: schema.sql, functions.sql, procedures.sql, triggers.sql,
--                and sample_data.sql.
-- Safety: Completely read-only and non-destructive.
-- =============================================================================

USE job_portal_ats;

-- =============================================================================
-- SECTION A — BASIC SELECT QUERIES
-- Demonstrating: SELECT, WHERE, ORDER BY, LIMIT, DISTINCT, status/date/salary/skill filtering
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q01: Active Job Postings
-- Purpose: Display all currently active job postings ordered by most recently created.
-- Concepts: SELECT, WHERE, ORDER BY
-- -----------------------------------------------------------------------------
SELECT 
    job_id,
    title,
    location,
    employment_type,
    workplace_type,
    min_experience_years,
    salary_min,
    salary_max,
    deadline_date,
    created_at
FROM jobs
WHERE status = 'ACTIVE'
ORDER BY created_at DESC;

-- -----------------------------------------------------------------------------
-- Q02: High-Salary Job Postings Filter
-- Purpose: Identify competitive roles offering a base salary of at least $140,000.
-- Concepts: Numeric comparison filtering, ORDER BY DESC
-- -----------------------------------------------------------------------------
SELECT 
    job_id,
    title,
    location,
    salary_min,
    salary_max,
    employment_type,
    workplace_type
FROM jobs
WHERE salary_min >= 140000.00
ORDER BY salary_min DESC, salary_max DESC;

-- -----------------------------------------------------------------------------
-- Q03: Experienced Candidate Profiles Filter
-- Purpose: Retrieve senior talent having at least 5.0 years of verified professional experience.
-- Concepts: Numeric filtering on decimal attributes, ORDER BY
-- -----------------------------------------------------------------------------
SELECT 
    candidate_id,
    headline,
    current_location,
    years_of_experience,
    highest_education,
    linkedin_url
FROM candidate_profiles
WHERE years_of_experience >= 5.0
ORDER BY years_of_experience DESC;

-- -----------------------------------------------------------------------------
-- Q04: Distinct Standardized Skills & Categories
-- Purpose: List all standardized skill categories and their cataloged skills.
-- Concepts: DISTINCT, multi-column ordering
-- -----------------------------------------------------------------------------
SELECT DISTINCT 
    category,
    skill_name
FROM skills
ORDER BY category ASC, skill_name ASC;

-- -----------------------------------------------------------------------------
-- Q05: Recent Job Applications
-- Purpose: Display the 5 most recently submitted job applications across the platform.
-- Concepts: ORDER BY TIMESTAMP, LIMIT pagination
-- -----------------------------------------------------------------------------
SELECT 
    application_id,
    job_id,
    candidate_id,
    current_status,
    match_score,
    applied_at
FROM applications
ORDER BY applied_at DESC
LIMIT 5;

-- -----------------------------------------------------------------------------
-- Q06: Upcoming Scheduled Interviews in a Target Window
-- Purpose: List active interview sessions scheduled on or after December 1, 2026.
-- Concepts: Date/time range filtering, ENUM set filtering
-- -----------------------------------------------------------------------------
SELECT 
    interview_id,
    application_id,
    interviewer_name,
    round_number,
    round_type,
    scheduled_at,
    duration_minutes,
    location,
    status
FROM interviews
WHERE status IN ('SCHEDULED', 'RESCHEDULED')
  AND scheduled_at >= '2026-12-01 00:00:00'
ORDER BY scheduled_at ASC;

-- -----------------------------------------------------------------------------
-- Q07: Remote & Hybrid Work Opportunities
-- Purpose: Retrieve all active job requisitions offering flexible workplace arrangements.
-- Concepts: IN predicate with ENUM values, compound WHERE filtering
-- -----------------------------------------------------------------------------
SELECT 
    job_id,
    title,
    workplace_type,
    location,
    employment_type,
    salary_min,
    salary_max
FROM jobs
WHERE workplace_type IN ('REMOTE', 'HYBRID')
  AND status = 'ACTIVE'
ORDER BY workplace_type ASC, salary_min DESC;

-- -----------------------------------------------------------------------------
-- Q08: Candidate Profile Search by Degree & Headline
-- Purpose: Search candidates holding an advanced degree (Master's / M.S.) with Python focus.
-- Concepts: Pattern matching with LIKE, Boolean AND logic
-- -----------------------------------------------------------------------------
SELECT 
    candidate_id,
    headline,
    highest_education,
    years_of_experience,
    current_location
FROM candidate_profiles
WHERE (highest_education LIKE '%M.S.%' OR highest_education LIKE '%Master%')
  AND headline LIKE '%Python%'
ORDER BY years_of_experience DESC;


-- =============================================================================
-- SECTION B — RELATIONAL JOIN QUERIES
-- Demonstrating: INNER JOIN, LEFT JOIN, multi-table joins, referential navigation
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q09: Candidate + Applications Join
-- Purpose: Show candidate contact details alongside each job opening applied for.
-- Concepts: 4-table INNER JOIN across candidate_profiles, users, applications, jobs
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email AS candidate_email,
    j.job_id,
    j.title AS job_title,
    a.application_id,
    a.current_status,
    a.match_score,
    a.applied_at
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN applications a ON cp.candidate_id = a.candidate_id
INNER JOIN jobs j ON a.job_id = j.job_id
ORDER BY a.applied_at DESC;

-- -----------------------------------------------------------------------------
-- Q10: Candidate + Resume + Application Join
-- Purpose: Verify which specific resume document was attached to each submitted application.
-- Concepts: Multi-table join enforcing candidate-resume ownership linkage
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    r.resume_id,
    r.file_name AS resume_file_name,
    r.file_size_kb,
    r.is_primary,
    a.current_status
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN resumes r ON a.resume_id = r.resume_id
INNER JOIN jobs j ON a.job_id = j.job_id
ORDER BY a.application_id ASC;

-- -----------------------------------------------------------------------------
-- Q11: Recruiter + Company + Jobs Join
-- Purpose: Display corporate recruiters and all jobs published under their requisition.
-- Concepts: 3-table join linking users, recruiter_profiles, and jobs
-- -----------------------------------------------------------------------------
SELECT 
    rp.recruiter_id,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    rp.company_name,
    rp.designation,
    j.job_id,
    j.title AS job_title,
    j.employment_type,
    j.workplace_type,
    j.status AS job_status,
    j.deadline_date
FROM recruiter_profiles rp
INNER JOIN users u ON rp.user_id = u.user_id
INNER JOIN jobs j ON rp.recruiter_id = j.recruiter_id
ORDER BY rp.company_name ASC, j.created_at DESC;

-- -----------------------------------------------------------------------------
-- Q12: Job + Required & Optional Skills Join
-- Purpose: Detail the technical skill requirements and experience thresholds for each job.
-- Concepts: M:N bridge join between jobs, job_skills, and skills master table
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    s.skill_name,
    s.category AS skill_category,
    CASE WHEN js.is_required = TRUE THEN 'MANDATORY' ELSE 'PREFERRED' END AS requirement_type,
    js.min_years_experience
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN job_skills js ON j.job_id = js.job_id
INNER JOIN skills s ON js.skill_id = s.skill_id
ORDER BY j.job_id ASC, js.is_required DESC, js.min_years_experience DESC;

-- -----------------------------------------------------------------------------
-- Q13: Candidate + Verified Skills & Proficiencies Join
-- Purpose: Map candidate talent competencies, declared proficiency levels, and experience.
-- Concepts: M:N bridge join between candidate_profiles, candidate_skills, and skills
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    cp.current_location,
    s.skill_name,
    s.category AS skill_category,
    cs.proficiency_level,
    cs.years_of_experience AS skill_years
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN candidate_skills cs ON cp.candidate_id = cs.candidate_id
INNER JOIN skills s ON cs.skill_id = s.skill_id
ORDER BY cp.candidate_id ASC, cs.years_of_experience DESC;

-- -----------------------------------------------------------------------------
-- Q14: Application + Full Lifecycle Status Audit History Join
-- Purpose: Display the sequential audit trail of status transitions for applications.
-- Concepts: Multi-table join with LEFT JOIN on audit actor user account
-- -----------------------------------------------------------------------------
SELECT 
    h.history_id,
    a.application_id,
    CONCAT(u_cand.first_name, ' ', u_cand.last_name) AS candidate_name,
    j.title AS job_title,
    h.old_status,
    h.new_status,
    h.change_notes,
    CONCAT(COALESCE(u_actor.first_name, 'System'), ' ', COALESCE(u_actor.last_name, 'Automated')) AS transitioned_by,
    h.changed_at
FROM application_status_history h
INNER JOIN applications a ON h.application_id = a.application_id
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u_cand ON cp.user_id = u_cand.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
LEFT JOIN users u_actor ON h.changed_by_user_id = u_actor.user_id
ORDER BY a.application_id ASC, h.changed_at ASC;

-- -----------------------------------------------------------------------------
-- Q15: Application + Interview Evaluations Join
-- Purpose: Present candidate applications and their corresponding interview round feedback.
-- Concepts: 4-table join connecting applications, candidates, jobs, and interviews
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    i.interview_id,
    i.round_number,
    i.round_type,
    i.interviewer_name,
    i.scheduled_at,
    i.duration_minutes,
    i.status AS interview_status,
    i.rating,
    i.feedback
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN interviews i ON a.application_id = i.application_id
ORDER BY a.application_id ASC, i.round_number ASC;

-- -----------------------------------------------------------------------------
-- Q16: Full ATS 360° Master Application Record
-- Purpose: Comprehensive enterprise view uniting candidate, application, job,
--          recruiter, company, resume, and ATS match score.
-- Concepts: 6-table relational master join
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u_cand.first_name, ' ', u_cand.last_name) AS candidate_name,
    u_cand.email AS candidate_email,
    cp.current_location AS candidate_location,
    cp.years_of_experience AS candidate_experience,
    j.title AS job_title,
    rp.company_name,
    CONCAT(u_rec.first_name, ' ', u_rec.last_name) AS recruiter_name,
    r.file_name AS resume_file_name,
    a.match_score,
    a.current_status,
    a.applied_at,
    a.updated_at
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u_cand ON cp.user_id = u_cand.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN users u_rec ON rp.user_id = u_rec.user_id
INNER JOIN resumes r ON a.resume_id = r.resume_id
ORDER BY a.application_id ASC;

-- -----------------------------------------------------------------------------
-- Q17: Unapplied Jobs & Requisition Application Volume (LEFT JOIN)
-- Purpose: Show all published jobs and total applications received, including zero-applicant jobs.
-- Concepts: LEFT JOIN, COUNT aggregation with outer table preservation
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    j.status AS job_status,
    COUNT(a.application_id) AS total_applicants
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name, j.status
ORDER BY total_applicants ASC, j.job_id ASC;

-- -----------------------------------------------------------------------------
-- Q18: Applications Without Scheduled Interviews (LEFT JOIN with NULL Check)
-- Purpose: Identify active applications that have not yet had any interview round scheduled.
-- Concepts: LEFT JOIN with IS NULL filter on foreign key
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    rp.company_name,
    a.current_status,
    a.match_score,
    a.applied_at
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
LEFT JOIN interviews i ON a.application_id = i.application_id
WHERE i.interview_id IS NULL
ORDER BY a.applied_at DESC;


-- =============================================================================
-- SECTION C — GROUP BY AND AGGREGATE QUERIES
-- Demonstrating: COUNT, SUM, AVG, MIN, MAX, GROUP BY, HAVING filtering
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q19: Application Volume and Match Score Averages per Job
-- Purpose: Summarize applicant volume and average candidate match quality per job opening.
-- Concepts: COUNT, AVG, MIN, MAX, GROUP BY
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    COUNT(a.application_id) AS total_applicants,
    ROUND(AVG(a.match_score), 2) AS avg_match_score,
    MIN(a.match_score) AS min_match_score,
    MAX(a.match_score) AS max_match_score
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name
ORDER BY total_applicants DESC, avg_match_score DESC;

-- -----------------------------------------------------------------------------
-- Q20: Candidate Application Portfolio and Score Range
-- Purpose: Compute total submissions and match score bounds for each active candidate.
-- Concepts: Multi-table aggregation, ROUND(AVG())
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    COUNT(a.application_id) AS total_applications_submitted,
    ROUND(AVG(a.match_score), 2) AS avg_candidate_match,
    MIN(a.match_score) AS lowest_match_score,
    MAX(a.match_score) AS highest_match_score
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN applications a ON cp.candidate_id = a.candidate_id
GROUP BY cp.candidate_id, u.first_name, u.last_name
ORDER BY total_applications_submitted DESC, avg_candidate_match DESC;

-- -----------------------------------------------------------------------------
-- Q21: Job Postings Distribution by Recruiter and Company
-- Purpose: Audit recruiter requisition workloads and active vs closed job counts.
-- Concepts: Conditional aggregation with SUM(CASE), COUNT
-- -----------------------------------------------------------------------------
SELECT 
    rp.recruiter_id,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    rp.company_name,
    COUNT(j.job_id) AS total_jobs_posted,
    SUM(CASE WHEN j.status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_jobs,
    SUM(CASE WHEN j.status = 'CLOSED' THEN 1 ELSE 0 END) AS closed_jobs
FROM recruiter_profiles rp
INNER JOIN users u ON rp.user_id = u.user_id
LEFT JOIN jobs j ON rp.recruiter_id = j.recruiter_id
GROUP BY rp.recruiter_id, u.first_name, u.last_name, rp.company_name
ORDER BY total_jobs_posted DESC;

-- -----------------------------------------------------------------------------
-- Q22: Application Volume Distribution Across Pipeline Statuses
-- Purpose: Measure candidate distribution across all 8 ATS pipeline stages.
-- Concepts: Single-table GROUP BY with COUNT and relative share
-- -----------------------------------------------------------------------------
SELECT 
    current_status,
    COUNT(*) AS applicant_count
FROM applications
GROUP BY current_status
ORDER BY applicant_count DESC;

-- -----------------------------------------------------------------------------
-- Q23: Average ATS Match Score per Job with Applicant Threshold (HAVING)
-- Purpose: Report average match scores only for jobs that have received at least 2 applicants.
-- Concepts: GROUP BY with HAVING clause filtering on aggregate count
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    COUNT(a.application_id) AS applicant_volume,
    ROUND(AVG(a.match_score), 2) AS avg_match_score
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name
HAVING COUNT(a.application_id) >= 2
ORDER BY avg_match_score DESC;

-- -----------------------------------------------------------------------------
-- Q24: Candidates with Multiple Submissions and High Average Match (HAVING)
-- Purpose: Identify active candidates who have submitted >= 2 applications with avg match >= 70%.
-- Concepts: Multiple aggregate filters inside HAVING clause
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    COUNT(a.application_id) AS application_count,
    ROUND(AVG(a.match_score), 2) AS avg_match_score
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN applications a ON cp.candidate_id = a.candidate_id
GROUP BY cp.candidate_id, u.first_name, u.last_name
HAVING COUNT(a.application_id) >= 2
   AND AVG(a.match_score) >= 70.00
ORDER BY avg_match_score DESC;

-- -----------------------------------------------------------------------------
-- Q25: Interview Frequency and Average Feedback Rating per Application
-- Purpose: Track the depth of the interview process and mean rating per candidate application.
-- Concepts: Aggregating child records with COUNT and AVG(rating)
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    COUNT(i.interview_id) AS total_rounds_scheduled,
    SUM(CASE WHEN i.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_rounds,
    ROUND(AVG(i.rating), 2) AS avg_interview_rating
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN interviews i ON a.application_id = i.application_id
GROUP BY a.application_id, u.first_name, u.last_name, j.title
ORDER BY avg_interview_rating DESC, total_rounds_scheduled DESC;

-- -----------------------------------------------------------------------------
-- Q26: Industry Skill Demand Ranking in Job Requisitions
-- Purpose: Rank skills according to how frequently employers require or prefer them.
-- Concepts: GROUP BY on master skill catalog with SUM(CASE) breakdown
-- -----------------------------------------------------------------------------
SELECT 
    s.skill_id,
    s.skill_name,
    s.category,
    COUNT(js.job_id) AS total_demand_count,
    SUM(CASE WHEN js.is_required = TRUE THEN 1 ELSE 0 END) AS mandatory_demand_count,
    SUM(CASE WHEN js.is_required = FALSE THEN 1 ELSE 0 END) AS preferred_demand_count
FROM skills s
INNER JOIN job_skills js ON s.skill_id = js.skill_id
GROUP BY s.skill_id, s.skill_name, s.category
ORDER BY total_demand_count DESC, mandatory_demand_count DESC;

-- -----------------------------------------------------------------------------
-- Q27: Candidate Talent Pool Skill Availability by Category
-- Purpose: Analyze talent pool depth by counting candidates possessing each standardized skill.
-- Concepts: GROUP BY with multi-level ordering
-- -----------------------------------------------------------------------------
SELECT 
    s.category,
    s.skill_name,
    COUNT(cs.candidate_id) AS candidate_count,
    ROUND(AVG(cs.years_of_experience), 1) AS avg_years_experience
FROM skills s
INNER JOIN candidate_skills cs ON s.skill_id = cs.skill_id
GROUP BY s.category, s.skill_name
ORDER BY s.category ASC, candidate_count DESC;

-- -----------------------------------------------------------------------------
-- Q28: Compensation Statistics Across Workplace Models
-- Purpose: Compare minimum, maximum, and average salary bands by workplace arrangement.
-- Concepts: Aggregating financial bounds: MIN, MAX, AVG across workplace types
-- -----------------------------------------------------------------------------
SELECT 
    workplace_type,
    COUNT(*) AS total_openings,
    MIN(salary_min) AS lowest_min_salary,
    MAX(salary_max) AS highest_max_salary,
    ROUND(AVG(salary_min), 2) AS avg_base_salary_min,
    ROUND(AVG(salary_max), 2) AS avg_base_salary_max
FROM jobs
WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
GROUP BY workplace_type
ORDER BY avg_base_salary_max DESC;

-- -----------------------------------------------------------------------------
-- Q29: High-Volume Job Requisitions (HAVING clause)
-- Purpose: Highlight popular jobs attracting more than 2 applications.
-- Concepts: Strict HAVING filter with ORDER BY
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title,
    rp.company_name,
    COUNT(a.application_id) AS total_applications
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name
HAVING COUNT(a.application_id) > 2
ORDER BY total_applications DESC;


-- =============================================================================
-- SECTION D — SUBQUERIES
-- Demonstrating: Scalar subqueries, correlated subqueries, IN, EXISTS, NOT EXISTS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q30: Candidates Who Have Applied to at Least One Job (IN Subquery)
-- Purpose: Identify all registered candidates with active submissions in the system.
-- Concepts: Independent subquery evaluated within an IN predicate
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email,
    cp.headline,
    cp.years_of_experience
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
WHERE cp.candidate_id IN (
    SELECT DISTINCT candidate_id 
    FROM applications
)
ORDER BY cp.candidate_id ASC;

-- -----------------------------------------------------------------------------
-- Q31: Candidates Who Have Never Applied (NOT EXISTS Correlated Subquery)
-- Purpose: Find registered candidates who have created a profile but never submitted an application.
-- Concepts: Correlated subquery with NOT EXISTS
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email,
    cp.years_of_experience,
    cp.created_at
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
WHERE NOT EXISTS (
    SELECT 1 
    FROM applications a 
    WHERE a.candidate_id = cp.candidate_id
)
ORDER BY cp.candidate_id ASC;

-- -----------------------------------------------------------------------------
-- Q32: Jobs That Have Received Applications (EXISTS Correlated Subquery)
-- Purpose: Filter job openings that have successfully attracted at least one candidate.
-- Concepts: Correlated subquery with EXISTS
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title,
    rp.company_name,
    j.location,
    j.status
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
WHERE EXISTS (
    SELECT 1 
    FROM applications a 
    WHERE a.job_id = j.job_id
)
ORDER BY j.job_id ASC;

-- -----------------------------------------------------------------------------
-- Q33: Jobs That Have Received Zero Applications (NOT EXISTS Subquery)
-- Purpose: Identify dormant or underperforming job listings needing sourcing attention.
-- Concepts: Correlated subquery with NOT EXISTS
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title,
    rp.company_name,
    j.status,
    j.created_at
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
WHERE NOT EXISTS (
    SELECT 1 
    FROM applications a 
    WHERE a.job_id = j.job_id
)
ORDER BY j.created_at DESC;

-- -----------------------------------------------------------------------------
-- Q34: Applications Exceeding the Platform-Wide Average Match Score
-- Purpose: Isolate top-tier applications performing above the system average match score.
-- Concepts: Scalar subquery returning a single aggregate value inside WHERE
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    rp.company_name,
    a.match_score,
    a.current_status
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
WHERE a.match_score > (
    SELECT AVG(match_score) 
    FROM applications
)
ORDER BY a.match_score DESC;

-- -----------------------------------------------------------------------------
-- Q35: Job Openings Receiving Above-Average Application Volume
-- Purpose: Detect high-traffic job posts that exceed the mean application count per job.
-- Concepts: Subquery inside HAVING comparing group aggregate with system-wide mean
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    COUNT(a.application_id) AS total_applicants
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name
HAVING COUNT(a.application_id) > (
    SELECT COUNT(*) / COUNT(DISTINCT job_id) 
    FROM applications
)
ORDER BY total_applicants DESC;

-- -----------------------------------------------------------------------------
-- Q36: Candidates Possessing Python Skill with Advanced or Expert Proficiency
-- Purpose: Talent search finding candidates mastering Python via a correlated subquery.
-- Concepts: Correlated subquery with EXISTS and multiple predicate conditions
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email,
    cp.headline,
    cp.years_of_experience
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
WHERE EXISTS (
    SELECT 1 
    FROM candidate_skills cs
    INNER JOIN skills s ON cs.skill_id = s.skill_id
    WHERE cs.candidate_id = cp.candidate_id
      AND s.skill_name = 'Python'
      AND cs.proficiency_level IN ('ADVANCED', 'EXPERT')
)
ORDER BY cp.years_of_experience DESC;

-- -----------------------------------------------------------------------------
-- Q37: Recruiters Publishing More Jobs Than the Platform Average
-- Purpose: Highlight high-volume corporate recruiters managing above-average job pipelines.
-- Concepts: Subquery in HAVING comparing group count with recruiter mean
-- -----------------------------------------------------------------------------
SELECT 
    rp.recruiter_id,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    rp.company_name,
    COUNT(j.job_id) AS jobs_posted
FROM recruiter_profiles rp
INNER JOIN users u ON rp.user_id = u.user_id
INNER JOIN jobs j ON rp.recruiter_id = j.recruiter_id
GROUP BY rp.recruiter_id, u.first_name, u.last_name, rp.company_name
HAVING COUNT(j.job_id) > (
    SELECT COUNT(*) / COUNT(DISTINCT recruiter_id) 
    FROM jobs
)
ORDER BY jobs_posted DESC;

-- -----------------------------------------------------------------------------
-- Q38: Candidates with Above-Average Match Scores Across Applications
-- Purpose: Filter candidate profiles whose individual mean match score outperforms the global average.
-- Concepts: Scalar subquery combined with GROUP BY and HAVING
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    COUNT(a.application_id) AS applications_count,
    ROUND(AVG(a.match_score), 2) AS candidate_avg_score
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN applications a ON cp.candidate_id = a.candidate_id
GROUP BY cp.candidate_id, u.first_name, u.last_name
HAVING AVG(a.match_score) > (
    SELECT AVG(match_score) 
    FROM applications
)
ORDER BY candidate_avg_score DESC;


-- =============================================================================
-- SECTION E — ADVANCED ANALYTICAL QUERIES (MySQL 8.0+)
-- Demonstrating: CTEs, window functions (DENSE_RANK, RANK, ROW_NUMBER, LAG),
--                conditional aggregation, and candidate-skill gap analysis
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q39: Candidate Ranking per Job Requisition
-- Purpose: Rank all applicants for each job by ATS match score, with tie-handling.
-- Concepts: DENSE_RANK() OVER (PARTITION BY ... ORDER BY ... DESC)
-- -----------------------------------------------------------------------------
SELECT 
    a.job_id,
    j.title AS job_title,
    rp.company_name,
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    a.match_score,
    a.current_status,
    DENSE_RANK() OVER (
        PARTITION BY a.job_id 
        ORDER BY a.match_score DESC
    ) AS applicant_rank
FROM applications a
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
ORDER BY a.job_id ASC, applicant_rank ASC;

-- -----------------------------------------------------------------------------
-- Q40: Job Application Popularity Ranking
-- Purpose: Rank job openings by total application volume using window functions.
-- Concepts: RANK() OVER (ORDER BY COUNT(*) DESC)
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    j.status AS job_status,
    COUNT(a.application_id) AS total_applications,
    RANK() OVER (
        ORDER BY COUNT(a.application_id) DESC
    ) AS popularity_rank
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name, j.status
ORDER BY popularity_rank ASC, j.job_id ASC;

-- -----------------------------------------------------------------------------
-- Q41: Recruiter Hiring Pipeline Productivity Matrix (Multi-CTE)
-- Purpose: Synthesize recruiter performance across postings, applicant volume, and interviews.
-- Concepts: Multiple Common Table Expressions (WITH clause) with outer join assembly
-- -----------------------------------------------------------------------------
WITH recruiter_jobs AS (
    SELECT recruiter_id, COUNT(*) AS jobs_posted
    FROM jobs
    GROUP BY recruiter_id
),
recruiter_apps AS (
    SELECT j.recruiter_id, COUNT(a.application_id) AS applications_received
    FROM jobs j
    INNER JOIN applications a ON j.job_id = a.job_id
    GROUP BY j.recruiter_id
),
recruiter_interviews AS (
    SELECT j.recruiter_id, COUNT(i.interview_id) AS interviews_conducted
    FROM jobs j
    INNER JOIN applications a ON j.job_id = a.job_id
    INNER JOIN interviews i ON a.application_id = i.application_id
    GROUP BY j.recruiter_id
)
SELECT 
    rp.recruiter_id,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    rp.company_name,
    COALESCE(rj.jobs_posted, 0) AS total_jobs_posted,
    COALESCE(ra.applications_received, 0) AS total_applications_received,
    COALESCE(ri.interviews_conducted, 0) AS total_interviews_conducted,
    DENSE_RANK() OVER (
        ORDER BY COALESCE(ra.applications_received, 0) DESC, COALESCE(ri.interviews_conducted, 0) DESC
    ) AS pipeline_rank
FROM recruiter_profiles rp
INNER JOIN users u ON rp.user_id = u.user_id
LEFT JOIN recruiter_jobs rj ON rp.recruiter_id = rj.recruiter_id
LEFT JOIN recruiter_apps ra ON rp.recruiter_id = ra.recruiter_id
LEFT JOIN recruiter_interviews ri ON rp.recruiter_id = ri.recruiter_id
ORDER BY pipeline_rank ASC;

-- -----------------------------------------------------------------------------
-- Q42: Enterprise Recruitment Funnel with Drop-off & Conversion Rates
-- Purpose: Calculate cumulative stage transitions and conversion percentages across the funnel.
-- Concepts: CTE with conditional aggregation and percentage computations
-- -----------------------------------------------------------------------------
WITH funnel_counts AS (
    SELECT 
        COUNT(*) AS stage_1_applied,
        SUM(CASE WHEN current_status IN ('UNDER_REVIEW', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED') THEN 1 ELSE 0 END) AS stage_2_reviewed,
        SUM(CASE WHEN current_status IN ('SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED') THEN 1 ELSE 0 END) AS stage_3_shortlisted,
        SUM(CASE WHEN current_status IN ('INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED') THEN 1 ELSE 0 END) AS stage_4_scheduled,
        SUM(CASE WHEN current_status IN ('INTERVIEWED', 'OFFERED') THEN 1 ELSE 0 END) AS stage_5_interviewed,
        SUM(CASE WHEN current_status = 'OFFERED' THEN 1 ELSE 0 END) AS stage_6_offered
    FROM applications
)
SELECT 
    stage_1_applied,
    stage_2_reviewed,
    ROUND((stage_2_reviewed / stage_1_applied) * 100.0, 1) AS review_rate_pct,
    stage_3_shortlisted,
    ROUND((stage_3_shortlisted / stage_1_applied) * 100.0, 1) AS shortlist_rate_pct,
    stage_4_scheduled,
    ROUND((stage_4_scheduled / stage_1_applied) * 100.0, 1) AS interview_schedule_rate_pct,
    stage_5_interviewed,
    ROUND((stage_5_interviewed / stage_1_applied) * 100.0, 1) AS interview_completed_rate_pct,
    stage_6_offered,
    ROUND((stage_6_offered / stage_1_applied) * 100.0, 1) AS final_offer_rate_pct
FROM funnel_counts;

-- -----------------------------------------------------------------------------
-- Q43: Candidate Application Velocity & Cumulative Timeline
-- Purpose: Track the sequence and running cumulative application count for each candidate.
-- Concepts: Window function COUNT() OVER (PARTITION BY ... ORDER BY ... ROWS UNBOUNDED PRECEDING)
-- -----------------------------------------------------------------------------
SELECT 
    a.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    a.application_id,
    j.title AS applied_job_title,
    a.applied_at,
    ROW_NUMBER() OVER (
        PARTITION BY a.candidate_id 
        ORDER BY a.applied_at ASC
    ) AS application_sequence_num,
    COUNT(a.application_id) OVER (
        PARTITION BY a.candidate_id 
        ORDER BY a.applied_at ASC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_applications_count
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
ORDER BY a.candidate_id ASC, a.applied_at ASC;

-- -----------------------------------------------------------------------------
-- Q44: Interviewer Performance Scorecard & Evaluation Consistency
-- Purpose: Audit evaluation rigor, average ratings, and round completion rate per interviewer.
-- Concepts: GROUP BY with conditional aggregation, AVG, MIN, MAX
-- -----------------------------------------------------------------------------
SELECT 
    interviewer_name,
    COUNT(*) AS total_interviews_assigned,
    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_interviews,
    SUM(CASE WHEN status IN ('SCHEDULED', 'RESCHEDULED') THEN 1 ELSE 0 END) AS pending_interviews,
    ROUND(AVG(rating), 2) AS mean_rating,
    MIN(rating) AS min_rating_given,
    MAX(rating) AS max_rating_given,
    ROUND(SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) / COUNT(rating) * 100.0, 1) AS high_score_pct
FROM interviews
GROUP BY interviewer_name
ORDER BY total_interviews_assigned DESC, mean_rating DESC;

-- -----------------------------------------------------------------------------
-- Q45: Skill Demand Market Share & Cumulative Distribution
-- Purpose: Calculate each skill's percentage share of total job market requirements.
-- Concepts: CTE with window function SUM() OVER () for grand totals
-- -----------------------------------------------------------------------------
WITH skill_counts AS (
    SELECT 
        s.skill_id,
        s.skill_name,
        s.category,
        COUNT(js.job_id) AS demand_frequency
    FROM skills s
    INNER JOIN job_skills js ON s.skill_id = js.skill_id
    GROUP BY s.skill_id, s.skill_name, s.category
)
SELECT 
    skill_name,
    category,
    demand_frequency,
    ROUND((demand_frequency / SUM(demand_frequency) OVER ()) * 100.0, 2) AS market_demand_share_pct,
    DENSE_RANK() OVER (
        ORDER BY demand_frequency DESC
    ) AS demand_rank
FROM skill_counts
ORDER BY demand_rank ASC, skill_name ASC;

-- -----------------------------------------------------------------------------
-- Q46: Candidate-to-Job Skill Gap & Competency Coverage Analysis
-- Purpose: Match candidate profile skills against job requirements to compute matched
--          skills, missing required skills, and overall skill coverage ratio.
-- Concepts: Multi-table CTE comparing job requirements vs candidate inventory
-- -----------------------------------------------------------------------------
WITH job_requisition_summary AS (
    SELECT 
        job_id,
        COUNT(*) AS total_skills_required,
        SUM(CASE WHEN is_required = TRUE THEN 1 ELSE 0 END) AS mandatory_skills_count
    FROM job_skills
    GROUP BY job_id
),
candidate_job_match AS (
    SELECT 
        a.application_id,
        a.job_id,
        a.candidate_id,
        COUNT(cs.skill_id) AS matched_skills_count,
        SUM(CASE WHEN js.is_required = TRUE THEN 1 ELSE 0 END) AS matched_mandatory_skills
    FROM applications a
    INNER JOIN job_skills js ON a.job_id = js.job_id
    INNER JOIN candidate_skills cs ON a.candidate_id = cs.candidate_id AND js.skill_id = cs.skill_id
    GROUP BY a.application_id, a.job_id, a.candidate_id
)
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    jrs.total_skills_required,
    jrs.mandatory_skills_count,
    COALESCE(cjm.matched_skills_count, 0) AS matched_skills_count,
    COALESCE(cjm.matched_mandatory_skills, 0) AS matched_mandatory_skills,
    (jrs.mandatory_skills_count - COALESCE(cjm.matched_mandatory_skills, 0)) AS missing_mandatory_skills,
    ROUND((COALESCE(cjm.matched_skills_count, 0) / jrs.total_skills_required) * 100.0, 1) AS skill_coverage_pct,
    a.match_score AS ats_match_score
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN job_requisition_summary jrs ON j.job_id = jrs.job_id
LEFT JOIN candidate_job_match cjm ON a.application_id = cjm.application_id
ORDER BY ats_match_score DESC, skill_coverage_pct DESC;


-- =============================================================================
-- SECTION F — DATE AND TIME ANALYSIS
-- Demonstrating: DATE, DATE_FORMAT, DAYNAME, DATEDIFF, TIMESTAMPDIFF, LAG()
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q47: Daily Application Intake and Day-of-Week Distribution
-- Purpose: Measure candidate submission patterns across days of the week.
-- Concepts: DAYNAME(), DATE(), COUNT()
-- -----------------------------------------------------------------------------
SELECT 
    DAYNAME(applied_at) AS day_of_week,
    COUNT(*) AS total_applications_submitted,
    ROUND(AVG(match_score), 2) AS avg_match_score
FROM applications
GROUP BY DAYNAME(applied_at), DAYOFWEEK(applied_at)
ORDER BY DAYOFWEEK(applied_at) ASC;

-- -----------------------------------------------------------------------------
-- Q48: Monthly Application Volume and Job Requisition Creation Trend
-- Purpose: Monitor platform monthly velocity for application throughput and job postings.
-- Concepts: DATE_FORMAT(timestamp, '%Y-%m') aggregation
-- -----------------------------------------------------------------------------
SELECT 
    DATE_FORMAT(applied_at, '%Y-%m') AS application_month,
    COUNT(*) AS applications_submitted,
    ROUND(AVG(match_score), 2) AS avg_monthly_match_score
FROM applications
GROUP BY DATE_FORMAT(applied_at, '%Y-%m')
ORDER BY application_month ASC;

-- -----------------------------------------------------------------------------
-- Q49: Job Requisition Urgency and Days Remaining Until Application Deadline
-- Purpose: Classify active jobs by urgency based on calendar days remaining before deadline.
-- Concepts: DATEDIFF(deadline_date, CURRENT_DATE), CASE statement
-- -----------------------------------------------------------------------------
SELECT 
    job_id,
    title,
    location,
    status,
    deadline_date,
    CURRENT_DATE AS today_date,
    DATEDIFF(deadline_date, CURRENT_DATE) AS days_remaining,
    CASE 
        WHEN deadline_date IS NULL THEN 'NO DEADLINE SPECIFIED'
        WHEN DATEDIFF(deadline_date, CURRENT_DATE) < 0 THEN 'EXPIRED'
        WHEN DATEDIFF(deadline_date, CURRENT_DATE) <= 15 THEN 'CRITICAL (<= 15 DAYS)'
        WHEN DATEDIFF(deadline_date, CURRENT_DATE) <= 30 THEN 'URGENT (<= 30 DAYS)'
        ELSE 'OPEN'
    END AS deadline_urgency
FROM jobs
ORDER BY deadline_date ASC;

-- -----------------------------------------------------------------------------
-- Q50: Upcoming Interview Operational Calendar (Next 30 Days)
-- Purpose: Display upcoming interviews scheduled within a 30-day operating window.
-- Concepts: INTERVAL arithmetic with scheduled_at, DATETIME comparisons
-- -----------------------------------------------------------------------------
SELECT 
    i.interview_id,
    i.scheduled_at,
    i.duration_minutes,
    i.round_type,
    i.interviewer_name,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email AS candidate_email,
    j.title AS job_title,
    rp.company_name,
    i.meeting_link,
    i.location
FROM interviews i
INNER JOIN applications a ON i.application_id = a.application_id
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
WHERE i.status IN ('SCHEDULED', 'RESCHEDULED')
  AND i.scheduled_at >= '2026-11-01 00:00:00'
ORDER BY i.scheduled_at ASC;

-- -----------------------------------------------------------------------------
-- Q51: Past Completed Interviews Duration and Evaluation Audit
-- Purpose: Review concluded interview rounds with elapsed days and feedback ratings.
-- Concepts: DATEDIFF, duration calculation, rating distribution
-- -----------------------------------------------------------------------------
SELECT 
    i.interview_id,
    i.interviewer_name,
    i.round_type,
    i.scheduled_at,
    i.duration_minutes,
    i.rating,
    DATEDIFF(CURRENT_TIMESTAMP, i.scheduled_at) AS days_since_interview,
    i.feedback
FROM interviews i
WHERE i.status = 'COMPLETED'
ORDER BY i.scheduled_at DESC;

-- -----------------------------------------------------------------------------
-- Q52: Application Velocity & Time Elapsed Since Latest Update
-- Purpose: Compute total hours elapsed between application creation and latest update.
-- Concepts: TIMESTAMPDIFF(HOUR, applied_at, updated_at)
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    a.current_status,
    a.applied_at,
    a.updated_at,
    TIMESTAMPDIFF(HOUR, a.applied_at, a.updated_at) AS hours_in_pipeline,
    TIMESTAMPDIFF(DAY, a.applied_at, a.updated_at) AS days_in_pipeline
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
ORDER BY a.applied_at ASC;

-- -----------------------------------------------------------------------------
-- Q53: Audit Trail Transition Duration Between Status Changes
-- Purpose: Calculate exact hours spent in each pipeline state using the LAG() window function.
-- Concepts: LAG() OVER (PARTITION BY ... ORDER BY ...), TIMESTAMPDIFF()
-- -----------------------------------------------------------------------------
SELECT 
    h.application_id,
    h.history_id,
    h.old_status,
    h.new_status,
    h.change_notes,
    h.changed_at,
    LAG(h.changed_at) OVER (
        PARTITION BY h.application_id 
        ORDER BY h.changed_at ASC
    ) AS prior_state_changed_at,
    TIMESTAMPDIFF(
        MINUTE,
        LAG(h.changed_at) OVER (PARTITION BY h.application_id ORDER BY h.changed_at ASC),
        h.changed_at
    ) AS minutes_in_prior_state
FROM application_status_history h
ORDER BY h.application_id ASC, h.changed_at ASC;


-- =============================================================================
-- SECTION G — ATS BUSINESS INTELLIGENCE & REPORTING SUITE
-- Demonstrating: End-to-end operational reports for Candidates, Recruiters & Admins
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q54: Candidate Application 360° Summary Report
-- Purpose: Enterprise executive summary of each candidate's career portal engagement.
-- Concepts: Aggregating candidate submissions, offer counts, and average match scores
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email AS candidate_email,
    cp.headline,
    cp.years_of_experience,
    COUNT(a.application_id) AS total_applications_submitted,
    SUM(CASE WHEN a.current_status = 'OFFERED' THEN 1 ELSE 0 END) AS offers_received,
    SUM(CASE WHEN a.current_status = 'REJECTED' THEN 1 ELSE 0 END) AS rejections_received,
    SUM(CASE WHEN a.current_status NOT IN ('OFFERED', 'REJECTED', 'WITHDRAWN') THEN 1 ELSE 0 END) AS active_in_pipeline,
    ROUND(AVG(a.match_score), 2) AS overall_avg_match_score
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
LEFT JOIN applications a ON cp.candidate_id = a.candidate_id
GROUP BY cp.candidate_id, u.first_name, u.last_name, u.email, cp.headline, cp.years_of_experience
ORDER BY offers_received DESC, overall_avg_match_score DESC;

-- -----------------------------------------------------------------------------
-- Q55: Candidate Job Application History & Status Log
-- Purpose: Complete personal application timeline for candidate tracking.
-- Concepts: Chronological history join
-- -----------------------------------------------------------------------------
SELECT 
    a.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    j.title AS job_title,
    rp.company_name,
    j.location,
    j.employment_type,
    a.current_status,
    a.match_score,
    a.applied_at
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
ORDER BY a.candidate_id ASC, a.applied_at DESC;

-- -----------------------------------------------------------------------------
-- Q56: Comprehensive Job Requisition Performance Report
-- Purpose: Deep-dive operational dashboard for job openings, status breakdown, and ATS scores.
-- Concepts: Multi-table conditional aggregation across all 8 pipeline statuses
-- -----------------------------------------------------------------------------
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    j.status AS requisition_status,
    COUNT(a.application_id) AS total_applicants,
    ROUND(AVG(a.match_score), 2) AS avg_match_score,
    SUM(CASE WHEN a.current_status = 'APPLIED' THEN 1 ELSE 0 END) AS count_applied,
    SUM(CASE WHEN a.current_status = 'UNDER_REVIEW' THEN 1 ELSE 0 END) AS count_under_review,
    SUM(CASE WHEN a.current_status = 'SHORTLISTED' THEN 1 ELSE 0 END) AS count_shortlisted,
    SUM(CASE WHEN a.current_status = 'INTERVIEW_SCHEDULED' THEN 1 ELSE 0 END) AS count_interview_scheduled,
    SUM(CASE WHEN a.current_status = 'INTERVIEWED' THEN 1 ELSE 0 END) AS count_interviewed,
    SUM(CASE WHEN a.current_status = 'OFFERED' THEN 1 ELSE 0 END) AS count_offered,
    SUM(CASE WHEN a.current_status = 'REJECTED' THEN 1 ELSE 0 END) AS count_rejected,
    SUM(CASE WHEN a.current_status = 'WITHDRAWN' THEN 1 ELSE 0 END) AS count_withdrawn
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN users u ON rp.user_id = u.user_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY j.job_id, j.title, rp.company_name, u.first_name, u.last_name, j.status
ORDER BY total_applicants DESC, avg_match_score DESC;

-- -----------------------------------------------------------------------------
-- Q57: Recruiter Productivity & Talent Conversion Report
-- Purpose: Assess recruiter talent funnel velocity from requisition posting to formal hire offer.
-- Concepts: Pre-aggregated CTEs to prevent join fan-out, pipeline conversion calculation
-- -----------------------------------------------------------------------------
WITH recruiter_apps AS (
    SELECT 
        j.recruiter_id,
        COUNT(DISTINCT j.job_id) AS jobs_posted,
        COUNT(DISTINCT a.application_id) AS total_applications_handled,
        SUM(CASE WHEN a.current_status = 'OFFERED' THEN 1 ELSE 0 END) AS total_offers_extended
    FROM jobs j
    LEFT JOIN applications a ON j.job_id = a.job_id
    GROUP BY j.recruiter_id
),
recruiter_interviews AS (
    SELECT 
        j.recruiter_id,
        COUNT(DISTINCT i.interview_id) AS total_interviews_generated
    FROM jobs j
    INNER JOIN applications a ON j.job_id = a.job_id
    INNER JOIN interviews i ON a.application_id = i.application_id
    GROUP BY j.recruiter_id
)
SELECT 
    rp.recruiter_id,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    rp.company_name,
    COALESCE(ra.jobs_posted, 0) AS jobs_posted,
    COALESCE(ra.total_applications_handled, 0) AS total_applications_handled,
    COALESCE(ri.total_interviews_generated, 0) AS total_interviews_generated,
    COALESCE(ra.total_offers_extended, 0) AS total_offers_extended,
    ROUND(
        CASE 
            WHEN COALESCE(ra.total_applications_handled, 0) = 0 THEN 0.00
            ELSE (COALESCE(ra.total_offers_extended, 0) / ra.total_applications_handled) * 100.00
        END, 2
    ) AS application_to_offer_conversion_pct
FROM recruiter_profiles rp
INNER JOIN users u ON rp.user_id = u.user_id
LEFT JOIN recruiter_apps ra ON rp.recruiter_id = ra.recruiter_id
LEFT JOIN recruiter_interviews ri ON rp.recruiter_id = ri.recruiter_id
ORDER BY total_offers_extended DESC, total_applications_handled DESC;

-- -----------------------------------------------------------------------------
-- Q58: Platform-Wide Recruitment Funnel Report
-- Purpose: Standard executive report tracking funnel conversion drop-off from intake to hire.
-- Concepts: Subquery CTE with stage-to-stage percentage calculation
-- -----------------------------------------------------------------------------
WITH stage_summary AS (
    SELECT 
        COUNT(*) AS total_applications,
        SUM(CASE WHEN current_status NOT IN ('APPLIED') THEN 1 ELSE 0 END) AS progressed_past_applied,
        SUM(CASE WHEN current_status IN ('SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED') THEN 1 ELSE 0 END) AS reached_shortlist,
        SUM(CASE WHEN current_status IN ('INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED') THEN 1 ELSE 0 END) AS reached_interview_stage,
        SUM(CASE WHEN current_status IN ('OFFERED') THEN 1 ELSE 0 END) AS reached_offer_stage
    FROM applications
)
SELECT 
    total_applications AS total_submissions,
    progressed_past_applied AS under_review_or_later,
    ROUND((progressed_past_applied / total_applications) * 100.0, 1) AS review_conversion_pct,
    reached_shortlist AS shortlisted_or_later,
    ROUND((reached_shortlist / total_applications) * 100.0, 1) AS shortlist_conversion_pct,
    reached_interview_stage AS interview_scheduled_or_later,
    ROUND((reached_interview_stage / total_applications) * 100.0, 1) AS interview_conversion_pct,
    reached_offer_stage AS offered_employment,
    ROUND((reached_offer_stage / total_applications) * 100.0, 1) AS offer_conversion_pct
FROM stage_summary;

-- -----------------------------------------------------------------------------
-- Q59: Master Interview Pipeline & Operational Schedule
-- Purpose: Full operational view of scheduled interviews for talent coordination teams.
-- Concepts: Comprehensive multi-table interview join
-- -----------------------------------------------------------------------------
SELECT 
    i.interview_id,
    i.scheduled_at,
    i.round_number,
    i.round_type,
    i.interviewer_name,
    CONCAT(u_cand.first_name, ' ', u_cand.last_name) AS candidate_name,
    u_cand.email AS candidate_email,
    u_cand.phone AS candidate_phone,
    j.title AS job_title,
    rp.company_name,
    i.duration_minutes,
    i.meeting_link,
    i.location,
    i.status AS interview_status
FROM interviews i
INNER JOIN applications a ON i.application_id = a.application_id
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u_cand ON cp.user_id = u_cand.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
WHERE i.status IN ('SCHEDULED', 'RESCHEDULED')
ORDER BY i.scheduled_at ASC;

-- -----------------------------------------------------------------------------
-- Q60: Market Skill Demand vs Candidate Pool Supply Gap Analysis
-- Purpose: Contrast the percentage of job requisitions requesting a skill against
--          the percentage of candidates possessing that skill to reveal talent shortages.
-- Concepts: Two independent CTEs joined on master skill entity with gap indicator
-- -----------------------------------------------------------------------------
WITH total_counts AS (
    SELECT 
        (SELECT COUNT(*) FROM jobs) AS total_jobs,
        (SELECT COUNT(*) FROM candidate_profiles) AS total_candidates
    FROM DUAL
),
job_demand AS (
    SELECT 
        skill_id, 
        COUNT(DISTINCT job_id) AS demanding_jobs_count
    FROM job_skills
    GROUP BY skill_id
),
candidate_supply AS (
    SELECT 
        skill_id, 
        COUNT(DISTINCT candidate_id) AS possessing_candidates_count
    FROM candidate_skills
    GROUP BY skill_id
)
SELECT 
    s.skill_id,
    s.skill_name,
    s.category,
    COALESCE(jd.demanding_jobs_count, 0) AS jobs_requiring,
    ROUND((COALESCE(jd.demanding_jobs_count, 0) / tc.total_jobs) * 100.0, 1) AS job_demand_pct,
    COALESCE(cs.possessing_candidates_count, 0) AS candidates_available,
    ROUND((COALESCE(cs.possessing_candidates_count, 0) / tc.total_candidates) * 100.0, 1) AS talent_supply_pct,
    ROUND(
        ((COALESCE(jd.demanding_jobs_count, 0) / tc.total_jobs) * 100.0) -
        ((COALESCE(cs.possessing_candidates_count, 0) / tc.total_candidates) * 100.0), 1
    ) AS demand_supply_gap_pct
FROM skills s
CROSS JOIN total_counts tc
LEFT JOIN job_demand jd ON s.skill_id = jd.skill_id
LEFT JOIN candidate_supply cs ON s.skill_id = cs.skill_id
ORDER BY demand_supply_gap_pct DESC, jobs_requiring DESC;

-- -----------------------------------------------------------------------------
-- Q61: Executive Talent Search Query (Multi-Skill Matching)
-- Purpose: Identify elite candidates holding simultaneous competency in Python, MySQL, and Docker.
-- Concepts: Relational division using GROUP BY and HAVING COUNT(DISTINCT skill)
-- -----------------------------------------------------------------------------
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email,
    cp.headline,
    cp.current_location,
    cp.years_of_experience,
    GROUP_CONCAT(CONCAT(s.skill_name, ' (', cs.proficiency_level, ')') ORDER BY s.skill_name SEPARATOR ', ') AS matched_skills
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN candidate_skills cs ON cp.candidate_id = cs.candidate_id
INNER JOIN skills s ON cs.skill_id = s.skill_id
WHERE s.skill_name IN ('Python', 'MySQL', 'Docker')
GROUP BY cp.candidate_id, u.first_name, u.last_name, u.email, cp.headline, cp.current_location, cp.years_of_experience
HAVING COUNT(DISTINCT s.skill_name) = 3
ORDER BY cp.years_of_experience DESC;


-- =============================================================================
-- SECTION H — DATA VALIDATION & INTEGRITY AUDITING QUERIES
-- Demonstrating: Verification of schema integrity, Phase 2 procedural invariants,
--                resume ownership rules, boundary checks, and orphan detection
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q62: Resume Ownership Integrity Audit
-- Purpose: Confirm that all applications strictly reference resumes belonging to the applicant.
-- Expected Outcome: 0 rows (A violation indicates unauthorized resume attachment).
-- Concepts: Integrity check joining applications with resumes on mismatched candidate_id
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    a.candidate_id AS application_candidate_id,
    r.candidate_id AS resume_owner_candidate_id,
    a.resume_id,
    r.file_name
FROM applications a
INNER JOIN resumes r ON a.resume_id = r.resume_id
WHERE a.candidate_id <> r.candidate_id;

-- -----------------------------------------------------------------------------
-- Q63: Duplicate Application Integrity Check
-- Purpose: Verify that no candidate has multiple applications for the same job requisition.
-- Expected Outcome: 0 rows (Guaranteed by unique constraint uq_job_candidate).
-- Concepts: HAVING COUNT(*) > 1 violation detection
-- -----------------------------------------------------------------------------
SELECT 
    job_id,
    candidate_id,
    COUNT(*) AS duplicate_count
FROM applications
GROUP BY job_id, candidate_id
HAVING COUNT(*) > 1;

-- -----------------------------------------------------------------------------
-- Q64: Match Score Boundary Integrity Check
-- Purpose: Verify that all calculated ATS match scores strictly fall in the range [0.00, 100.00].
-- Expected Outcome: 0 rows (Guaranteed by CHECK constraint chk_app_match_score).
-- Concepts: Boundary validation
-- -----------------------------------------------------------------------------
SELECT 
    application_id,
    job_id,
    candidate_id,
    match_score
FROM applications
WHERE match_score < 0.00 OR match_score > 100.00;

-- -----------------------------------------------------------------------------
-- Q65: Status History Audit Consistency Check
-- Purpose: Ensure every application has an initial audit log record and latest status alignment.
-- Expected Outcome: 0 rows with missing history records.
-- Concepts: LEFT JOIN audit history checking for orphan applications without audit log
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    a.current_status,
    COUNT(h.history_id) AS total_history_records
FROM applications a
LEFT JOIN application_status_history h ON a.application_id = h.application_id
GROUP BY a.application_id, a.current_status
HAVING COUNT(h.history_id) = 0;

-- -----------------------------------------------------------------------------
-- Q66: Interviewer Calendar Overlap Conflict Audit
-- Purpose: Detect any invalid overlapping active interviews for the SAME interviewer.
-- Expected Outcome: 0 rows (Confirms sp_schedule_interview and triggers work as intended).
-- Concepts: Self-join on interviews with active status, same interviewer, and overlapping time
-- -----------------------------------------------------------------------------
SELECT 
    i1.interview_id AS interview_1_id,
    i2.interview_id AS interview_2_id,
    i1.interviewer_name,
    i1.scheduled_at AS int1_start,
    i1.scheduled_at + INTERVAL i1.duration_minutes MINUTE AS int1_end,
    i2.scheduled_at AS int2_start,
    i2.scheduled_at + INTERVAL i2.duration_minutes MINUTE AS int2_end
FROM interviews i1
INNER JOIN interviews i2 
    ON i1.interviewer_name = i2.interviewer_name
   AND i1.interview_id < i2.interview_id
   AND i1.status IN ('SCHEDULED', 'RESCHEDULED')
   AND i2.status IN ('SCHEDULED', 'RESCHEDULED')
   AND (i1.scheduled_at < i2.scheduled_at + INTERVAL i2.duration_minutes MINUTE)
   AND (i2.scheduled_at < i1.scheduled_at + INTERVAL i1.duration_minutes MINUTE);

-- -----------------------------------------------------------------------------
-- Q67: Orphan Profile & Referential Integrity Check
-- Purpose: Verify that candidate and recruiter profiles always have corresponding user accounts.
-- Expected Outcome: 0 rows (Enforced by foreign keys fk_candidate_users and fk_recruiter_users).
-- Concepts: LEFT JOIN checking for NULL parent foreign key references
-- -----------------------------------------------------------------------------
SELECT 
    'Candidate Profile' AS profile_type,
    cp.candidate_id AS profile_id,
    cp.user_id
FROM candidate_profiles cp
LEFT JOIN users u ON cp.user_id = u.user_id
WHERE u.user_id IS NULL
UNION ALL
SELECT 
    'Recruiter Profile' AS profile_type,
    rp.recruiter_id AS profile_id,
    rp.user_id
FROM recruiter_profiles rp
LEFT JOIN users u ON rp.user_id = u.user_id
WHERE u.user_id IS NULL;

-- -----------------------------------------------------------------------------
-- Q68: Application Deadline Compliance Audit
-- Purpose: Audit whether any application was recorded after the job requisition's deadline date.
-- Expected Outcome: 0 rows (Enforced by procedural validation in sp_apply_job).
-- Concepts: Date comparison between applied_at timestamp and job deadline_date
-- -----------------------------------------------------------------------------
SELECT 
    a.application_id,
    a.job_id,
    j.title AS job_title,
    j.deadline_date,
    DATE(a.applied_at) AS date_applied,
    DATEDIFF(DATE(a.applied_at), j.deadline_date) AS days_late
FROM applications a
INNER JOIN jobs j ON a.job_id = j.job_id
WHERE j.deadline_date IS NOT NULL
  AND DATE(a.applied_at) > j.deadline_date;
