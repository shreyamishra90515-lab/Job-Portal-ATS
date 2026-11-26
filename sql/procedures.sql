-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: procedures.sql (Phase 2: Stored Procedures)
-- Description: ACID transactional workflows for user registration, job applications,
--              status lifecycle management, and interview scheduling.
-- Prerequisites: schema.sql and functions.sql must be executed first.
-- =============================================================================

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- 1. sp_register_candidate
-- Description: Registers a new candidate by atomically creating records in
--              `users` and `candidate_profiles` within a rollback-safe transaction.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_register_candidate;

DELIMITER $$

CREATE PROCEDURE sp_register_candidate(
    IN p_email VARCHAR(255),
    IN p_password_hash VARCHAR(255),
    IN p_first_name VARCHAR(100),
    IN p_last_name VARCHAR(100),
    IN p_phone VARCHAR(20),
    IN p_headline VARCHAR(255),
    IN p_summary TEXT,
    IN p_current_location VARCHAR(150),
    IN p_years_of_experience DECIMAL(4, 1),
    IN p_highest_education VARCHAR(100),
    IN p_linkedin_url VARCHAR(255),
    IN p_portfolio_url VARCHAR(255),
    OUT p_user_id INT,
    OUT p_candidate_id INT
)
BEGIN
    DECLARE v_role_id INT DEFAULT NULL;
    DECLARE v_email_count INT DEFAULT 0;

    -- Rollback handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- Input Validation
    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Email is required.';
    END IF;

    IF p_password_hash IS NULL OR TRIM(p_password_hash) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Password hash is required.';
    END IF;

    IF p_first_name IS NULL OR TRIM(p_first_name) = '' OR p_last_name IS NULL OR TRIM(p_last_name) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: First name and last name are required.';
    END IF;

    IF p_years_of_experience IS NOT NULL AND p_years_of_experience < 0.0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Years of experience must be non-negative.';
    END IF;

    -- Prevent duplicate email registration
    SELECT COUNT(*) INTO v_email_count FROM users WHERE email = p_email;
    IF v_email_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Duplicate Error: Email is already registered.';
    END IF;

    -- Lookup CANDIDATE role_id
    SELECT role_id INTO v_role_id FROM roles WHERE role_name = 'CANDIDATE';
    IF v_role_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Configuration Error: CANDIDATE role not found in roles table.';
    END IF;

    -- Transactional execution
    START TRANSACTION;
        INSERT INTO users (
            role_id, email, password_hash, first_name, last_name, phone, is_active
        ) VALUES (
            v_role_id, p_email, p_password_hash, p_first_name, p_last_name, p_phone, TRUE
        );
        SET p_user_id = LAST_INSERT_ID();

        INSERT INTO candidate_profiles (
            user_id, headline, summary, current_location, years_of_experience,
            highest_education, linkedin_url, portfolio_url
        ) VALUES (
            p_user_id, p_headline, p_summary, p_current_location,
            COALESCE(p_years_of_experience, 0.0), p_highest_education,
            p_linkedin_url, p_portfolio_url
        );
        SET p_candidate_id = LAST_INSERT_ID();
    COMMIT;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 2. sp_register_recruiter
-- Description: Registers a new recruiter by atomically creating records in
--              `users` and `recruiter_profiles` within a transaction.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_register_recruiter;

DELIMITER $$

CREATE PROCEDURE sp_register_recruiter(
    IN p_email VARCHAR(255),
    IN p_password_hash VARCHAR(255),
    IN p_first_name VARCHAR(100),
    IN p_last_name VARCHAR(100),
    IN p_phone VARCHAR(20),
    IN p_company_name VARCHAR(150),
    IN p_company_website VARCHAR(255),
    IN p_department VARCHAR(100),
    IN p_designation VARCHAR(100),
    IN p_office_location VARCHAR(150),
    OUT p_user_id INT,
    OUT p_recruiter_id INT
)
BEGIN
    DECLARE v_role_id INT DEFAULT NULL;
    DECLARE v_email_count INT DEFAULT 0;

    -- Rollback handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- Input Validation
    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Email is required.';
    END IF;

    IF p_password_hash IS NULL OR TRIM(p_password_hash) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Password hash is required.';
    END IF;

    IF p_first_name IS NULL OR TRIM(p_first_name) = '' OR p_last_name IS NULL OR TRIM(p_last_name) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: First name and last name are required.';
    END IF;

    IF p_company_name IS NULL OR TRIM(p_company_name) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Company name is required for recruiter registration.';
    END IF;

    -- Prevent duplicate email registration
    SELECT COUNT(*) INTO v_email_count FROM users WHERE email = p_email;
    IF v_email_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Duplicate Error: Email is already registered.';
    END IF;

    -- Lookup RECRUITER role_id
    SELECT role_id INTO v_role_id FROM roles WHERE role_name = 'RECRUITER';
    IF v_role_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Configuration Error: RECRUITER role not found in roles table.';
    END IF;

    -- Transactional execution
    START TRANSACTION;
        INSERT INTO users (
            role_id, email, password_hash, first_name, last_name, phone, is_active
        ) VALUES (
            v_role_id, p_email, p_password_hash, p_first_name, p_last_name, p_phone, TRUE
        );
        SET p_user_id = LAST_INSERT_ID();

        INSERT INTO recruiter_profiles (
            user_id, company_name, company_website, department, designation, office_location
        ) VALUES (
            p_user_id, p_company_name, p_company_website, p_department, p_designation, p_office_location
        );
        SET p_recruiter_id = LAST_INSERT_ID();
    COMMIT;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 3. sp_apply_job
