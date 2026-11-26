# Job Portal and Application Tracking System (ATS)
## Phase 3: Queries, Reports & Analytical Views Specification

---

### 1. Phase 3 Objectives

Phase 3 implements the **query, reporting, analytical, and view layer** of the enterprise Job Portal and Application Tracking System (ATS). 

While Phase 1 established the frozen relational foundation (`sql/schema.sql`) and Phase 2 implemented procedural business workflows and lifecycle triggers (`sql/functions.sql`, `sql/procedures.sql`, `sql/triggers.sql`, `sql/sample_data.sql`), **Phase 3 empowers stakeholders with actionable business intelligence**.

Phase 3 is divided into two SQL implementation artifacts and this architectural document:
1. **`sql/queries.sql`**: A catalog of 68 categorized, production-grade MySQL 8.0+ queries demonstrating fundamental to advanced database management concepts (filtering, multi-table joins, aggregations, subqueries, CTEs, window functions, time-series analysis, and integrity audits).
2. **`sql/views.sql`**: Eight production-ready database views encapsulating complex relational joins, window aggregations, and business metrics for future consumption by Python Flask controllers and user interfaces.
3. **`docs/phase3_queries_reports_views.md`**: Complete architectural documentation, query and view catalogs, DBMS concept mappings, ATS reporting use cases, and verification instructions.

---

### 2. Approved Schema Dependency & Freezing Declaration

> **CRITICAL ARCHITECTURAL GUARANTEE — ZERO SCHEMA MODIFICATION**:
> Phase 3 treats Phase 1 and Phase 2 as **STRICTLY FROZEN**:
> - `sql/schema.sql` (Unchanged)
> - `sql/functions.sql` (Unchanged)
> - `sql/procedures.sql` (Unchanged)
> - `sql/triggers.sql` (Unchanged)
> - `sql/sample_data.sql` (Unchanged)
>
> No tables, columns, data types, primary keys, foreign keys, unique constraints, CHECK constraints, triggers, or stored procedures were added, modified, or dropped. All queries and views operate strictly on the approved 12-table relational schema:
> `roles`, `users`, `candidate_profiles`, `recruiter_profiles`, `skills`, `candidate_skills`, `jobs`, `job_skills`, `resumes`, `applications`, `interviews`, `application_status_history`.

---

### 3. Query Categories Overview

The query suite in `sql/queries.sql` is organized into eight logical sections:

