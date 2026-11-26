-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: security.sql (Phase 4: Least-Privilege Database User Strategy)
-- Description: Creates dedicated least-privilege application and reporting
--              accounts without modifying any Phase 1 tables, triggers,
--              procedures, functions, or Phase 3 views.
-- IMPORTANT: Replace placeholder passwords before running in any non-local environment.
-- =============================================================================

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- 1. Least-Privilege Flask Application Runtime Account
--    Required privileges:
--      - SELECT, INSERT, UPDATE on job_portal_ats.* (data & view access)
--      - EXECUTE on job_portal_ats.* (Phase 2 stored procedures & functions)
--      - DELETE restricted strictly to candidate-managed child tables
--    Explicitly withheld:
--      - DROP, ALTER, CREATE, INDEX, REFERENCES, TRIGGER, SUPER, GRANT OPTION
-- -----------------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'ats_app_user'@'localhost'
    IDENTIFIED BY 'CHANGE_ME_STRONG_APP_PASSWORD';

REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'ats_app_user'@'localhost';

GRANT SELECT, INSERT, UPDATE, EXECUTE
    ON job_portal_ats.*
    TO 'ats_app_user'@'localhost';

GRANT DELETE ON job_portal_ats.resumes TO 'ats_app_user'@'localhost';
GRANT DELETE ON job_portal_ats.candidate_skills TO 'ats_app_user'@'localhost';
GRANT DELETE ON job_portal_ats.job_skills TO 'ats_app_user'@'localhost';

-- -----------------------------------------------------------------------------
-- 2. Read-Only Reporting / Analytics Account (Phase 3 Views & Audits)
-- -----------------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'ats_report_user'@'localhost'
    IDENTIFIED BY 'CHANGE_ME_STRONG_REPORT_PASSWORD';

REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'ats_report_user'@'localhost';

GRANT SELECT ON job_portal_ats.vw_candidate_application_dashboard TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_recruiter_job_performance TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_application_funnel TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_interview_schedule TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_job_skill_requirements TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_candidate_skill_profile TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_job_application_statistics TO 'ats_report_user'@'localhost';
GRANT SELECT ON job_portal_ats.vw_candidate_application_statistics TO 'ats_report_user'@'localhost';

FLUSH PRIVILEGES;