-- Description: Submits a candidate job application, enforces resume ownership,
--              calculates ATS match percentage, and initiates the audit trail.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_apply_job;

DELIMITER $$

CREATE PROCEDURE sp_apply_job(
    IN p_job_id INT,
    IN p_candidate_id INT,
    IN p_resume_id INT,
    IN p_cover_letter TEXT,
    OUT p_application_id INT
)
BEGIN
    DECLARE v_cand_exists INT DEFAULT 0;
    DECLARE v_cand_user_id INT DEFAULT NULL;
    DECLARE v_job_status VARCHAR(50) DEFAULT NULL;
    DECLARE v_deadline DATE DEFAULT NULL;
    DECLARE v_dup_count INT DEFAULT 0;
    DECLARE v_resume_valid INT DEFAULT 0;
    DECLARE v_match_score DECIMAL(5, 2) DEFAULT 0.00;

    -- Rollback handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET @app_status_changed_by_user_id = NULL;
        SET @app_status_change_notes = NULL;
        ROLLBACK;
        RESIGNAL;
    END;

    -- 1. Validate Candidate Existence
    SELECT user_id INTO v_cand_user_id 
    FROM candidate_profiles 
    WHERE candidate_id = p_candidate_id;

    IF v_cand_user_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Candidate profile does not exist.';
    END IF;

    -- 2. Validate Job Existence and Status
    SELECT status, deadline_date INTO v_job_status, v_deadline
    FROM jobs
    WHERE job_id = p_job_id;

    IF v_job_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Job requisition does not exist.';
    END IF;

    IF v_job_status <> 'ACTIVE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Business Logic Error: Job is not accepting applications (status is not ACTIVE).';
    END IF;

    IF v_deadline IS NOT NULL AND v_deadline < CURRENT_DATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Business Logic Error: Application deadline for this job has expired.';
    END IF;

    -- 3. Prevent Duplicate Applications
    SELECT COUNT(*) INTO v_dup_count
    FROM applications
    WHERE job_id = p_job_id AND candidate_id = p_candidate_id;

    IF v_dup_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Integrity Error: Candidate has already applied for this job opening.';
    END IF;

    -- 4. Validate Resume Ownership (matches composite constraint in schema)
    SELECT COUNT(*) INTO v_resume_valid
    FROM resumes
    WHERE resume_id = p_resume_id AND candidate_id = p_candidate_id;

    IF v_resume_valid = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Integrity Error: Resume does not belong to the candidate or does not exist.';
    END IF;

    -- 5. Calculate ATS Match Score using stored function
    SET v_match_score = fn_calculate_match_score(p_job_id, p_candidate_id);

    -- 6. Insert Application within Transaction
    START TRANSACTION;
        -- Set session context for automatic audit trigger
        SET @app_status_changed_by_user_id = v_cand_user_id;
        SET @app_status_change_notes = 'Candidate submitted job application via portal';

        INSERT INTO applications (
            job_id, candidate_id, resume_id, cover_letter, current_status, match_score
        ) VALUES (
            p_job_id, p_candidate_id, p_resume_id, p_cover_letter, 'APPLIED', v_match_score
        );
        SET p_application_id = LAST_INSERT_ID();

        -- Reset session context
        SET @app_status_changed_by_user_id = NULL;
        SET @app_status_change_notes = NULL;
    COMMIT;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 4. sp_update_application_status
-- Description: Updates an application's `current_status` and records the actor
--              and explanation for the status history audit trail.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_application_status;

DELIMITER $$