| Section | Focus Area | Query IDs | Core DBMS Mechanisms |
| :--- | :--- | :--- | :--- |
| **Section A** | Basic Select Queries | `Q01` – `Q08` | `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`, `DISTINCT`, numeric/date filtering |
| **Section B** | Relational Joins | `Q09` – `Q18` | `INNER JOIN`, `LEFT JOIN`, multi-table joins (up to 6 tables), `IS NULL` checks |
| **Section C** | Grouping & Aggregation | `Q19` – `Q29` | `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `GROUP BY`, `HAVING` threshold filtering |
| **Section D** | Subqueries | `Q30` – `Q38` | Scalar subqueries, correlated subqueries, `IN`, `EXISTS`, `NOT EXISTS` |
| **Section E** | Advanced Analytics | `Q39` – `Q46` | CTEs (`WITH`), window functions (`DENSE_RANK`, `RANK`, `ROW_NUMBER`, `LAG`), conditional aggregation |
| **Section F** | Date & Time Analysis | `Q47` – `Q53` | `DATE()`, `DAYNAME()`, `DATE_FORMAT()`, `DATEDIFF()`, `TIMESTAMPDIFF()`, lag intervals |
| **Section G** | ATS Executive Reports | `Q54` – `Q61` | Funnel drop-off, recruiter productivity, skill gap matrix, talent search |
| **Section H** | Data Integrity Audits | `Q62` – `Q68` | Referential consistency, resume ownership, clash audits, boundary validations |

---

### 4. Query Catalog

#### Section A — Basic Select Queries

- **Q01 — Active Job Postings**
  - **Purpose**: Retrieve currently active job requisitions ordered by newest creation date.
  - **SQL Section**: Section A
  - **Tables Used**: `jobs`
  - **DBMS Concepts**: `SELECT`, `WHERE status = 'ACTIVE'`, `ORDER BY created_at DESC`
  - **Expected Result**: 5 rows (all active job openings in sample data).

- **Q02 — High-Salary Job Postings Filter**
  - **Purpose**: Identify competitive roles offering base compensation $\ge \$140,000$.
  - **SQL Section**: Section A
  - **Tables Used**: `jobs`
  - **DBMS Concepts**: Numeric inequality filtering (`salary_min >= 140000.00`), multi-column ordering.
  - **Expected Result**: 4 rows (Jobs 4, 2, 1 with minimum salaries from $\$145\text{k}$ to $\$155\text{k}$).

- **Q03 — Experienced Candidate Profiles Filter**
  - **Purpose**: Retrieve senior candidate profiles with $\ge 5.0$ years of verified experience.
  - **SQL Section**: Section A
  - **Tables Used**: `candidate_profiles`
  - **DBMS Concepts**: Decimal attribute filtering (`years_of_experience >= 5.0`), `ORDER BY DESC`.
  - **Expected Result**: 4 rows (Candidates 5, 1, 7, 3 with $5.0$ to $7.0$ years experience).

- **Q04 — Distinct Standardized Skills & Categories**
  - **Purpose**: Display canonical skill taxonomy without duplicate entries.
  - **SQL Section**: Section A
  - **Tables Used**: `skills`
  - **DBMS Concepts**: `DISTINCT`, multi-level ordering (`category ASC, skill_name ASC`).
  - **Expected Result**: 20 rows across Programming, Database, Cloud & DevOps, Web Framework, Core Architecture.

- **Q05 — Recent Job Applications**
  - **Purpose**: Provide real-time operational visibility into the 5 most recently submitted applications.
  - **SQL Section**: Section A
  - **Tables Used**: `applications`
  - **DBMS Concepts**: `ORDER BY applied_at DESC`, `LIMIT 5` pagination.
  - **Expected Result**: 5 rows representing latest candidate submissions.

- **Q06 — Upcoming Scheduled Interviews**
  - **Purpose**: List pending interview rounds scheduled on or after target date.
  - **SQL Section**: Section A
  - **Tables Used**: `interviews`
  - **DBMS Concepts**: `status IN ('SCHEDULED', 'RESCHEDULED')`, DATETIME boundary filtering.
  - **Expected Result**: 2 rows (Interviews 5 and 8 scheduled in December 2026).

- **Q07 — Remote & Hybrid Work Opportunities**
  - **Purpose**: Filter active roles supporting remote or hybrid workplace models.
  - **SQL Section**: Section A
  - **Tables Used**: `jobs`
  - **DBMS Concepts**: Set membership (`IN ('REMOTE', 'HYBRID')`), compound `AND` logic.
  - **Expected Result**: 3 rows (Jobs 1, 3, 4).

- **Q08 — Candidate Profile Search by Degree & Headline**
  - **Purpose**: Text-based candidate search filtering for Master's degree holders with Python expertise.
  - **SQL Section**: Section A
  - **Tables Used**: `candidate_profiles`
  - **DBMS Concepts**: Pattern matching with `LIKE '%...%'`, parenthetical Boolean logic.
  - **Expected Result**: Candidate 6 (Sophia Rodriguez - M.S. in Data Science).

---

#### Section B — Relational Join Queries

- **Q09 — Candidate + Applications Relational Join**
  - **Purpose**: Link candidate personal identities and contact information to their applied jobs.
  - **SQL Section**: Section B
  - **Tables Used**: `candidate_profiles`, `users`, `applications`, `jobs`
  - **DBMS Concepts**: 4-table relational `INNER JOIN` navigating 1:1 and 1:N foreign keys.
  - **Expected Result**: 12 rows (one for each submitted application).

- **Q10 — Candidate + Resume + Application Ownership Linkage**
  - **Purpose**: Validate which specific resume document was attached to each submitted application.
  - **SQL Section**: Section B
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `resumes`, `jobs`
  - **DBMS Concepts**: Multi-table join enforcing composite candidate-resume referential integrity.
  - **Expected Result**: 12 rows with accurate file names and primary resume flags.

- **Q11 — Recruiter + Company + Job Postings**
  - **Purpose**: Present corporate hiring specialists alongside the job requisitions they manage.
  - **SQL Section**: Section B
  - **Tables Used**: `recruiter_profiles`, `users`, `jobs`
  - **DBMS Concepts**: 3-table join connecting authentication identity to corporate domain entities.
  - **Expected Result**: 6 rows covering all jobs across Google, AWS, Microsoft, and Stripe.

- **Q12 — Job + Required & Optional Skills Specification**
  - **Purpose**: Break down technical requirements for job requisitions into mandatory vs preferred tiers.
  - **SQL Section**: Section B
  - **Tables Used**: `jobs`, `recruiter_profiles`, `job_skills`, `skills`
  - **DBMS Concepts**: M:N bridge join with conditional classification (`CASE WHEN js.is_required ...`).
  - **Expected Result**: 23 rows mapping all required skills to their respective job requisitions.

- **Q13 — Candidate + Verified Skills & Proficiencies**
  - **Purpose**: Display candidate skill portfolios, verified proficiency rankings, and experience.
  - **SQL Section**: Section B
  - **Tables Used**: `candidate_profiles`, `users`, `candidate_skills`, `skills`
  - **DBMS Concepts**: M:N bridge join with multi-level sorting (`proficiency_level DESC`).
  - **Expected Result**: 38 rows across all candidate proficiencies.

- **Q14 — Application + Full Lifecycle Status Audit History**
  - **Purpose**: Provide complete chronological audit trails of application state transitions.
  - **SQL Section**: Section B
  - **Tables Used**: `application_status_history`, `applications`, `candidate_profiles`, `users`, `jobs`
  - **DBMS Concepts**: Multi-table join with `LEFT JOIN` on audit actor user account.
  - **Expected Result**: Complete sequential audit log showing who transitioned each status and why.

- **Q15 — Application + Interview Rounds & Evaluations**
  - **Purpose**: Present candidate applications alongside scheduled/completed interview rounds and ratings.
  - **SQL Section**: Section B
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`, `interviews`
  - **DBMS Concepts**: Relational join connecting application pipelines to multi-round interview records.
  - **Expected Result**: 8 rows linking interviews to respective applications and job titles.

- **Q16 — Full ATS 360° Master Application Record**
  - **Purpose**: Provide a comprehensive single-query master record uniting all core entities.
  - **SQL Section**: Section B
  - **Tables Used**: `applications`, `candidate_profiles`, `users (candidates)`, `jobs`, `recruiter_profiles`, `users (recruiters)`, `resumes`
  - **DBMS Concepts**: 6-table relational master join uniting candidate, recruiter, job, resume, and ATS match score.
  - **Expected Result**: 12 rows with exhaustive context for each application.

- **Q17 — Unapplied Jobs & Requisition Application Volume (LEFT JOIN)**
  - **Purpose**: Show all published jobs and total applicant counts, preserving openings with zero applications.
  - **SQL Section**: Section B
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: `LEFT JOIN` with `GROUP BY` and `COUNT(a.application_id)` preservation.
  - **Expected Result**: 6 rows (including Job 6 with 1 application and active jobs with 2–3 applications).

