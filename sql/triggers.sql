-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: triggers.sql (Phase 2: Database Triggers)
-- Description: Automated status history audit logging and interview scheduling
--              integrity validations.
-- Prerequisites: schema.sql must be executed first.
-- =============================================================================

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- 1. trg_applications_after_insert
-- Description: Automatically records the initial state transition in
--              `application_status_history` when a new application is submitted.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_applications_after_insert;

DELIMITER $$

CREATE TRIGGER trg_applications_after_insert
AFTER INSERT ON applications
FOR EACH ROW
BEGIN
    INSERT INTO application_status_history (
        application_id,
        old_status,
        new_status,
        changed_by_user_id,
        change_notes,
        changed_at
    ) VALUES (
        NEW.application_id,
        NULL,
        NEW.current_status,
        @app_status_changed_by_user_id,
        COALESCE(@app_status_change_notes, 'Initial application submitted'),
        CURRENT_TIMESTAMP
    );
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 2. trg_applications_after_update
-- Description: Automatically logs state changes to `application_status_history`
--              only when `current_status` actually changes.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_applications_after_update;

DELIMITER $$

CREATE TRIGGER trg_applications_after_update
AFTER UPDATE ON applications
FOR EACH ROW
BEGIN
    -- Only capture audit record when current_status actually transitions
    IF OLD.current_status <> NEW.current_status THEN
        INSERT INTO application_status_history (
            application_id,
            old_status,
            new_status,
            changed_by_user_id,
            change_notes,
            changed_at
        ) VALUES (
            NEW.application_id,
            OLD.current_status,
            NEW.current_status,
            @app_status_changed_by_user_id,
            COALESCE(
                @app_status_change_notes,
                CONCAT('Application status transitioned from ', OLD.current_status, ' to ', NEW.current_status)
            ),
            CURRENT_TIMESTAMP
        );
    END IF;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 3. trg_interviews_before_insert
-- Description: Validates interview scheduling before insertion using existing
--              fields: application_id, interviewer_name, scheduled_at, duration_minutes, and status.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_interviews_before_insert;

DELIMITER $$

CREATE TRIGGER trg_interviews_before_insert
BEFORE INSERT ON interviews
FOR EACH ROW
BEGIN
    DECLARE v_app_status VARCHAR(50) DEFAULT NULL;
    DECLARE v_overlap_count INT DEFAULT 0;

    -- 1. Validate application status: Prevent scheduling for terminal states
    SELECT current_status INTO v_app_status
    FROM applications
    WHERE application_id = NEW.application_id;

    IF v_app_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Interview Validation Error: Application does not exist.';
    END IF;

    IF v_app_status IN ('REJECTED', 'WITHDRAWN') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Interview Validation Error: Cannot schedule an interview for a rejected or withdrawn application.';
    END IF;

    -- 2. Validate duration
    IF NEW.duration_minutes IS NULL OR NEW.duration_minutes <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Interview Validation Error: duration_minutes must be greater than zero.';
    END IF;

    -- 3. Prevent overlapping interviews for the same interviewer
    IF NEW.status IN ('SCHEDULED', 'RESCHEDULED') THEN
        SELECT COUNT(*) INTO v_overlap_count
        FROM interviews
        WHERE interviewer_name = NEW.interviewer_name
          AND status IN ('SCHEDULED', 'RESCHEDULED')
          AND (scheduled_at < NEW.scheduled_at + INTERVAL NEW.duration_minutes MINUTE)
          AND (NEW.scheduled_at < scheduled_at + INTERVAL duration_minutes MINUTE);

        IF v_overlap_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Interview Validation Error: Another active interview is already scheduled for this interviewer during the requested time window.';
        END IF;
    END IF;
END$$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- 4. trg_interviews_before_update
-- Description: Validates interview modifications before update to prevent
--              scheduling clashes and invalid state configurations.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_interviews_before_update;

DELIMITER $$

CREATE TRIGGER trg_interviews_before_update
BEFORE UPDATE ON interviews
FOR EACH ROW
BEGIN
    DECLARE v_overlap_count INT DEFAULT 0;

    -- 1. Validate duration
    IF NEW.duration_minutes IS NULL OR NEW.duration_minutes <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Interview Validation Error: duration_minutes must be greater than zero.';
    END IF;

    -- 2. If interview is rescheduled/scheduled, check for time overlaps excluding this interview
    IF NEW.status IN ('SCHEDULED', 'RESCHEDULED') THEN
        SELECT COUNT(*) INTO v_overlap_count
        FROM interviews
        WHERE interviewer_name = NEW.interviewer_name
          AND interview_id <> OLD.interview_id
          AND status IN ('SCHEDULED', 'RESCHEDULED')
          AND (scheduled_at < NEW.scheduled_at + INTERVAL NEW.duration_minutes MINUTE)
          AND (NEW.scheduled_at < scheduled_at + INTERVAL duration_minutes MINUTE);

        IF v_overlap_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Interview Validation Error: Rescheduled time window conflicts with another active interview for this interviewer.';
        END IF;
    END IF;
END$$

DELIMITER ;
