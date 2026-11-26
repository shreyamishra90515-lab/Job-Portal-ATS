-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: views.sql (Phase 3: Database Views & Reporting Layer)
-- Description: Production-ready reporting and analytical views encapsulating
--              business logic for candidate portals, recruiter dashboards,
--              interview pipelines, and ATS executive metrics.
-- Prerequisites: schema.sql, functions.sql, procedures.sql, triggers.sql,
--                and sample_data.sql.
-- Note: Views are completely non-destructive and operate on approved schema tables.
-- =============================================================================

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- View 1: vw_candidate_application_dashboard
-- Description: Central portal view for candidates and recruiters displaying
--              comprehensive application status, matching scores, and attached
--              verified resumes.
-- Reusability: Powers candidate "My Applications" dashboard and recruiter pipeline views.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_candidate_application_dashboard AS
SELECT 
    a.application_id,
    a.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email AS candidate_email,
    cp.headline AS candidate_headline,
    cp.years_of_experience AS candidate_experience,
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    j.location AS job_location,
    j.employment_type,
    j.workplace_type,
    a.applied_at,
    a.current_status,
    a.match_score,
    r.resume_id,
    r.file_name AS resume_file_name,
    r.is_primary AS is_primary_resume
FROM applications a
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN resumes r ON a.resume_id = r.resume_id;

-- -----------------------------------------------------------------------------
-- View 2: vw_recruiter_job_performance
-- Description: Performance and throughput metrics for job requisitions managed
--              by corporate recruiters, summarizing application volumes, match
--              quality, interview volume, and offers extended.
-- Reusability: Powers the recruiter job management screen and performance audits.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_recruiter_job_performance AS
WITH job_app_stats AS (
    SELECT 
        job_id,
        COUNT(application_id) AS total_applications,
        ROUND(AVG(match_score), 2) AS avg_match_score,
        SUM(CASE WHEN current_status = 'OFFERED' THEN 1 ELSE 0 END) AS total_offers
    FROM applications
    GROUP BY job_id
),
job_interview_stats AS (
    SELECT 
        a.job_id,
        COUNT(i.interview_id) AS total_interviews
    FROM applications a
    INNER JOIN interviews i ON a.application_id = i.application_id
    GROUP BY a.job_id
)
SELECT 
    rp.recruiter_id,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    rp.company_name,
    rp.designation AS recruiter_designation,
    j.job_id,
    j.title AS job_title,
    j.status AS job_status,
    j.employment_type,
    j.workplace_type,
    j.min_experience_years,
    j.salary_min,
    j.salary_max,
    j.deadline_date,
    COALESCE(jas.total_applications, 0) AS total_applications,
    jas.avg_match_score,
    COALESCE(jis.total_interviews, 0) AS total_interviews,
    COALESCE(jas.total_offers, 0) AS total_offers
FROM recruiter_profiles rp
INNER JOIN users u ON rp.user_id = u.user_id
INNER JOIN jobs j ON rp.recruiter_id = j.recruiter_id
LEFT JOIN job_app_stats jas ON j.job_id = jas.job_id
LEFT JOIN job_interview_stats jis ON j.job_id = jis.job_id;

-- -----------------------------------------------------------------------------
-- View 3: vw_application_funnel
-- Description: Platform-wide recruitment funnel showing candidate distribution
--              and percentage share across the standard 8 application stages.
-- Reusability: Powers ATS executive drop-off dashboards and pipeline visualizers.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_application_funnel AS
WITH total_count AS (
    SELECT COUNT(*) AS total_apps FROM applications
),
status_counts AS (
    SELECT 
        current_status,
        COUNT(*) AS applicant_count
    FROM applications
    GROUP BY current_status
)
SELECT 
    CASE sc.current_status
        WHEN 'APPLIED' THEN 1
        WHEN 'UNDER_REVIEW' THEN 2
        WHEN 'SHORTLISTED' THEN 3
        WHEN 'INTERVIEW_SCHEDULED' THEN 4
        WHEN 'INTERVIEWED' THEN 5
        WHEN 'OFFERED' THEN 6
        WHEN 'REJECTED' THEN 7
        WHEN 'WITHDRAWN' THEN 8
        ELSE 9
    END AS stage_order,
    sc.current_status AS application_status,
    sc.applicant_count,
    ROUND((sc.applicant_count / tc.total_apps) * 100.0, 2) AS pct_of_total_applications