- **Q18 — Applications Without Scheduled Interviews (LEFT JOIN with NULL Check)**
  - **Purpose**: Identify candidate applications that have not yet had any interview scheduled.
  - **SQL Section**: Section B
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`, `interviews`
  - **DBMS Concepts**: `LEFT JOIN` with outer table `WHERE i.interview_id IS NULL` filtering.
  - **Expected Result**: 7 rows (Applications 2, 4, 6, 8, 10, 11, 12).

---

#### Section C — Group By and Aggregate Queries

- **Q19 — Application Volume and Match Score Averages per Job**
  - **Purpose**: Aggregated applicant volume, average match score, minimum score, and maximum score by job.
  - **SQL Section**: Section C
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: `COUNT(a.application_id)`, `ROUND(AVG(a.match_score), 2)`, `MIN()`, `MAX()`, `GROUP BY`.
  - **Expected Result**: 6 rows summarizing job applicant distribution.

- **Q20 — Candidate Application Portfolio and Score Range**
  - **Purpose**: Compute total submissions and match score bounds for each active candidate.
  - **SQL Section**: Section C
  - **Tables Used**: `candidate_profiles`, `users`, `applications`
  - **DBMS Concepts**: Multi-table aggregation, `AVG()`, `MIN()`, `MAX()`.
  - **Expected Result**: 8 rows showing candidate application counts (1 to 2) and score ranges.

- **Q21 — Job Postings Distribution by Recruiter and Company**
  - **Purpose**: Audit recruiter requisition workloads and active vs closed job counts.
  - **SQL Section**: Section C
  - **Tables Used**: `recruiter_profiles`, `users`, `jobs`
  - **DBMS Concepts**: Conditional aggregation using `SUM(CASE WHEN ...)`, `COUNT()`.
  - **Expected Result**: 4 rows (Elena: 2 jobs, Marcus: 2 jobs, Priya: 1 job, Alex: 1 job).

- **Q22 — Application Volume Distribution Across Pipeline Statuses**
  - **Purpose**: Measure platform-wide talent distribution across all 8 ATS pipeline stages.
  - **SQL Section**: Section C
  - **Tables Used**: `applications`
  - **DBMS Concepts**: Single-table `GROUP BY current_status`, `COUNT(*)`.
  - **Expected Result**: 8 rows (APPLIED: 2, UNDER_REVIEW: 2, SHORTLISTED: 1, INTERVIEW_SCHEDULED: 2, INTERVIEWED: 1, OFFERED: 2, REJECTED: 1, WITHDRAWN: 1).

- **Q23 — Average ATS Match Score per Job with Applicant Threshold (HAVING)**
  - **Purpose**: Filter aggregated job scores to include only requisitions with $\ge 2$ applications.
  - **SQL Section**: Section C
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: `GROUP BY` with `HAVING COUNT(a.application_id) >= 2`.
  - **Expected Result**: 5 rows (Jobs 1, 2, 3, 4, 5).

- **Q24 — Candidates with Multiple Submissions and High Average Match (HAVING)**
  - **Purpose**: Identify candidates who have applied to $\ge 2$ jobs with mean match score $\ge 70.00\%$.
  - **SQL Section**: Section C
  - **Tables Used**: `candidate_profiles`, `users`, `applications`
  - **DBMS Concepts**: Multiple aggregate filters inside `HAVING` (`COUNT >= 2 AND AVG >= 70.00`).
  - **Expected Result**: Candidates 1, 2, 3, 7.

- **Q25 — Interview Frequency and Average Feedback Rating per Application**
  - **Purpose**: Track the depth of the interview process and mean rating per candidate application.
  - **SQL Section**: Section C
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`, `interviews`
  - **DBMS Concepts**: `COUNT(i.interview_id)`, `SUM(CASE WHEN i.status = 'COMPLETED' ...)`, `AVG(i.rating)`.
  - **Expected Result**: 5 rows for applications with interview rounds (Apps 1, 3, 5, 7, 9).

- **Q26 — Industry Skill Demand Ranking in Job Requisitions**
  - **Purpose**: Aggregate how frequently skills are demanded across published jobs.
  - **SQL Section**: Section C
  - **Tables Used**: `skills`, `job_skills`
  - **DBMS Concepts**: `COUNT(js.job_id)`, `SUM(CASE WHEN js.is_required = TRUE ...)` breakdown.
  - **Expected Result**: Ranked list of 11 distinct skills required in seed jobs (Docker, Python, AWS at the top).

- **Q27 — Candidate Talent Pool Skill Availability by Category**
  - **Purpose**: Group candidate skills by category and count available candidates.
  - **SQL Section**: Section C
  - **Tables Used**: `skills`, `candidate_skills`
  - **DBMS Concepts**: Multi-level grouping (`category`, `skill_name`), `AVG(years_of_experience)`.
  - **Expected Result**: 16 rows detailing skill inventory across candidate profiles.

- **Q28 — Compensation Statistics Across Workplace Models**
  - **Purpose**: Compute minimum, maximum, and average salary bands grouped by workplace model.
  - **SQL Section**: Section C
  - **Tables Used**: `jobs`
  - **DBMS Concepts**: `MIN(salary_min)`, `MAX(salary_max)`, `AVG(salary_min)`, `AVG(salary_max)`.
  - **Expected Result**: 3 rows (HYBRID, ON_SITE, REMOTE).

- **Q29 — High-Volume Job Requisitions (HAVING clause)**
  - **Purpose**: Highlight popular jobs attracting more than 2 applications.
  - **SQL Section**: Section C
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: Strict `HAVING COUNT(a.application_id) > 2` filtering.
  - **Expected Result**: Job 1 (Senior Cloud Python Backend Engineer with 3 applications).

---

#### Section D — Subqueries

- **Q30 — Candidates Who Have Applied to at Least One Job (IN Subquery)**
  - **Purpose**: Filter candidates whose IDs exist in the applications table.
  - **SQL Section**: Section D
  - **Tables Used**: `candidate_profiles`, `users`, `applications`
  - **DBMS Concepts**: Independent subquery evaluated within an `IN` predicate.
  - **Expected Result**: 8 rows (all registered candidates in sample data).

- **Q31 — Candidates Who Have Never Applied (NOT EXISTS Correlated Subquery)**
  - **Purpose**: Detect passive registered candidates with zero submitted applications.
  - **SQL Section**: Section D
  - **Tables Used**: `candidate_profiles`, `users`, `applications`
  - **DBMS Concepts**: Correlated subquery with `NOT EXISTS (SELECT 1 FROM applications a WHERE ...)`.
  - **Expected Result**: 0 rows (demonstrating all seed candidates are active applicants).

- **Q32 — Job Requisitions That Have Received Applications (EXISTS Subquery)**
  - **Purpose**: Identify jobs with active candidate engagement.
  - **SQL Section**: Section D
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: Correlated subquery with `EXISTS`.
  - **Expected Result**: 6 rows (all seed jobs have received at least 1 application).

- **Q33 — Jobs That Have Received Zero Applications (NOT EXISTS Subquery)**
  - **Purpose**: Identify dormant job listings requiring marketing or sourcing attention.
  - **SQL Section**: Section D
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: Correlated subquery with `NOT EXISTS`.
  - **Expected Result**: 0 rows in seed dataset.

