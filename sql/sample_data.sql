-- =============================================================================
-- Job Portal and Application Tracking System (ATS)
-- Database Engine: MySQL 8.0+
-- File: sample_data.sql (Phase 2: Comprehensive Seed Data)
-- Description: Realistic test dataset across all 12 tables demonstrating
--              multiple roles, candidates, recruiters, jobs, skills, resumes,
--              applications across lifecycle statuses, interviews, and audit logs.
-- Safety: Completely non-destructive (no DROP or TRUNCATE statements).
-- Prerequisites: schema.sql, functions.sql, procedures.sql, and triggers.sql.
-- =============================================================================

USE job_portal_ats;

-- -----------------------------------------------------------------------------
-- 1. ROLES TABLE (3 Standard Roles)
-- -----------------------------------------------------------------------------
INSERT INTO roles (role_id, role_name, description) VALUES
(1, 'ADMIN', 'System Administrator with overall platform governance, user management, and report auditing privileges.'),
(2, 'RECRUITER', 'Talent acquisition specialist or hiring manager who publishes jobs, reviews applicant pipelines, and schedules interviews.'),
(3, 'CANDIDATE', 'Job seeker who maintains a professional profile, uploads resumes, tracks applications, and attends interviews.')
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- -----------------------------------------------------------------------------
-- 2. USERS TABLE (14 Realistic Users: 2 Admins, 4 Recruiters, 8 Candidates)
-- Password hash corresponds to Bcrypt hash for standard seed password 'Password@123'
-- -----------------------------------------------------------------------------
INSERT INTO users (user_id, role_id, email, password_hash, first_name, last_name, phone, is_active) VALUES
-- System Administrators
(1, 1, 'admin.sarah@atsportal.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Sarah', 'Jenkins', '+1-415-555-0101', TRUE),
(2, 1, 'admin.david@atsportal.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'David', 'Miller', '+1-206-555-0102', TRUE),

-- Recruiters
(3, 2, 'elena.rostova@google.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Elena', 'Rostova', '+1-650-555-0201', TRUE),
(4, 2, 'marcus.vance@amazon.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Marcus', 'Vance', '+1-206-555-0202', TRUE),
(5, 2, 'priya.sharma@microsoft.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Priya', 'Sharma', '+1-425-555-0203', TRUE),
(6, 2, 'alex.chen@stripe.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Alex', 'Chen', '+1-415-555-0204', TRUE),

-- Candidates
(7, 3, 'aarav.patel@gmail.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Aarav', 'Patel', '+1-415-555-0301', TRUE),
(8, 3, 'emily.watson@gmail.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Emily', 'Watson', '+1-206-555-0302', TRUE),
(9, 3, 'carlos.mendez@outlook.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Carlos', 'Mendez', '+1-512-555-0303', TRUE),
(10, 3, 'aisha.khan@yahoo.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Aisha', 'Khan', '+1-212-555-0304', TRUE),
(11, 3, 'liam.oconnor@gmail.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Liam', 'O''Connor', '+1-312-555-0305', TRUE),
(12, 3, 'sophia.rodriguez@gmail.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Sophia', 'Rodriguez', '+1-617-555-0306', TRUE),
(13, 3, 'vikram.singh@outlook.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Vikram', 'Singh', '+1-408-555-0307', TRUE),
(14, 3, 'chloe.dubois@gmail.com', '$2b$12$e8w6Q0nO82u3pM98qAkeIe3nKq7gB5O6U3.pL7vM8yK2d1F5e0S8y', 'Chloe', 'Dubois', '+1-303-555-0308', TRUE)
ON DUPLICATE KEY UPDATE first_name = VALUES(first_name), last_name = VALUES(last_name);

-- -----------------------------------------------------------------------------
-- 3. RECRUITER PROFILES TABLE (4 Corporate Recruiter Profiles)
-- -----------------------------------------------------------------------------
INSERT INTO recruiter_profiles (recruiter_id, user_id, company_name, company_website, department, designation, office_location) VALUES
(1, 3, 'Google LLC', 'https://about.google', 'Google Cloud Platform', 'Staff Technical Recruiter', 'Sunnyvale, CA'),
(2, 4, 'Amazon Web Services', 'https://aws.amazon.com', 'Cloud Infrastructure & Networking', 'Senior Talent Partner', 'Seattle, WA'),
(3, 5, 'Microsoft Corporation', 'https://microsoft.com', 'Azure Enterprise Engineering', 'Lead Technical Talent Specialist', 'Redmond, WA'),
(4, 6, 'Stripe Inc.', 'https://stripe.com', 'Core Payments & Infrastructure', 'Principal Talent Acquisition Lead', 'San Francisco, CA')
ON DUPLICATE KEY UPDATE company_name = VALUES(company_name);

-- -----------------------------------------------------------------------------
-- 4. CANDIDATE PROFILES TABLE (8 Diverse Candidate Profiles)
-- -----------------------------------------------------------------------------
INSERT INTO candidate_profiles (candidate_id, user_id, headline, summary, current_location, years_of_experience, highest_education, linkedin_url, portfolio_url) VALUES
(1, 7, 'Senior Python & Cloud Architect', 'Experienced backend specialist with 6+ years architecting microservices on GCP and AWS.', 'San Francisco, CA', 6.5, 'B.S. in Computer Science', 'https://linkedin.com/in/aarav-patel', 'https://github.com/aaravpatel'),
(2, 8, 'Full-Stack Software Engineer (React & Python)', 'Versatile developer experienced with modern React frontends, Flask/Django APIs, and distributed caching.', 'Seattle, WA', 4.0, 'M.S. in Software Engineering', 'https://linkedin.com/in/emily-watson', 'https://emilywatson.dev'),
(3, 9, 'DevOps & Site Reliability Engineer', 'Cloud native enthusiast focused on Kubernetes orchestration, Terraform IaC, and zero-downtime CI/CD pipelines.', 'Austin, TX', 5.0, 'B.Tech in Information Technology', 'https://linkedin.com/in/carlos-mendez', 'https://github.com/carlosmendez'),
(4, 10, 'Junior Software Engineer | Fast Learner', 'Recent graduate passionate about backend development, database optimization, and scalable web services.', 'New York, NY', 1.5, 'B.S. in Computer Engineering', 'https://linkedin.com/in/aisha-khan', 'https://aishakhan.me'),
(5, 11, 'Senior Database Administrator & MySQL Specialist', 'High-throughput database tuning, replication clustering, index optimization, and transaction safety expert.', 'Chicago, IL', 7.0, 'B.S. in Information Systems', 'https://linkedin.com/in/liam-oconnor', 'https://github.com/liamoconnor'),
(6, 12, 'Python Data & Machine Learning Engineer', 'Specializes in ETL data pipelines, predictive modeling, and RESTful machine learning inference services.', 'Boston, MA', 3.5, 'M.S. in Data Science', 'https://linkedin.com/in/sophia-rodriguez', 'https://sophiarodriguez.ai'),
(7, 13, 'Senior Infrastructure & Security Engineer', 'Deep expertise in multi-cloud architecture (AWS/GCP), IAM role hardening, and Linux systems internals.', 'San Jose, CA', 5.5, 'B.E. in Computer Science', 'https://linkedin.com/in/vikram-singh', 'https://github.com/vikramsingh'),
(8, 14, 'Frontend UI/UX & Web Developer', 'Crafting accessible, high-performance web user experiences with React, TypeScript, and modern CSS.', 'Denver, CO', 3.0, 'B.A. in Digital Interactive Media', 'https://linkedin.com/in/chloe-dubois', 'https://chloedubois.design')
ON DUPLICATE KEY UPDATE headline = VALUES(headline);

-- -----------------------------------------------------------------------------
-- 5. SKILLS MASTER TABLE (20 Standardized Industry Skills)
-- -----------------------------------------------------------------------------
INSERT INTO skills (skill_id, skill_name, category) VALUES
(1, 'Python', 'Programming'),
(2, 'Java', 'Programming'),
(3, 'Go', 'Programming'),
(4, 'JavaScript', 'Programming'),
(5, 'TypeScript', 'Programming'),
(6, 'C++', 'Programming'),
(7, 'MySQL', 'Database'),
(8, 'PostgreSQL', 'Database'),
(9, 'MongoDB', 'Database'),
(10, 'Redis', 'Database'),
(11, 'Docker', 'Cloud & DevOps'),
(12, 'Kubernetes', 'Cloud & DevOps'),
(13, 'AWS', 'Cloud & DevOps'),
(14, 'Google Cloud Platform', 'Cloud & DevOps'),
(15, 'Terraform', 'Cloud & DevOps'),
(16, 'React', 'Web Framework'),
(17, 'Node.js', 'Web Framework'),
(18, 'Flask', 'Web Framework'),
(19, 'Django', 'Web Framework'),
(20, 'System Design', 'Core Architecture')
ON DUPLICATE KEY UPDATE category = VALUES(category);

-- -----------------------------------------------------------------------------
-- 6. CANDIDATE SKILLS TABLE (M:N Bridge: Candidate Proficiencies)
-- -----------------------------------------------------------------------------
INSERT INTO candidate_skills (candidate_id, skill_id, proficiency_level, years_of_experience) VALUES
-- Candidate 1 (Aarav Patel - Senior Python/Cloud)
(1, 1, 'EXPERT', 6.0),         -- Python
(1, 7, 'ADVANCED', 5.0),       -- MySQL
(1, 11, 'ADVANCED', 4.0),      -- Docker
(1, 14, 'ADVANCED', 4.0),      -- GCP
(1, 18, 'EXPERT', 5.0),        -- Flask
(1, 20, 'ADVANCED', 4.5),      -- System Design

-- Candidate 2 (Emily Watson - Full Stack)
(2, 4, 'EXPERT', 4.0),         -- JavaScript
(2, 5, 'ADVANCED', 3.0),       -- TypeScript
(2, 16, 'EXPERT', 4.0),        -- React
(2, 17, 'ADVANCED', 3.5),      -- Node.js
(2, 1, 'INTERMEDIATE', 2.5),   -- Python
(2, 18, 'INTERMEDIATE', 2.0),  -- Flask

-- Candidate 3 (Carlos Mendez - DevOps/K8s)
(3, 11, 'EXPERT', 5.0),        -- Docker
(3, 12, 'EXPERT', 4.5),        -- Kubernetes
(3, 13, 'ADVANCED', 4.5),      -- AWS
(3, 15, 'ADVANCED', 4.0),      -- Terraform
(3, 3, 'INTERMEDIATE', 2.5),   -- Go

-- Candidate 4 (Aisha Khan - Junior Dev)
(4, 1, 'INTERMEDIATE', 1.5),   -- Python
(4, 7, 'INTERMEDIATE', 1.5),   -- MySQL
(4, 16, 'BEGINNER', 1.0),      -- React
(4, 18, 'BEGINNER', 1.0),      -- Flask

-- Candidate 5 (Liam O'Connor - MySQL DBA)
(5, 7, 'EXPERT', 7.0),         -- MySQL
(5, 8, 'ADVANCED', 5.0),       -- PostgreSQL
(5, 10, 'ADVANCED', 4.0),      -- Redis
(5, 20, 'ADVANCED', 5.0),      -- System Design
(5, 1, 'INTERMEDIATE', 3.0),   -- Python

-- Candidate 6 (Sophia Rodriguez - ML/Python)
(6, 1, 'EXPERT', 3.5),         -- Python
(6, 8, 'INTERMEDIATE', 2.5),   -- PostgreSQL
(6, 11, 'INTERMEDIATE', 2.0),  -- Docker
(6, 18, 'INTERMEDIATE', 2.0),  -- Flask

-- Candidate 7 (Vikram Singh - Infrastructure/Security)
(7, 13, 'EXPERT', 5.5),        -- AWS
(7, 14, 'ADVANCED', 4.0),      -- GCP
(7, 11, 'ADVANCED', 4.5),      -- Docker
(7, 12, 'ADVANCED', 3.5),      -- Kubernetes
(7, 15, 'ADVANCED', 3.5),      -- Terraform

-- Candidate 8 (Chloe Dubois - Frontend)
(8, 4, 'ADVANCED', 3.0),       -- JavaScript
(8, 5, 'INTERMEDIATE', 2.0),   -- TypeScript
(8, 16, 'ADVANCED', 3.0),      -- React
(8, 17, 'BEGINNER', 1.5)       -- Node.js
ON DUPLICATE KEY UPDATE proficiency_level = VALUES(proficiency_level);

-- -----------------------------------------------------------------------------
-- 7. JOBS TABLE (6 Job Openings Posted by Recruiters)
-- -----------------------------------------------------------------------------
INSERT INTO jobs (job_id, recruiter_id, title, description, employment_type, workplace_type, location, min_experience_years, salary_min, salary_max, status, deadline_date) VALUES
(1, 1, 'Senior Cloud Python Backend Engineer', 
 'Architect scalable microservices on Google Cloud Platform, optimize database interactions, and lead architectural design sessions.',
 'FULL_TIME', 'HYBRID', 'Sunnyvale, CA', 5.0, 145000.00, 185000.00, 'ACTIVE', '2026-12-31'),

(2, 2, 'Senior DevOps & Kubernetes Architect', 
 'Build mission-critical CI/CD automation and containerized multi-region clusters using Kubernetes, Docker, and Terraform.',
 'FULL_TIME', 'ON_SITE', 'Seattle, WA', 4.0, 150000.00, 195000.00, 'ACTIVE', '2026-12-31'),

(3, 3, 'Full-Stack Software Engineer (React & Node)', 
 'Develop robust customer-facing web applications with modern React, TypeScript, Node.js microservices, and Azure integrations.',
 'FULL_TIME', 'HYBRID', 'Redmond, WA', 3.0, 120000.00, 160000.00, 'ACTIVE', '2026-11-30'),

(4, 4, 'High-Throughput MySQL Database Administrator', 
 'Own the core payments database topology, architect query indexing strategies, manage replication topologies, and ensure 99.999% SLA.',
 'FULL_TIME', 'REMOTE', 'San Francisco, CA', 5.0, 155000.00, 205000.00, 'ACTIVE', '2026-12-15'),

(5, 1, 'Associate Software Developer (Early Career)', 
 'Collaborate with senior mentors to build backend API endpoints in Python and Flask, write unit tests, and maintain database schemas.',
 'FULL_TIME', 'ON_SITE', 'Sunnyvale, CA', 1.0, 85000.00, 115000.00, 'ACTIVE', '2026-12-31'),

(6, 2, 'Legacy Cloud Infrastructure Specialist', 
 'Maintain and decommission legacy on-premise compute instances and migrate containerized services into AWS cloud clusters.',
 'CONTRACT', 'REMOTE', 'Seattle, WA', 4.0, 110000.00, 140000.00, 'CLOSED', '2026-06-30')
ON DUPLICATE KEY UPDATE title = VALUES(title);

-- -----------------------------------------------------------------------------
-- 8. JOB SKILLS TABLE (M:N Bridge: Job Skill Requisitions)
-- -----------------------------------------------------------------------------
INSERT INTO job_skills (job_id, skill_id, is_required, min_years_experience) VALUES
-- Job 1: Senior Cloud Python Engineer
(1, 1, TRUE, 5.0),   -- Python (Mandatory)
(1, 14, TRUE, 3.0),  -- GCP (Mandatory)
(1, 11, TRUE, 3.0),  -- Docker (Mandatory)
(1, 20, FALSE, 3.0), -- System Design (Preferred)
(1, 18, FALSE, 2.0), -- Flask (Preferred)

-- Job 2: Senior DevOps & Kubernetes Architect
(2, 12, TRUE, 4.0),  -- Kubernetes (Mandatory)
(2, 11, TRUE, 4.0),  -- Docker (Mandatory)
(2, 15, TRUE, 3.0),  -- Terraform (Mandatory)
(2, 13, TRUE, 3.0),  -- AWS (Mandatory)
(2, 3, FALSE, 2.0),  -- Go (Preferred)

-- Job 3: Full-Stack Software Engineer (React & Node)
(3, 16, TRUE, 3.0),  -- React (Mandatory)
(3, 4, TRUE, 3.0),   -- JavaScript (Mandatory)
(3, 17, TRUE, 2.5),  -- Node.js (Mandatory)
(3, 5, FALSE, 2.0),  -- TypeScript (Preferred)

-- Job 4: High-Throughput MySQL DBA
(4, 7, TRUE, 5.0),   -- MySQL (Mandatory)
(4, 10, TRUE, 3.0),  -- Redis (Mandatory)
(4, 20, TRUE, 4.0),  -- System Design (Mandatory)
(4, 8, FALSE, 3.0),  -- PostgreSQL (Preferred)

-- Job 5: Associate Software Developer
(5, 1, TRUE, 1.0),   -- Python (Mandatory)
(5, 7, TRUE, 1.0),   -- MySQL (Mandatory)
(5, 18, FALSE, 0.5), -- Flask (Preferred)

-- Job 6: Legacy Cloud Specialist (Closed)
(6, 13, TRUE, 4.0),  -- AWS (Mandatory)
(6, 11, TRUE, 3.0)   -- Docker (Mandatory)
ON DUPLICATE KEY UPDATE is_required = VALUES(is_required);

-- -----------------------------------------------------------------------------
-- 9. RESUMES TABLE (11 Candidate Resume Documents)
-- Candidate ownership strictly satisfied: resume_id maps to candidate_id
-- -----------------------------------------------------------------------------
INSERT INTO resumes (resume_id, candidate_id, file_name, file_path, file_size_kb, is_primary) VALUES
-- Candidate 1 (Aarav Patel)
(1, 1, 'aarav_patel_cloud_architect.pdf', '/uploads/resumes/c1_aarav_patel_cloud_architect.pdf', 245, TRUE),
(2, 1, 'aarav_patel_backend_general.pdf', '/uploads/resumes/c1_aarav_patel_backend_general.pdf', 210, FALSE),

-- Candidate 2 (Emily Watson)
(3, 2, 'emily_watson_fullstack_cv.pdf', '/uploads/resumes/c2_emily_watson_fullstack_cv.pdf', 188, TRUE),

-- Candidate 3 (Carlos Mendez)
(4, 3, 'carlos_mendez_devops_sre.pdf', '/uploads/resumes/c3_carlos_mendez_devops_sre.pdf', 312, TRUE),
(5, 3, 'carlos_mendez_cloud_specialist.pdf', '/uploads/resumes/c3_carlos_mendez_cloud_specialist.pdf', 290, FALSE),

-- Candidate 4 (Aisha Khan)
(6, 4, 'aisha_khan_software_engineer.pdf', '/uploads/resumes/c4_aisha_khan_software_engineer.pdf', 165, TRUE),

-- Candidate 5 (Liam O'Connor)
(7, 5, 'liam_oconnor_database_architect.pdf', '/uploads/resumes/c5_liam_oconnor_database_architect.pdf', 260, TRUE),

-- Candidate 6 (Sophia Rodriguez)
(8, 6, 'sophia_rodriguez_data_engineer.pdf', '/uploads/resumes/c6_sophia_rodriguez_data_engineer.pdf', 230, TRUE),

-- Candidate 7 (Vikram Singh)
(9, 7, 'vikram_singh_infrastructure_lead.pdf', '/uploads/resumes/c7_vikram_singh_infrastructure_lead.pdf', 275, TRUE),
(10, 7, 'vikram_singh_cloud_security.pdf', '/uploads/resumes/c7_vikram_singh_cloud_security.pdf', 255, FALSE),

-- Candidate 8 (Chloe Dubois)
(11, 8, 'chloe_dubois_frontend_resume.pdf', '/uploads/resumes/c8_chloe_dubois_frontend_resume.pdf', 195, TRUE)
ON DUPLICATE KEY UPDATE file_name = VALUES(file_name);

-- -----------------------------------------------------------------------------
-- 10. APPLICATIONS TABLE (12 Realistic Job Applications)
-- Calculated match score via fn_calculate_match_score
-- -----------------------------------------------------------------------------
-- Temporarily set session variable to denote seed insertion
SET @app_status_changed_by_user_id = 1;
SET @app_status_change_notes = 'Initial seed application submission';

INSERT INTO applications (application_id, job_id, candidate_id, resume_id, cover_letter, current_status, match_score) VALUES
-- App 1: Aarav Patel applies to Senior Cloud Python Engineer (Job 1) -> Match: High
(1, 1, 1, 1, 'Excited to apply for the Senior Cloud Python role at Google. My extensive experience with GCP microservices aligns directly with your platform requirements.', 'APPLIED', fn_calculate_match_score(1, 1)),

-- App 2: Aarav Patel applies to MySQL DBA (Job 4) -> Match: Moderate
(2, 4, 1, 2, 'Bringing strong database tuning and MySQL query design skills alongside distributed systems background.', 'APPLIED', fn_calculate_match_score(4, 1)),

-- App 3: Emily Watson applies to Full-Stack Engineer (Job 3) -> Match: High
(3, 3, 2, 3, 'Passionate about modern React architecture and Node.js backend integrations with Microsoft enterprise cloud.', 'APPLIED', fn_calculate_match_score(3, 2)),

-- App 4: Emily Watson applies to Associate Software Dev (Job 5) -> Match: Moderate
(4, 5, 2, 3, 'Looking to apply my versatile full stack skills to early career opportunities at Google.', 'APPLIED', fn_calculate_match_score(5, 2)),

-- App 5: Carlos Mendez applies to DevOps Architect (Job 2) -> Match: High
(5, 2, 3, 4, 'Kubernetes and Terraform specialist eager to contribute to AWS world-scale container operations.', 'APPLIED', fn_calculate_match_score(2, 3)),

-- App 6: Aisha Khan applies to Associate Software Dev (Job 5) -> Match: High
(6, 5, 4, 6, 'Enthusiastic junior developer with hands-on coursework in Python, Flask, and relational database schema design.', 'APPLIED', fn_calculate_match_score(5, 4)),

-- App 7: Liam O''Connor applies to MySQL DBA (Job 4) -> Match: Exceptional
(7, 4, 5, 7, 'Over 7 years specializing in high-throughput MySQL clustering, InnoDB query analysis, and transactional integrity.', 'APPLIED', fn_calculate_match_score(4, 5)),

-- App 8: Sophia Rodriguez applies to Senior Cloud Python Engineer (Job 1) -> Match: Moderate
(8, 1, 6, 8, 'Applying strong Python backend foundations and data analytics experience to cloud service engineering.', 'APPLIED', fn_calculate_match_score(1, 6)),

-- App 9: Vikram Singh applies to DevOps Architect (Job 2) -> Match: High
(9, 2, 7, 9, 'Multi-cloud infrastructure architect with deep AWS containerization and infrastructure-as-code automation skills.', 'APPLIED', fn_calculate_match_score(2, 7)),

-- App 10: Vikram Singh applies to Senior Cloud Python Engineer (Job 1) -> Match: Moderate
(10, 1, 7, 10, 'Combining cloud security hardening and container operations with GCP cloud platform development.', 'APPLIED', fn_calculate_match_score(1, 7)),

-- App 11: Chloe Dubois applies to Full-Stack Engineer (Job 3) -> Match: Moderate
(11, 3, 8, 11, 'Bringing rich interactive frontend React and TypeScript skills to the Microsoft Azure team.', 'APPLIED', fn_calculate_match_score(3, 8)),

-- App 12: Carlos Mendez applies to Legacy Cloud Specialist (Job 6) -> Match: High
(12, 6, 3, 5, 'Applying container migration experience to assist with legacy compute instance modernization.', 'APPLIED', fn_calculate_match_score(6, 3))
ON DUPLICATE KEY UPDATE cover_letter = VALUES(cover_letter);

-- Reset session variables
SET @app_status_changed_by_user_id = NULL;
SET @app_status_change_notes = NULL;

-- -----------------------------------------------------------------------------
-- UPDATE APPLICATIONS TO DIVERSE PIPELINE STATUSES
-- This triggers trg_applications_after_update, building realistic audit trails!
-- -----------------------------------------------------------------------------

-- Advance App 1 (Aarav @ Google) -> SHORTLISTED -> INTERVIEW_SCHEDULED -> INTERVIEWED -> OFFERED
SET @app_status_changed_by_user_id = 3; -- Recruiter Elena Rostova
SET @app_status_change_notes = 'Candidate profile passed initial screening; shortlisted';
UPDATE applications SET current_status = 'SHORTLISTED' WHERE application_id = 1;

SET @app_status_change_notes = 'Interviews scheduled with hiring team';
UPDATE applications SET current_status = 'INTERVIEW_SCHEDULED' WHERE application_id = 1;

SET @app_status_change_notes = 'Technical and leadership interview rounds completed';
UPDATE applications SET current_status = 'INTERVIEWED' WHERE application_id = 1;

SET @app_status_change_notes = 'Hiring committee approved formal employment offer';
UPDATE applications SET current_status = 'OFFERED' WHERE application_id = 1;

-- Advance App 2 (Aarav @ Stripe) -> UNDER_REVIEW
SET @app_status_changed_by_user_id = 6; -- Recruiter Alex Chen
SET @app_status_change_notes = 'Application currently under technical review by hiring manager';
UPDATE applications SET current_status = 'UNDER_REVIEW' WHERE application_id = 2;

-- Advance App 3 (Emily @ Microsoft) -> SHORTLISTED -> INTERVIEW_SCHEDULED -> INTERVIEWED
SET @app_status_changed_by_user_id = 5; -- Recruiter Priya Sharma
SET @app_status_change_notes = 'Impressive frontend React and Node portfolio; shortlisted';
UPDATE applications SET current_status = 'SHORTLISTED' WHERE application_id = 3;

SET @app_status_change_notes = 'Interview panel scheduled';
UPDATE applications SET current_status = 'INTERVIEW_SCHEDULED' WHERE application_id = 3;

SET @app_status_change_notes = 'Candidate completed live coding round';
UPDATE applications SET current_status = 'INTERVIEWED' WHERE application_id = 3;

-- Advance App 4 (Emily @ Google) -> SHORTLISTED
SET @app_status_changed_by_user_id = 3;
SET @app_status_change_notes = 'Shortlisted for early career pipeline';
UPDATE applications SET current_status = 'SHORTLISTED' WHERE application_id = 4;

-- Advance App 5 (Carlos @ AWS) -> SHORTLISTED -> INTERVIEW_SCHEDULED
SET @app_status_changed_by_user_id = 4; -- Recruiter Marcus Vance
SET @app_status_change_notes = 'Strong Kubernetes and Terraform background verified; shortlisted';
UPDATE applications SET current_status = 'SHORTLISTED' WHERE application_id = 5;

SET @app_status_change_notes = 'Technical round scheduled with SRE lead';
UPDATE applications SET current_status = 'INTERVIEW_SCHEDULED' WHERE application_id = 5;

-- App 6 (Aisha @ Google) remains in 'APPLIED' stage

-- Advance App 7 (Liam @ Stripe) -> SHORTLISTED -> INTERVIEW_SCHEDULED -> INTERVIEWED -> OFFERED
SET @app_status_changed_by_user_id = 6;
SET @app_status_change_notes = 'Top-tier DBA candidate match score (100%); shortlisted immediately';
UPDATE applications SET current_status = 'SHORTLISTED' WHERE application_id = 7;

SET @app_status_change_notes = 'System architecture interview scheduled';
UPDATE applications SET current_status = 'INTERVIEW_SCHEDULED' WHERE application_id = 7;

SET @app_status_change_notes = 'Candidate completed deep-dive database internals interview';
UPDATE applications SET current_status = 'INTERVIEWED' WHERE application_id = 7;

SET @app_status_change_notes = 'Staff DBA offer extended';
UPDATE applications SET current_status = 'OFFERED' WHERE application_id = 7;

-- Advance App 8 (Sophia @ Google) -> UNDER_REVIEW -> REJECTED
SET @app_status_changed_by_user_id = 3;
SET @app_status_change_notes = 'Under review by Google Cloud hiring manager';
UPDATE applications SET current_status = 'UNDER_REVIEW' WHERE application_id = 8;

SET @app_status_change_notes = 'Role requires 5+ years backend cloud experience; candidate not selected at this time';
UPDATE applications SET current_status = 'REJECTED' WHERE application_id = 8;

-- Advance App 9 (Vikram @ AWS) -> SHORTLISTED -> INTERVIEW_SCHEDULED
SET @app_status_changed_by_user_id = 4;
SET @app_status_change_notes = 'Candidate meets all mandatory AWS & Docker requirements; shortlisted';
UPDATE applications SET current_status = 'SHORTLISTED' WHERE application_id = 9;

SET @app_status_change_notes = 'Architecture interview scheduled';
UPDATE applications SET current_status = 'INTERVIEW_SCHEDULED' WHERE application_id = 9;

-- Advance App 10 (Vikram @ Google) -> UNDER_REVIEW
SET @app_status_changed_by_user_id = 3;
SET @app_status_change_notes = 'Application routed to Cloud Security review committee';
UPDATE applications SET current_status = 'UNDER_REVIEW' WHERE application_id = 10;

-- App 11 (Chloe @ Microsoft) remains in 'APPLIED' stage

-- Advance App 12 (Carlos @ AWS Contract) -> WITHDRAWN
SET @app_status_changed_by_user_id = 9; -- Candidate Carlos Mendez
SET @app_status_change_notes = 'Candidate accepted another opportunity; application withdrawn';
UPDATE applications SET current_status = 'WITHDRAWN' WHERE application_id = 12;

-- Reset session variables
SET @app_status_changed_by_user_id = NULL;
SET @app_status_change_notes = NULL;

-- -----------------------------------------------------------------------------
-- 11. INTERVIEWS TABLE (8 Interview Rounds Across Stages)
-- -----------------------------------------------------------------------------
INSERT INTO interviews (interview_id, application_id, interviewer_name, round_number, round_type, scheduled_at, duration_minutes, meeting_link, location, status, feedback, rating) VALUES
-- Application 1 (Aarav Patel @ Google Cloud)
(1, 1, 'Dr. Aris Thorne', 1, 'TECHNICAL', '2026-10-15 10:00:00', 60, 'https://meet.google.com/abc-defg-hij', 'Google Cloud Hangout', 'COMPLETED', 
 'Exceptional understanding of distributed system architecture, Python GIL constraints, and asyncio performance patterns.', 5),

(2, 1, 'Elena Rostova & Dir. Zhang', 2, 'MANAGERIAL', '2026-10-22 14:00:00', 60, 'https://meet.google.com/xyz-uvwx-rst', 'Sunnyvale Bldg MP2, Conf Rm 4B', 'COMPLETED', 
 'Outstanding leadership and communication skills. Clear alignment with Google Cloud core engineering principles.', 5),

-- Application 3 (Emily Watson @ Microsoft)
(3, 3, 'Nathan Drake', 1, 'SCREENING', '2026-11-05 11:00:00', 45, 'https://teams.microsoft.com/l/meetup-join/12345', 'Microsoft Teams Online', 'COMPLETED', 
 'Solid frontend fundamentals, articulate communicator, and strong mastery of modern React hooks and TypeScript.', 4),

(4, 3, 'Sarah Connor', 2, 'TECHNICAL', '2026-11-12 13:30:00', 75, 'https://teams.microsoft.com/l/meetup-join/67890', 'Microsoft Teams Online', 'COMPLETED', 
 'Built an interactive data table with server-side pagination cleanly within the time limit. Recommended for hire.', 4),

-- Application 5 (Carlos Mendez @ AWS)
(5, 5, 'James T. Kirk', 1, 'TECHNICAL', '2026-12-05 09:30:00', 60, 'https://chime.aws/1234567890', 'AWS Chime Video', 'SCHEDULED', 
 NULL, NULL),

-- Application 7 (Liam O''Connor @ Stripe)
(6, 7, 'Gregory House', 1, 'TECHNICAL', '2026-10-10 15:00:00', 90, 'https://meet.google.com/str-stripe-db', 'Google Meet', 'COMPLETED', 
 'Rare mastery of InnoDB index internals, MVCC locks, and zero-downtime partition management. Absolute top candidate.', 5),

(7, 7, 'Alex Chen & VP Davis', 2, 'FINAL', '2026-10-18 11:00:00', 60, 'https://meet.google.com/str-stripe-vp', 'San Francisco HQ, Boardroom 2', 'COMPLETED', 
 'Culture fit confirmed. Agreed on competitive compensation package.', 5),

-- Application 9 (Vikram Singh @ AWS)
(8, 9, 'Dana Scully', 1, 'TECHNICAL', '2026-12-08 14:00:00', 60, 'https://chime.aws/9876543210', 'AWS Chime Video', 'SCHEDULED', 
 NULL, NULL)
ON DUPLICATE KEY UPDATE feedback = VALUES(feedback);
