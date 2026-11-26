-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: schema.sql (Phase 1: DDL Schema Definition)
-- Description: Core database schema, constraints, relationships, and indexes.
-- Safety: Completely safe to execute without deleting or dropping existing data.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS job_portal_ats
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- 1. ROLES TABLE (RBAC Base Entity)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE COMMENT 'ADMIN, RECRUITER, CANDIDATE',
    description VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='Defines system user roles for RBAC authorization';

-- -----------------------------------------------------------------------------
-- 2. USERS TABLE (Authentication & Base User Entity)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL COMMENT 'Bcrypt or Werkzeug secure hash',
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role_id (role_id),
    INDEX idx_users_email (email),
    CONSTRAINT fk_users_roles
        FOREIGN KEY (role_id) REFERENCES roles (role_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Unified credentials and identity for all users';

-- -----------------------------------------------------------------------------
-- 3. CANDIDATE PROFILES TABLE (Specialization for Candidates - 1:1 with Users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_profiles (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    headline VARCHAR(255) NULL COMMENT 'Professional headline, e.g., Senior Full-Stack Engineer',
    summary TEXT NULL,
    current_location VARCHAR(150) NULL,
    years_of_experience DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    highest_education VARCHAR(100) NULL,
    linkedin_url VARCHAR(255) NULL,
    portfolio_url VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_candidate_exp (years_of_experience),
    CONSTRAINT fk_candidate_users
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_candidate_exp
        CHECK (years_of_experience >= 0.0)
) ENGINE=InnoDB COMMENT='Extended profile for candidates';

-- -----------------------------------------------------------------------------
-- 4. RECRUITER PROFILES TABLE (Specialization for Recruiters - 1:1 with Users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recruiter_profiles (
    recruiter_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    company_name VARCHAR(150) NOT NULL,
    company_website VARCHAR(255) NULL,
    department VARCHAR(100) NULL,
    designation VARCHAR(100) NULL COMMENT 'e.g. Senior Talent Acquisition Specialist',
    office_location VARCHAR(150) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_recruiter_company (company_name),
    CONSTRAINT fk_recruiter_users
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Extended profile and company metadata for recruiters';

-- -----------------------------------------------------------------------------
-- 5. SKILLS MASTER TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL COMMENT 'e.g. Programming, Database, Cloud, Framework, Soft Skill',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_skills_name (skill_name),
    INDEX idx_skills_category (category)
) ENGINE=InnoDB COMMENT='Standardized master skill catalog';

-- -----------------------------------------------------------------------------
-- 6. CANDIDATE SKILLS TABLE (Bridge Table: Candidate Profiles M:N Skills)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_skills (
    candidate_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level ENUM('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT') NOT NULL DEFAULT 'INTERMEDIATE',
    years_of_experience DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    PRIMARY KEY (candidate_id, skill_id),
    INDEX idx_cskills_skill (skill_id),
    CONSTRAINT fk_cskills_candidate
        FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (candidate_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_cskills_skill
        FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_cskills_exp
        CHECK (years_of_experience >= 0.0)
) ENGINE=InnoDB COMMENT='Skills possessed by candidate with proficiency levels';

-- -----------------------------------------------------------------------------
-- 7. JOBS TABLE (Posted by Recruiters)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    employment_type ENUM('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP') NOT NULL DEFAULT 'FULL_TIME',
    workplace_type ENUM('ON_SITE', 'REMOTE', 'HYBRID') NOT NULL DEFAULT 'ON_SITE',
    location VARCHAR(150) NOT NULL,
    min_experience_years DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    salary_min DECIMAL(12, 2) NULL,
    salary_max DECIMAL(12, 2) NULL,
    status ENUM('DRAFT', 'ACTIVE', 'PAUSED', 'CLOSED') NOT NULL DEFAULT 'ACTIVE',
    deadline_date DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_status_deadline (status, deadline_date),
    INDEX idx_jobs_recruiter (recruiter_id),
    INDEX idx_jobs_location (location),
    CONSTRAINT fk_jobs_recruiter
        FOREIGN KEY (recruiter_id) REFERENCES recruiter_profiles (recruiter_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_jobs_salary
        CHECK (
            (salary_min IS NULL OR salary_min >= 0.00) AND
            (salary_max IS NULL OR salary_max >= 0.00) AND
            (salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min)
        ),
    CONSTRAINT chk_jobs_exp
        CHECK (min_experience_years >= 0.0)
) ENGINE=InnoDB COMMENT='Job openings published by recruiters';

-- -----------------------------------------------------------------------------
-- 8. JOB SKILLS TABLE (Bridge Table: Jobs M:N Skills)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_skills (
    job_id INT NOT NULL,
    skill_id INT NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    min_years_experience DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    PRIMARY KEY (job_id, skill_id),
    INDEX idx_jskills_skill (skill_id),
    CONSTRAINT fk_jskills_job
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_jskills_skill
        FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_jskills_exp
        CHECK (min_years_experience >= 0.0)
) ENGINE=InnoDB COMMENT='Required and optional skills mapped to job postings';

-- -----------------------------------------------------------------------------
-- 9. RESUMES TABLE (Candidate Resume Documents)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resumes (
    resume_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_kb INT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_resumes_candidate (candidate_id),
    -- Composite unique key to enforce strict resume ownership at the schema level
    CONSTRAINT uq_resumes_id_candidate
        UNIQUE (resume_id, candidate_id),
    CONSTRAINT fk_resumes_candidate
        FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (candidate_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_resume_size
        CHECK (file_size_kb IS NULL OR file_size_kb > 0)
) ENGINE=InnoDB COMMENT='Resume files uploaded by candidates';

-- -----------------------------------------------------------------------------
-- 10. APPLICATIONS TABLE (Candidate Applications for Jobs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    candidate_id INT NOT NULL,
    resume_id INT NOT NULL,
    cover_letter TEXT NULL,
    current_status ENUM('APPLIED', 'UNDER_REVIEW', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED', 'REJECTED', 'WITHDRAWN') NOT NULL DEFAULT 'APPLIED',
    match_score DECIMAL(5, 2) NULL COMMENT 'Calculated ATS matching percentage (0.00 - 100.00)',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_applications_job_status (job_id, current_status),
    INDEX idx_applications_candidate (candidate_id),
    INDEX idx_applications_match_score (match_score DESC),
    INDEX idx_applications_resume (resume_id),
    CONSTRAINT uq_job_candidate
        UNIQUE (job_id, candidate_id),
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_applications_candidate
        FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (candidate_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    -- Composite foreign key guarantees that candidates can ONLY apply using their OWN resumes
    CONSTRAINT fk_applications_resume_owner
        FOREIGN KEY (resume_id, candidate_id) REFERENCES resumes (resume_id, candidate_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_app_match_score
        CHECK (match_score IS NULL OR (match_score >= 0.00 AND match_score <= 100.00))
) ENGINE=InnoDB COMMENT='Job applications submitted by candidates';

-- -----------------------------------------------------------------------------
-- 11. INTERVIEWS TABLE (Interview Rounds for Shortlisted Applications)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interviews (
    interview_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    interviewer_name VARCHAR(150) NOT NULL,
    round_number INT NOT NULL DEFAULT 1,
    round_type ENUM('SCREENING', 'TECHNICAL', 'HR', 'MANAGERIAL', 'FINAL') NOT NULL DEFAULT 'TECHNICAL',
    scheduled_at DATETIME NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 60,
    meeting_link VARCHAR(500) NULL,
    location VARCHAR(150) NULL COMMENT 'Physical location or Online platform',
    status ENUM('SCHEDULED', 'COMPLETED', 'CANCELLED', 'RESCHEDULED', 'NO_SHOW') NOT NULL DEFAULT 'SCHEDULED',
    feedback TEXT NULL,
    rating INT NULL COMMENT 'Interview score 1 to 5',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_interviews_scheduled_at (scheduled_at, status),
    INDEX idx_interviews_app_id (application_id),
    CONSTRAINT fk_interviews_application
        FOREIGN KEY (application_id) REFERENCES applications (application_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_interview_round
        CHECK (round_number >= 1),
    CONSTRAINT chk_interview_duration
        CHECK (duration_minutes > 0),
    CONSTRAINT chk_interview_rating
        CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5))
) ENGINE=InnoDB COMMENT='Scheduled and completed interview rounds';

-- -----------------------------------------------------------------------------
-- 12. APPLICATION STATUS HISTORY TABLE (State Transition Audit Trail)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS application_status_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    old_status ENUM('APPLIED', 'UNDER_REVIEW', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED', 'REJECTED', 'WITHDRAWN') NULL,
    new_status ENUM('APPLIED', 'UNDER_REVIEW', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED', 'REJECTED', 'WITHDRAWN') NOT NULL,
    changed_by_user_id INT NULL,
    change_notes VARCHAR(500) NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_history_app_id_time (application_id, changed_at),
    INDEX idx_history_user (changed_by_user_id),
    CONSTRAINT fk_history_application
        FOREIGN KEY (application_id) REFERENCES applications (application_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_history_user
        FOREIGN KEY (changed_by_user_id) REFERENCES users (user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Audit trail capturing every lifecycle state change for applications';