- **Q34 — Applications Exceeding the Platform-Wide Average Match Score**
  - **Purpose**: Isolate high-fit applications performing above the system-wide mean.
  - **SQL Section**: Section D
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`
  - **DBMS Concepts**: Scalar subquery inside `WHERE a.match_score > (SELECT AVG(...) FROM applications)`.
  - **Expected Result**: Top applications (Apps 7, 1, 5, 3, 9, 6) scoring above the global average.

- **Q35 — Job Openings Receiving Above-Average Application Volume**
  - **Purpose**: Detect high-traffic job posts that exceed the mean applicant volume per job.
  - **SQL Section**: Section D
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: Subquery inside `HAVING` comparing group count with system mean (`COUNT(*) / COUNT(DISTINCT job_id)`).
  - **Expected Result**: Job 1 (3 applications vs 2.0 platform average).

- **Q36 — Candidates Possessing Python Skill with Advanced or Expert Proficiency**
  - **Purpose**: Talent search finding candidates mastering Python via a correlated subquery.
  - **SQL Section**: Section D
  - **Tables Used**: `candidate_profiles`, `users`, `candidate_skills`, `skills`
  - **DBMS Concepts**: Correlated subquery with `EXISTS` and multiple predicate filters.
  - **Expected Result**: Candidate 1 (Aarav Patel - EXPERT) and Candidate 6 (Sophia Rodriguez - EXPERT).

- **Q37 — Recruiters Publishing More Jobs Than the Platform Average**
  - **Purpose**: Highlight prolific recruiters managing above-average requisition counts.
  - **SQL Section**: Section D
  - **Tables Used**: `recruiter_profiles`, `users`, `jobs`
  - **DBMS Concepts**: Subquery in `HAVING` comparing group count with recruiter mean ($6 / 4 = 1.5$).
  - **Expected Result**: Elena Rostova (2 jobs) and Marcus Vance (2 jobs).

- **Q38 — Candidates with Above-Average Match Scores Across Applications**
  - **Purpose**: Filter candidates whose personal mean match score outperforms the platform average.
  - **SQL Section**: Section D
  - **Tables Used**: `candidate_profiles`, `users`, `applications`
  - **DBMS Concepts**: Scalar subquery combined with `GROUP BY` and `HAVING AVG(a.match_score) > (SELECT AVG...)`.
  - **Expected Result**: Candidates with above-average cumulative match performance.

---

#### Section E — Advanced Analytical Queries (MySQL 8.0+)

- **Q39 — Candidate Ranking per Job Requisition**
  - **Purpose**: Rank all applicants for each job by ATS match score, with tie-handling.
  - **SQL Section**: Section E
  - **Tables Used**: `applications`, `jobs`, `recruiter_profiles`, `candidate_profiles`, `users`
  - **DBMS Concepts**: `DENSE_RANK() OVER (PARTITION BY a.job_id ORDER BY a.match_score DESC)`.
  - **Expected Result**: 12 rows partitioned by job opening with applicant ranks $1, 2, 3\dots$.

- **Q40 — Job Application Popularity Ranking**
  - **Purpose**: Rank job openings by total application volume using window functions.
  - **SQL Section**: Section E
  - **Tables Used**: `jobs`, `recruiter_profiles`, `applications`
  - **DBMS Concepts**: `RANK() OVER (ORDER BY COUNT(a.application_id) DESC)`.
  - **Expected Result**: 6 rows; Job 1 ranked #1 (3 apps), Jobs 2–5 tied at rank #2 (2 apps each).

- **Q41 — Recruiter Hiring Pipeline Productivity Matrix (Multi-CTE)**
  - **Purpose**: Synthesize recruiter performance across postings, applicant volume, and interviews.
  - **SQL Section**: Section E
  - **Tables Used**: `recruiter_profiles`, `users`, `jobs`, `applications`, `interviews`
  - **DBMS Concepts**: Multiple CTEs (`WITH recruiter_jobs AS ..., recruiter_apps AS ..., recruiter_interviews AS ...`), window ranking.
  - **Expected Result**: 4 rows summarizing full hiring pipeline volume by recruiter.

- **Q42 — Enterprise Recruitment Funnel with Drop-off & Conversion Rates**
  - **Purpose**: Calculate cumulative stage transitions and conversion percentages across the funnel.
  - **SQL Section**: Section E
  - **Tables Used**: `applications`
  - **DBMS Concepts**: CTE with conditional aggregation (`SUM(CASE WHEN ...)`), relative conversion percentages.
  - **Expected Result**: 1 row detailing counts and drop-off rates across stages 1 to 6.

- **Q43 — Candidate Application Velocity & Cumulative Timeline**
  - **Purpose**: Track the sequence and running cumulative application count for each candidate over time.
  - **SQL Section**: Section E
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`
  - **DBMS Concepts**: `ROW_NUMBER() OVER (...)`, `COUNT(...) OVER (PARTITION BY ... ORDER BY ... ROWS UNBOUNDED PRECEDING)`.
  - **Expected Result**: 12 rows showing progressive cumulative counts ($1, 2\dots$) per candidate.

- **Q44 — Interviewer Performance Scorecard & Evaluation Consistency**
  - **Purpose**: Audit evaluation rigor, average ratings, and round completion rate per interviewer.
  - **SQL Section**: Section E
  - **Tables Used**: `interviews`
  - **DBMS Concepts**: Conditional aggregation, `ROUND(AVG(rating), 2)`, high-score rate computation.
  - **Expected Result**: 7 rows covering all active interviewers and panel configurations.

- **Q45 — Skill Demand Market Share & Cumulative Distribution**
  - **Purpose**: Calculate each skill's percentage share of total job market requirements.
  - **SQL Section**: Section E
  - **Tables Used**: `skills`, `job_skills`
  - **DBMS Concepts**: CTE with window function `SUM(demand_frequency) OVER ()`, `DENSE_RANK()`.
  - **Expected Result**: 11 rows ranked by market demand share percentage.

- **Q46 — Candidate-to-Job Skill Gap & Competency Coverage Analysis**
  - **Purpose**: Match candidate profile skills against job requirements to compute matched skills, missing required skills, and overall skill coverage ratio.
  - **SQL Section**: Section E
  - **Tables Used**: `applications`, `job_skills`, `candidate_skills`, `candidate_profiles`, `users`, `jobs`
  - **DBMS Concepts**: Multi-table CTE matching engine, skill inventory gap calculation.
  - **Expected Result**: 12 rows comparing required vs possessed skills for each application.

---

#### Section F — Date and Time Analysis