CREATE PROCEDURE sp_update_application_status(
    IN p_application_id INT,
    IN p_new_status VARCHAR(50),
    IN p_changed_by_user_id INT,
    IN p_change_notes VARCHAR(500)
)
BEGIN
    DECLARE v_old_status VARCHAR(50) DEFAULT NULL;
    DECLARE v_user_count INT DEFAULT 0;

    -- Rollback handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET @app_status_changed_by_user_id = NULL;
        SET @app_status_change_notes = NULL;
        ROLLBACK;
        RESIGNAL;
    END;

    -- 1. Validate Application Existence
    SELECT current_status INTO v_old_status
    FROM applications
    WHERE application_id = p_application_id;

    IF v_old_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Application does not exist.';
    END IF;

    -- 2. Validate Target Status against ENUM values
    IF p_new_status NOT IN (
        'APPLIED', 'UNDER_REVIEW', 'SHORTLISTED', 'INTERVIEW_SCHEDULED',
        'INTERVIEWED', 'OFFERED', 'REJECTED', 'WITHDRAWN'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Invalid application status value provided.';
    END IF;

    -- 3. Avoid redundant update if status is unchanged
    IF v_old_status = p_new_status THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Notice: Application is already in the requested status.';
    END IF;

    -- 4. Validate actor user existence if specified
    IF p_changed_by_user_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_user_count FROM users WHERE user_id = p_changed_by_user_id;
        IF v_user_count = 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Specified changed_by_user_id does not exist.';
        END IF;
    END IF;

    -- 5. Execute Update within Transaction
    START TRANSACTION;
        -- Pass actor metadata to the AFTER UPDATE trigger via session variables
        SET @app_status_changed_by_user_id = p_changed_by_user_id;
        SET @app_status_change_notes = p_change_notes;

        UPDATE applications
        SET 
            current_status = p_new_status,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = p_application_id;

        -- Clean up session variables
        SET @app_status_changed_by_user_id = NULL;
        SET @app_status_change_notes = NULL;
    COMMIT;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 5. sp_schedule_interview
-- Description: Creates an interview round, checks for interviewer calendar clashes,
--              and advances application status to INTERVIEW_SCHEDULED.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_schedule_interview;

DELIMITER $$

CREATE PROCEDURE sp_schedule_interview(
    IN p_application_id INT,
    IN p_interviewer_name VARCHAR(150),
    IN p_round_number INT,
    IN p_round_type VARCHAR(50),
    IN p_scheduled_at DATETIME,
    IN p_duration_minutes INT,
    IN p_meeting_link VARCHAR(500),
    IN p_location VARCHAR(150),
    OUT p_interview_id INT
)
BEGIN
    DECLARE v_app_status VARCHAR(50) DEFAULT NULL;
    DECLARE v_clash_count INT DEFAULT 0;

    -- Rollback handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET @app_status_changed_by_user_id = NULL;
        SET @app_status_change_notes = NULL;
        ROLLBACK;
        RESIGNAL;
    END;

    -- 1. Validate Application Existence & Lifecycle Status
    SELECT current_status INTO v_app_status
    FROM applications
    WHERE application_id = p_application_id;

    IF v_app_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Application does not exist.';
    END IF;

    IF v_app_status IN ('REJECTED', 'WITHDRAWN') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Business Logic Error: Cannot schedule interview for rejected or withdrawn application.';
    END IF;

    -- 2. Parameter Validation
    IF p_interviewer_name IS NULL OR TRIM(p_interviewer_name) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Interviewer name is required.';
    END IF;

    IF p_scheduled_at IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Scheduled date and time is required.';
    END IF;

    IF p_duration_minutes IS NULL OR p_duration_minutes <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Duration minutes must be greater than zero.';
    END IF;

    IF p_round_number IS NULL OR p_round_number < 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Round number must be at least 1.';
    END IF;

    IF p_round_type NOT IN ('SCREENING', 'TECHNICAL', 'HR', 'MANAGERIAL', 'FINAL') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Invalid round_type specified.';
    END IF;

    -- 3. Check for Interviewer Scheduling Conflict (overlapping active interview time slots)
    SELECT COUNT(*) INTO v_clash_count
    FROM interviews
    WHERE interviewer_name = p_interviewer_name
      AND status IN ('SCHEDULED', 'RESCHEDULED')
      AND (scheduled_at < p_scheduled_at + INTERVAL p_duration_minutes MINUTE)
      AND (p_scheduled_at < scheduled_at + INTERVAL duration_minutes MINUTE);

    IF v_clash_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Scheduling Conflict: Interviewer already has an active interview in this time slot.';
    END IF;

    -- 4. Transactional Execution
    START TRANSACTION;
        INSERT INTO interviews (
            application_id, interviewer_name, round_number, round_type,
            scheduled_at, duration_minutes, meeting_link, location, status
        ) VALUES (
            p_application_id, p_interviewer_name, p_round_number, p_round_type,
            p_scheduled_at, p_duration_minutes, p_meeting_link, p_location, 'SCHEDULED'
        );
        SET p_interview_id = LAST_INSERT_ID();

        -- Advance application status to INTERVIEW_SCHEDULED if currently in early stages
        IF v_app_status IN ('APPLIED', 'UNDER_REVIEW', 'SHORTLISTED') THEN
            SET @app_status_changed_by_user_id = NULL;
            SET @app_status_change_notes = CONCAT('Interview round ', p_round_number, ' scheduled with ', p_interviewer_name);

            UPDATE applications
            SET current_status = 'INTERVIEW_SCHEDULED', updated_at = CURRENT_TIMESTAMP
            WHERE application_id = p_application_id;

            SET @app_status_changed_by_user_id = NULL;
            SET @app_status_change_notes = NULL;
        END IF;
    COMMIT;
END$$

DELIMITER ;
