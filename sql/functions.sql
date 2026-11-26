-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: functions.sql (Phase 2: Stored Functions)
-- Description: Business logic, ATS match scoring, and metric calculations.
-- Prerequisites: schema.sql must be executed first.
-- =============================================================================

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- 1. fn_calculate_match_score
-- Description: Computes an ATS candidate-to-job match percentage (0.00 to 100.00)
--              based on job skill requirements vs candidate skill competencies.
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_calculate_match_score;

DELIMITER $$

CREATE FUNCTION fn_calculate_match_score(
    p_job_id INT,
    p_candidate_id INT
)
RETURNS DECIMAL(5, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_job_exists INT DEFAULT 0;
    DECLARE v_candidate_exists INT DEFAULT 0;
    DECLARE v_total_skills INT DEFAULT 0;
    DECLARE v_total_possible_weight DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_total_earned_score DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_final_score DECIMAL(5, 2) DEFAULT 0.00;

    -- Validate job existence
    SELECT COUNT(*) INTO v_job_exists FROM jobs WHERE job_id = p_job_id;
    IF v_job_exists = 0 THEN
        RETURN 0.00;
    END IF;

    -- Validate candidate existence
    SELECT COUNT(*) INTO v_candidate_exists FROM candidate_profiles WHERE candidate_id = p_candidate_id;
    IF v_candidate_exists = 0 THEN
        RETURN 0.00;
    END IF;

    -- Compute total skill count and cumulative maximum possible weight for this job
    -- Mandatory skills (is_required = TRUE) carry weight = 2.00
    -- Optional/preferred skills (is_required = FALSE) carry weight = 1.00
    SELECT 
        COUNT(*),
        COALESCE(SUM(CASE WHEN is_required = TRUE THEN 2.00 ELSE 1.00 END), 0.00)
    INTO 
        v_total_skills,
        v_total_possible_weight
    FROM job_skills
    WHERE job_id = p_job_id;

    -- If the job posting has no skill requirements specified, match is 100.00 by default
    IF v_total_skills = 0 OR v_total_possible_weight = 0.00 THEN
        RETURN 100.00;
    END IF;

    -- Calculate total earned score across matched skills
    -- For each matched skill:
    --   Skill Weight = 2.00 (required) or 1.00 (optional)
    --   Multiplied by composite fulfillment factor (0.00 to 1.00):
    --     1. Base Skill Match: 0.60 (60% for having the skill)
    --     2. Experience Factor: up to 0.20 (20% based on candidate vs required years)
    --     3. Proficiency Bonus: up to 0.20 (EXPERT: 0.20, ADVANCED: 0.15, INTERMEDIATE: 0.10, BEGINNER: 0.05)
    SELECT COALESCE(SUM(
        (CASE WHEN js.is_required = TRUE THEN 2.00 ELSE 1.00 END) * (
            0.60 +
            (CASE 
                WHEN js.min_years_experience = 0.0 THEN 0.20
                WHEN cs.years_of_experience >= js.min_years_experience THEN 0.20
                ELSE (cs.years_of_experience / js.min_years_experience) * 0.20
             END) +
            (CASE cs.proficiency_level
                WHEN 'EXPERT' THEN 0.20
                WHEN 'ADVANCED' THEN 0.15
                WHEN 'INTERMEDIATE' THEN 0.10
                WHEN 'BEGINNER' THEN 0.05
                ELSE 0.00
             END)
        )
    ), 0.00)
    INTO v_total_earned_score
    FROM job_skills js
    INNER JOIN candidate_skills cs 
        ON js.skill_id = cs.skill_id 
        AND cs.candidate_id = p_candidate_id
    WHERE js.job_id = p_job_id;

    -- Compute percentage score
    SET v_final_score = ROUND((v_total_earned_score / v_total_possible_weight) * 100.00, 2);

    -- Clamp strictly between 0.00 and 100.00
    IF v_final_score > 100.00 THEN
        SET v_final_score = 100.00;
    ELSEIF v_final_score < 0.00 THEN
        SET v_final_score = 0.00;
    END IF;

    RETURN v_final_score;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 2. fn_get_candidate_application_count
-- Description: Returns total number of applications submitted by a candidate.
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_get_candidate_application_count;

DELIMITER $$

CREATE FUNCTION fn_get_candidate_application_count(
    p_candidate_id INT
)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT DEFAULT 0;

    SELECT COUNT(*)
    INTO v_count
    FROM applications
    WHERE candidate_id = p_candidate_id;

    RETURN v_count;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 3. fn_get_job_applicant_count
-- Description: Returns total number of applications received for a specific job.
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_get_job_applicant_count;

DELIMITER $$

CREATE FUNCTION fn_get_job_applicant_count(
    p_job_id INT
)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT DEFAULT 0;

    SELECT COUNT(*)
    INTO v_count
    FROM applications
    WHERE job_id = p_job_id;

    RETURN v_count;
END$$

DELIMITER ;