- **Q47 — Daily Application Intake and Day-of-Week Distribution**
  - **Purpose**: Measure candidate submission patterns across days of the week.
  - **SQL Section**: Section F
  - **Tables Used**: `applications`
  - **DBMS Concepts**: `DAYNAME(applied_at)`, `DAYOFWEEK(applied_at)` grouping and sorting.
  - **Expected Result**: Weekly intake breakdown with average match score per day.

- **Q48 — Monthly Application Volume and Job Requisition Creation Trend**
  - **Purpose**: Monitor platform monthly velocity for application throughput and job postings.
  - **SQL Section**: Section F
  - **Tables Used**: `applications`
  - **DBMS Concepts**: `DATE_FORMAT(applied_at, '%Y-%m')` grouping.
  - **Expected Result**: Monthly aggregated applicant trends.

- **Q49 — Job Requisition Urgency and Days Remaining Until Application Deadline**
  - **Purpose**: Classify active jobs by urgency based on calendar days remaining before deadline.
  - **SQL Section**: Section F
  - **Tables Used**: `jobs`
  - **DBMS Concepts**: `DATEDIFF(deadline_date, CURRENT_DATE)`, `CASE` statement urgency classification.
  - **Expected Result**: 6 rows classified as OPEN, URGENT, CRITICAL, or EXPIRED.

- **Q50 — Upcoming Interview Operational Calendar (Next 30 Days)**
  - **Purpose**: Display upcoming interviews scheduled within a 30-day operating window.
  - **SQL Section**: Section F
  - **Tables Used**: `interviews`, `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`
  - **DBMS Concepts**: DATETIME comparisons, status filtering, multi-table coordination.
  - **Expected Result**: 2 rows for pending December 2026 interviews.

- **Q51 — Past Completed Interviews Duration and Evaluation Audit**
  - **Purpose**: Review concluded interview rounds with elapsed days and feedback ratings.
  - **SQL Section**: Section F
  - **Tables Used**: `interviews`
  - **DBMS Concepts**: `DATEDIFF(CURRENT_TIMESTAMP, scheduled_at)`, duration check.
  - **Expected Result**: 6 rows for completed interviews with ratings and feedback notes.