FROM status_counts sc
CROSS JOIN total_count tc;

-- -----------------------------------------------------------------------------
-- View 4: vw_interview_schedule
-- Description: Operational interview schedule tracking scheduled, in-progress,
--              and completed rounds with interviewer identity, candidate contact
--              info, platform location links, and post-round evaluation ratings.
-- Reusability: Powers recruiter calendar coordination and interviewer schedules.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_interview_schedule AS
SELECT 
    i.interview_id,
    i.application_id,
    cp.candidate_id,
    CONCAT(u_cand.first_name, ' ', u_cand.last_name) AS candidate_name,
    u_cand.email AS candidate_email,
    u_cand.phone AS candidate_phone,
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    i.interviewer_name,
    i.round_number,
    i.round_type,
    i.scheduled_at,
    i.duration_minutes,
    i.meeting_link,
    i.location,
    i.status AS interview_status,
    i.feedback,
    i.rating
FROM interviews i
INNER JOIN applications a ON i.application_id = a.application_id
INNER JOIN candidate_profiles cp ON a.candidate_id = cp.candidate_id
INNER JOIN users u_cand ON cp.user_id = u_cand.user_id
INNER JOIN jobs j ON a.job_id = j.job_id
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id;

-- -----------------------------------------------------------------------------
-- View 5: vw_job_skill_requirements
-- Description: Normalized view of all job openings linked to their skill requisitions,
--              classifying skills as MANDATORY or PREFERRED along with required experience.
-- Reusability: Powers job detail pages and automated skill-gap matching algorithms.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_job_skill_requirements AS
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    j.status AS job_status,
    s.skill_id,
    s.skill_name,
    s.category AS skill_category,
    js.is_required,
    CASE WHEN js.is_required = TRUE THEN 'MANDATORY' ELSE 'PREFERRED' END AS requirement_type,
    js.min_years_experience
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN job_skills js ON j.job_id = js.job_id
INNER JOIN skills s ON js.skill_id = s.skill_id;

-- -----------------------------------------------------------------------------
-- View 6: vw_candidate_skill_profile
-- Description: Standardized view of candidate talent profiles and skill matrices,
--              featuring categorized skills, verified years of experience, and
--              proficiency rankings (BEGINNER to EXPERT).
-- Reusability: Powers candidate profile views and recruiter candidate-search engines.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_candidate_skill_profile AS
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email AS candidate_email,
    cp.current_location,
    cp.years_of_experience AS total_experience_years,
    cp.highest_education,
    s.skill_id,
    s.skill_name,
    s.category AS skill_category,
    cs.proficiency_level,
    cs.years_of_experience AS skill_experience_years
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
INNER JOIN candidate_skills cs ON cp.candidate_id = cs.candidate_id
INNER JOIN skills s ON cs.skill_id = s.skill_id;

-- -----------------------------------------------------------------------------
-- View 7: vw_job_application_statistics
-- Description: Aggregated analytics for job openings detailing applicant volume,
--              ATS match score distribution (min, max, avg), and stage-by-stage
--              candidate pipeline counts.
-- Reusability: Powers recruiter job requisition performance tables and analytics.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_job_application_statistics AS
SELECT 
    j.job_id,
    j.title AS job_title,
    rp.company_name,
    CONCAT(u.first_name, ' ', u.last_name) AS recruiter_name,
    j.status AS job_status,
    j.employment_type,
    j.workplace_type,
    j.salary_min,
    j.salary_max,
    COUNT(a.application_id) AS total_applications,
    MIN(a.match_score) AS min_match_score,
    MAX(a.match_score) AS max_match_score,
    ROUND(AVG(a.match_score), 2) AS avg_match_score,
    SUM(CASE WHEN a.current_status = 'APPLIED' THEN 1 ELSE 0 END) AS applied_count,
    SUM(CASE WHEN a.current_status = 'UNDER_REVIEW' THEN 1 ELSE 0 END) AS under_review_count,
    SUM(CASE WHEN a.current_status = 'SHORTLISTED' THEN 1 ELSE 0 END) AS shortlisted_count,
    SUM(CASE WHEN a.current_status = 'INTERVIEW_SCHEDULED' THEN 1 ELSE 0 END) AS interview_scheduled_count,
    SUM(CASE WHEN a.current_status = 'INTERVIEWED' THEN 1 ELSE 0 END) AS interviewed_count,
    SUM(CASE WHEN a.current_status = 'OFFERED' THEN 1 ELSE 0 END) AS offered_count,
    SUM(CASE WHEN a.current_status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_count,
    SUM(CASE WHEN a.current_status = 'WITHDRAWN' THEN 1 ELSE 0 END) AS withdrawn_count
FROM jobs j
INNER JOIN recruiter_profiles rp ON j.recruiter_id = rp.recruiter_id
INNER JOIN users u ON rp.user_id = u.user_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY 
    j.job_id, j.title, rp.company_name, u.first_name, u.last_name,
    j.status, j.employment_type, j.workplace_type, j.salary_min, j.salary_max;

-- -----------------------------------------------------------------------------
-- View 8: vw_candidate_application_statistics
-- Description: Comprehensive candidate analytics detailing individual applicant
--              engagement, total submissions, active opportunities, average
--              match percentages, completed interviews, and offer conversion.
-- Reusability: Powers candidate summary cards and talent pool analytics.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_candidate_application_statistics AS
WITH cand_app_stats AS (
    SELECT 
        candidate_id,
        COUNT(application_id) AS total_applications,
        SUM(CASE WHEN current_status NOT IN ('REJECTED', 'WITHDRAWN') THEN 1 ELSE 0 END) AS active_applications,
        ROUND(AVG(match_score), 2) AS avg_match_score,
        MAX(match_score) AS highest_match_score,
        SUM(CASE WHEN current_status = 'OFFERED' THEN 1 ELSE 0 END) AS offers_received,
        SUM(CASE WHEN current_status = 'REJECTED' THEN 1 ELSE 0 END) AS rejections_received
    FROM applications
    GROUP BY candidate_id
),
cand_interview_stats AS (
    SELECT 
        a.candidate_id,
        COUNT(i.interview_id) AS total_interviews
    FROM applications a
    INNER JOIN interviews i ON a.application_id = i.application_id
    GROUP BY a.candidate_id
)
SELECT 
    cp.candidate_id,
    CONCAT(u.first_name, ' ', u.last_name) AS candidate_name,
    u.email AS candidate_email,
    cp.headline,
    cp.years_of_experience,
    cp.highest_education,
    COALESCE(cas.total_applications, 0) AS total_applications,
    COALESCE(cas.active_applications, 0) AS active_applications,
    cas.avg_match_score,
    cas.highest_match_score,
    COALESCE(cis.total_interviews, 0) AS total_interviews,
    COALESCE(cas.offers_received, 0) AS offers_received,
    COALESCE(cas.rejections_received, 0) AS rejections_received
FROM candidate_profiles cp
INNER JOIN users u ON cp.user_id = u.user_id
LEFT JOIN cand_app_stats cas ON cp.candidate_id = cas.candidate_id
LEFT JOIN cand_interview_stats cis ON cp.candidate_id = cis.candidate_id;