- **Q52 — Application Velocity & Time Elapsed Since Latest Update**
  - **Purpose**: Compute total hours and days elapsed between application creation and latest update.
  - **SQL Section**: Section F
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`
  - **DBMS Concepts**: `TIMESTAMPDIFF(HOUR, applied_at, updated_at)`, `TIMESTAMPDIFF(DAY, ...)`.
  - **Expected Result**: 12 rows tracking lifecycle duration.

- **Q53 — Audit Trail Transition Duration Between Status Changes**
  - **Purpose**: Calculate exact minutes spent in each pipeline state using the `LAG()` window function.
  - **SQL Section**: Section F
  - **Tables Used**: `application_status_history`
  - **DBMS Concepts**: `LAG(changed_at) OVER (PARTITION BY application_id ORDER BY changed_at ASC)`, `TIMESTAMPDIFF(MINUTE, ...)`.
  - **Expected Result**: Step-by-step state transition duration log across all applications.

---

#### Section G — ATS Business Intelligence & Reporting Suite

- **Q54 — Candidate Application 360° Summary Report**
  - **Purpose**: Executive summary of each candidate's career portal engagement, offers, and average score.
  - **SQL Section**: Section G
  - **Tables Used**: `candidate_profiles`, `users`, `applications`
  - **DBMS Concepts**: Multi-table aggregation, `SUM(CASE WHEN status = 'OFFERED' ...)`.
  - **Expected Result**: 8 rows summarizing all candidates (Aarav and Liam with 1 offer each).

- **Q55 — Candidate Job Application History & Status Log**
  - **Purpose**: Complete personal application timeline for candidate tracking.
  - **SQL Section**: Section G
  - **Tables Used**: `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`
  - **DBMS Concepts**: Chronological history join.
  - **Expected Result**: 12 rows detailing all submissions by candidate.

- **Q56 — Comprehensive Job Requisition Performance Report**
  - **Purpose**: Deep-dive operational dashboard for job openings, status breakdown, and ATS scores.
  - **SQL Section**: Section G
  - **Tables Used**: `jobs`, `recruiter_profiles`, `users`, `applications`
  - **DBMS Concepts**: Multi-table conditional aggregation across all 8 pipeline statuses.
  - **Expected Result**: 6 rows detailing pipeline distribution for every job opening.

- **Q57 — Recruiter Productivity & Talent Conversion Report**
  - **Purpose**: Assess recruiter talent funnel velocity from requisition posting to formal hire offer.
  - **SQL Section**: Section G
  - **Tables Used**: `recruiter_profiles`, `users`, `jobs`, `applications`, `interviews` (via pre-aggregated CTEs)
  - **DBMS Concepts**: Pre-aggregated CTEs to eliminate join fan-out, requisition-to-hire conversion rate calculation (`total_offers / total_applications * 100`).
  - **Expected Result**: 4 rows covering all recruiters (Elena: 5 apps, 1 offer, 20.00% conversion; Alex: 2 apps, 1 offer, 50.00% conversion).

- **Q58 — Platform-Wide Recruitment Funnel Report**
  - **Purpose**: Standard executive report tracking funnel conversion drop-off from intake to hire.
  - **SQL Section**: Section G
  - **Tables Used**: `applications`
  - **DBMS Concepts**: Subquery CTE with stage-to-stage percentage calculation.
  - **Expected Result**: 1 row summarizing platform funnel metrics.

- **Q59 — Master Interview Pipeline & Operational Schedule**
  - **Purpose**: Full operational view of scheduled interviews for talent coordination teams.
  - **SQL Section**: Section G
  - **Tables Used**: `interviews`, `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`
  - **DBMS Concepts**: Comprehensive multi-table interview join.
  - **Expected Result**: 2 rows for scheduled upcoming rounds.

- **Q60 — Market Skill Demand vs Candidate Pool Supply Gap Analysis**
  - **Purpose**: Contrast the percentage of job requisitions requesting a skill against the percentage of candidates possessing that skill to reveal talent shortages.
  - **SQL Section**: Section G
  - **Tables Used**: `skills`, `job_skills`, `candidate_skills`, `jobs`, `candidate_profiles`
  - **DBMS Concepts**: Two independent CTEs joined on master skill entity with gap indicator.
  - **Expected Result**: Full skill catalog comparison with demand-supply gap percentages.

- **Q61 — Executive Talent Search Query (Multi-Skill Matching)**
  - **Purpose**: Identify elite candidates holding simultaneous competency in Python, MySQL, and Docker.
  - **SQL Section**: Section G
  - **Tables Used**: `candidate_profiles`, `users`, `candidate_skills`, `skills`
  - **DBMS Concepts**: Relational division using `GROUP BY` and `HAVING COUNT(DISTINCT s.skill_name) = 3`.
  - **Expected Result**: Candidate 1 (Aarav Patel possessing all 3 required technologies).

---

#### Section H — Data Validation & Integrity Auditing Queries

- **Q62 — Resume Ownership Integrity Audit**
  - **Purpose**: Confirm that all applications strictly reference resumes belonging to the applicant.
  - **SQL Section**: Section H
  - **Tables Used**: `applications`, `resumes`
  - **DBMS Concepts**: Referential integrity audit (`a.candidate_id <> r.candidate_id`).
  - **Expected Result**: **0 rows** (100% compliance with Phase 1 composite foreign key `fk_applications_resume_owner`).

- **Q63 — Duplicate Application Integrity Check**
  - **Purpose**: Verify that no candidate has multiple applications for the same job requisition.
  - **SQL Section**: Section H
  - **Tables Used**: `applications`
  - **DBMS Concepts**: `HAVING COUNT(*) > 1` duplicate detection.
  - **Expected Result**: **0 rows** (100% compliance with unique constraint `uq_job_candidate`).

- **Q64 — Match Score Boundary Integrity Check**
  - **Purpose**: Verify that all calculated ATS match scores strictly fall in the range $[0.00, 100.00]$.
  - **SQL Section**: Section H
  - **Tables Used**: `applications`
  - **DBMS Concepts**: Boundary check (`match_score < 0.00 OR match_score > 100.00`).
  - **Expected Result**: **0 rows** (100% compliance with `chk_app_match_score`).

- **Q65 — Status History Audit Consistency Check**
  - **Purpose**: Ensure every application has an initial audit log record and latest status alignment.
  - **SQL Section**: Section H
  - **Tables Used**: `applications`, `application_status_history`
  - **DBMS Concepts**: `LEFT JOIN` audit history checking for orphan applications without audit log.
  - **Expected Result**: **0 rows** (100% compliance with Phase 2 trigger `trg_applications_after_insert`).

- **Q66 — Interviewer Calendar Overlap Conflict Audit**
  - **Purpose**: Detect any invalid overlapping active interviews for the SAME interviewer.
  - **SQL Section**: Section H
  - **Tables Used**: `interviews (self-join)`
  - **DBMS Concepts**: Self-join on active interviews matching `interviewer_name` with time overlap.
  - **Expected Result**: **0 rows** (100% compliance with `sp_schedule_interview` and Phase 2 triggers).

- **Q67 — Orphan Profile & Referential Integrity Check**
  - **Purpose**: Verify that candidate and recruiter profiles always have corresponding user accounts.
  - **SQL Section**: Section H
  - **Tables Used**: `candidate_profiles`, `recruiter_profiles`, `users`
  - **DBMS Concepts**: `LEFT JOIN` checking for `NULL` parent foreign key references.
  - **Expected Result**: **0 rows** (100% referential integrity across 1:1 specialization tables).

- **Q68 — Application Deadline Compliance Audit**
  - **Purpose**: Audit whether any application was recorded after the job requisition's deadline date.
  - **SQL Section**: Section H
  - **Tables Used**: `applications`, `jobs`
  - **DBMS Concepts**: Date comparison (`DATE(a.applied_at) > j.deadline_date`).
  - **Expected Result**: **0 rows** (100% compliance with procedural validation in `sp_apply_job`).

---

### 5. View Catalog

All eight production-grade views are created using `CREATE OR REPLACE VIEW` in `sql/views.sql`:

#### View 1: `vw_candidate_application_dashboard`
- **Purpose**: Provides a unified portal view for candidates and recruiters displaying application progress, company details, match scores, and attached resumes.
- **Source Tables**: `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`, `resumes`
- **Important Columns**:
  - `application_id`, `candidate_id`, `candidate_name`, `candidate_email`, `candidate_headline`, `candidate_experience`
  - `job_id`, `job_title`, `company_name`, `job_location`, `employment_type`, `workplace_type`
  - `applied_at`, `current_status`, `match_score`, `resume_id`, `resume_file_name`, `is_primary_resume`
- **Business Use**: Powers candidate "My Applications" dashboard and recruiter pipeline views in future web UI.
- **Expected Result**: 12 rows representing all submitted applications with complete relational context.

#### View 2: `vw_recruiter_job_performance`
- **Purpose**: Analyzes job opening throughput, application attraction volume, match quality, interview volume, and offers extended per job posting.
- **Source Tables**: `recruiter_profiles`, `users`, `jobs`, `applications`, `interviews` (via pre-aggregated CTEs)
- **Important Columns**:
  - `recruiter_id`, `recruiter_name`, `company_name`, `recruiter_designation`
  - `job_id`, `job_title`, `job_status`, `employment_type`, `workplace_type`, `min_experience_years`, `salary_min`, `salary_max`, `deadline_date`
  - `total_applications`, `avg_match_score`, `total_interviews`, `total_offers`
- **Business Use**: Powers the corporate recruiter job management screen and recruitment KPI audits.
- **Expected Result**: 6 rows covering all job openings across the 4 corporate recruiters, with application counts, averages, and offer metrics calculated independently from interview records to prevent join multiplication.

#### View 3: `vw_application_funnel`
- **Purpose**: Provides standard stage-level reporting showing applicant count and percentage share across all 8 lifecycle states.
- **Source Tables**: `applications` (via CTE and cross join)
- **Important Columns**:
  - `stage_order` (1 to 8), `application_status`, `applicant_count`, `pct_of_total_applications`
- **Business Use**: Powers ATS executive drop-off dashboards and pipeline visualizers.
- **Expected Result**: 8 rows detailing distribution from `APPLIED` (16.67%) to `OFFERED` (16.67%).

#### View 4: `vw_interview_schedule`
- **Purpose**: Operational interview schedule tracking scheduled, in-progress, and completed rounds with candidate contact info, meeting links, room locations, and evaluation scores.
- **Source Tables**: `interviews`, `applications`, `candidate_profiles`, `users`, `jobs`, `recruiter_profiles`
- **Important Columns**:
  - `interview_id`, `application_id`, `candidate_id`, `candidate_name`, `candidate_email`, `candidate_phone`
  - `job_id`, `job_title`, `company_name`, `interviewer_name`, `round_number`, `round_type`
  - `scheduled_at`, `duration_minutes`, `meeting_link`, `location`, `interview_status`, `feedback`, `rating`
- **Business Use**: Powers interview coordination calendars and candidate interview invitation emails.
- **Expected Result**: 8 rows covering all interview rounds in the system.

#### View 5: `vw_job_skill_requirements`
- **Purpose**: Normalized catalog of all job openings linked to their skill requisitions, classifying requirements as MANDATORY or PREFERRED along with required experience.
- **Source Tables**: `jobs`, `recruiter_profiles`, `job_skills`, `skills`
- **Important Columns**:
  - `job_id`, `job_title`, `company_name`, `job_status`
  - `skill_id`, `skill_name`, `skill_category`, `is_required`, `requirement_type`, `min_years_experience`
- **Business Use**: Powers job detail pages and automated skill-gap matching algorithms.
- **Expected Result**: 23 rows detailing all technical requirements across the 6 job postings.

#### View 6: `vw_candidate_skill_profile`
- **Purpose**: Standardized view of candidate talent profiles and skill matrices, featuring categorized skills, verified years of experience, and proficiency rankings.
- **Source Tables**: `candidate_profiles`, `users`, `candidate_skills`, `skills`
- **Important Columns**:
  - `candidate_id`, `candidate_name`, `candidate_email`, `current_location`, `total_experience_years`, `highest_education`
  - `skill_id`, `skill_name`, `skill_category`, `proficiency_level`, `skill_experience_years`
- **Business Use**: Powers candidate profile views and recruiter candidate-search engines.
- **Expected Result**: 38 rows representing candidate skill competencies across the 8 registered candidates.

#### View 7: `vw_job_application_statistics`
- **Purpose**: Aggregated analytics for job openings detailing applicant volume, ATS match score distribution (min, max, avg), and stage-by-stage candidate pipeline counts.
- **Source Tables**: `jobs`, `recruiter_profiles`, `users`, `applications`
- **Important Columns**:
  - `job_id`, `job_title`, `company_name`, `recruiter_name`, `job_status`, `employment_type`, `workplace_type`, `salary_min`, `salary_max`
  - `total_applications`, `min_match_score`, `max_match_score`, `avg_match_score`
  - `applied_count`, `under_review_count`, `shortlisted_count`, `interview_scheduled_count`, `interviewed_count`, `offered_count`, `rejected_count`, `withdrawn_count`
- **Business Use**: Powers recruiter job requisition performance tables and analytics.
- **Expected Result**: 6 rows detailing pipeline distribution for every job opening.

#### View 8: `vw_candidate_application_statistics`
- **Purpose**: Comprehensive candidate analytics detailing individual applicant engagement, total submissions, active opportunities, average match percentages, completed interviews, and offer conversion.
- **Source Tables**: `candidate_profiles`, `users`, `applications`, `interviews` (via pre-aggregated CTEs)
- **Important Columns**:
  - `candidate_id`, `candidate_name`, `candidate_email`, `headline`, `years_of_experience`, `highest_education`
  - `total_applications`, `active_applications`, `avg_match_score`, `highest_match_score`, `total_interviews`, `offers_received`, `rejections_received`
- **Business Use**: Powers candidate summary cards and talent pool analytics.
- **Expected Result**: 8 rows summarizing candidate engagement across the platform, with application counts, active status tallies, and score averages isolated from interview volume.

---

### 6. DBMS Concepts Demonstrated

Phase 3 systematically demonstrates the depth and breadth of modern relational database management:

1. **SELECT & Projection**: Explicit column projection without `SELECT *`, renaming columns with clean, descriptive aliases (`candidate_name`, `avg_match_score`).
2. **Filtering & Predicates**:
   - Numeric range filters (`salary_min >= 140000.00`, `years_of_experience >= 5.0`).
   - Set membership filtering (`status IN ('SCHEDULED', 'RESCHEDULED')`).
   - String pattern matching (`highest_education LIKE '%Master%'`).
   - Temporal window boundaries (`scheduled_at >= '2026-12-01 00:00:00'`).
3. **Relational Joins**:
   - `INNER JOIN`: Exact referential navigation across 1:1, 1:N, and M:N relationships.
   - `LEFT JOIN`: Preserving unmatched parent records (e.g. jobs with 0 applications, applications with 0 interviews).
   - Multi-Table Joins: Seamless joining of up to 6 tables simultaneously (`applications` $\rightarrow$ `candidate_profiles` $\rightarrow$ `users` $\rightarrow$ `jobs` $\rightarrow$ `recruiter_profiles` $\rightarrow$ `resumes`).
   - Self-Joins: Detecting temporal conflicts by joining `interviews` onto itself (`Q66`).
4. **Aggregation & Grouping**:
   - Aggregate functions: `COUNT()`, `SUM()`, `AVG()`, `MIN()`, `MAX()`.
   - `GROUP BY`: Complete adherence to ANSI standard and MySQL `ONLY_FULL_GROUP_BY` strict mode.
   - `HAVING`: Proper post-aggregation filtering on group thresholds (`HAVING COUNT(a.application_id) >= 2`) rather than erroneous `WHERE` filtering on aggregates.
5. **Subqueries**:
   - Scalar subqueries returning single numeric values for relative filtering (`Q34`, `Q38`).
   - Independent subqueries with `IN` (`Q30`).
   - Correlated subqueries with `EXISTS` and `NOT EXISTS` (`Q31`, `Q32`, `Q33`, `Q36`).
   - Subqueries inside `HAVING` comparing group metrics with platform means (`Q35`, `Q37`).
6. **Common Table Expressions (CTEs)**:
   - Single and chained CTEs (`WITH ... AS (...)`) breaking complex multi-step transformations into clear, readable stages (`Q41`, `Q42`, `Q45`, `Q46`, `Q58`, `Q60`).
7. **Window Functions (MySQL 8.0+)**:
   - `DENSE_RANK() OVER (PARTITION BY ... ORDER BY ...)`: Competitive candidate ranking within job requisitions (`Q39`, `Q45`).
   - `RANK() OVER (ORDER BY ...)`: Global popularity ranking with tie-skipping (`Q40`).
   - `ROW_NUMBER() OVER (...)`: Candidate application sequence numbering (`Q43`).
   - Running totals: `COUNT() OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` (`Q43`).
   - Window grand totals: `SUM(...) OVER ()` to compute percentage share of market demand (`Q45`).
   - `LAG() OVER (...)`: Calculating exact elapsed time between successive lifecycle transitions in audit logs (`Q53`).
8. **Conditional Aggregation**:
   - `SUM(CASE WHEN status = 'OFFERED' THEN 1 ELSE 0 END)` to pivot categorical row data into multi-column metrics within single queries (`Q21`, `Q25`, `Q42`, `Q56`, `Q57`, `vw_job_application_statistics`).
9. **Date and Time Functions**:
   - Date extraction and formatting: `DATE()`, `DAYNAME()`, `DATE_FORMAT()`.
   - Date arithmetic: `scheduled_at + INTERVAL duration_minutes MINUTE`, `DATEDIFF()`, `TIMESTAMPDIFF()`.
10. **Database Views**:
    - Abstraction layer decoupling storage schemas from presentation needs.
    - Encapsulating complex analytical logic into reusable virtual tables.

---

### 7. ATS Reporting Use Cases for Future Phases

The views and queries developed in Phase 3 are specifically designed to serve as the backend data sources for the Flask web application in Phase 5:

1. **Candidate Dashboard (`vw_candidate_application_dashboard`)**:
   - Visualizes all applied jobs, company names, current pipeline stages, and calculated ATS match percentages.
   - Enables candidates to verify their attached resume document and review submission timestamps.
2. **Recruiter Job Management Portal (`vw_recruiter_job_performance`)**:
   - Provides recruiters with real-time requisition health cards: total applicant volume, mean applicant match quality, interview pipeline counts, and extended offers.
3. **Application Tracking Pipeline Visualizer (`vw_application_funnel`)**:
   - Powers interactive funnel charts showing conversion rates from initial application to formal hire offer, pinpointing drop-off bottlenecks.
4. **Interview Operations Calendar (`vw_interview_schedule`)**:
   - Drives candidate interview scheduling screens, providing interviewer names, meeting links, room locations, and evaluation scorecards.
5. **Talent Search Engine (`vw_candidate_skill_profile`, `Q61`)**:
   - Allows recruiters to execute multi-criteria candidate searches matching specific skill profiles, experience thresholds, and verified proficiency levels.
6. **Executive Requisition Analytics (`vw_job_application_statistics`)**:
   - Provides leadership with deep visibility into applicant volume and stage distribution across departments and office locations.
7. **Talent Pool Analytics (`vw_candidate_application_statistics`)**:
   - Identifies high-performing candidates with top match scores across multiple roles for accelerated hiring pipelines.

---

### 8. Testing and Verification Guide

To execute and verify Phase 3 queries and views, use standard MySQL 8.0+ CLI or MySQL Workbench:

#### Step 1: Execute Views Definition Script
```bash
mysql -u root -p job_portal_ats < sql/views.sql
```
*Expected Outcome*: Script completes with zero errors. All 8 views are created in `job_portal_ats`.

#### Step 2: Verify View Creation
```sql
USE job_portal_ats;
SHOW FULL TABLES WHERE Table_type = 'VIEW';
```
*Expected Outcome*: Exactly 8 views listed:
- `vw_application_funnel`
- `vw_candidate_application_dashboard`
- `vw_candidate_application_statistics`
- `vw_candidate_skill_profile`
- `vw_interview_schedule`
- `vw_job_application_statistics`
- `vw_job_skill_requirements`
- `vw_recruiter_job_performance`

#### Step 3: Execute Queries Suite
```bash
mysql -u root -p job_portal_ats < sql/queries.sql
```
*Expected Outcome*: All 68 queries execute cleanly without syntax or strict mode errors.

#### Step 4: Run Data Integrity Audits (Section H Verification)
Execute queries `Q62` through `Q68`:
```sql
USE job_portal_ats;

-- 1. Resume Ownership Check (Q62) -> Expected: 0 rows
SELECT a.application_id FROM applications a INNER JOIN resumes r ON a.resume_id = r.resume_id WHERE a.candidate_id <> r.candidate_id;

-- 2. Duplicate Application Check (Q63) -> Expected: 0 rows
SELECT job_id, candidate_id FROM applications GROUP BY job_id, candidate_id HAVING COUNT(*) > 1;

-- 3. Match Score Range Check (Q64) -> Expected: 0 rows
SELECT application_id FROM applications WHERE match_score < 0.00 OR match_score > 100.00;

-- 4. Status History Integrity Check (Q65) -> Expected: 0 rows
SELECT a.application_id FROM applications a LEFT JOIN application_status_history h ON a.application_id = h.application_id GROUP BY a.application_id, a.current_status HAVING COUNT(h.history_id) = 0;

-- 5. Interview Conflict Check (Q66) -> Expected: 0 rows
SELECT i1.interview_id, i2.interview_id FROM interviews i1 INNER JOIN interviews i2 ON i1.interviewer_name = i2.interviewer_name AND i1.interview_id < i2.interview_id AND i1.status IN ('SCHEDULED', 'RESCHEDULED') AND i2.status IN ('SCHEDULED', 'RESCHEDULED') AND (i1.scheduled_at < i2.scheduled_at + INTERVAL i2.duration_minutes MINUTE) AND (i2.scheduled_at < i1.scheduled_at + INTERVAL i1.duration_minutes MINUTE);

-- 6. Orphan Profile Check (Q67) -> Expected: 0 rows
SELECT cp.candidate_id FROM candidate_profiles cp LEFT JOIN users u ON cp.user_id = u.user_id WHERE u.user_id IS NULL;

-- 7. Application Deadline Check (Q68) -> Expected: 0 rows
SELECT a.application_id FROM applications a INNER JOIN jobs j ON a.job_id = j.job_id WHERE j.deadline_date IS NOT NULL AND DATE(a.applied_at) > j.deadline_date;
```
*Verification Confirmation*: Every audit query returns **0 rows**, proving 100% adherence to all Phase 1 schema constraints, Phase 2 procedural invariants, and interview conflict rules.
