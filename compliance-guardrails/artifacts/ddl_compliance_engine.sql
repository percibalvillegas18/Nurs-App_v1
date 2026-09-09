-- =============================================================================
-- HNWMS Compliance Guardrail Layer — DDL (PostgreSQL 14+)
-- Saudi Labor Law (HRSD/MOL) + CBAHI + Hospital Policy automated guardrails
-- =============================================================================
-- Design: a centralized, configurable rules engine evaluated at the point a
-- transaction is attempted (schedule/roster publish, OT approval, leave
-- approval, deployment/assignment, license/competency-driven blocking).
-- Companion docs: compliance-guardrails/01..07_*.md; rule seed data:
-- compliance_rule_catalog.csv
-- =============================================================================

-- ---------------------------------------------------------------
-- 1. MASTER CATALOGUE (the "Compliance_Rule_Master" table)
-- ---------------------------------------------------------------
CREATE TABLE compliance_rule (
    rule_id           BIGSERIAL PRIMARY KEY,
    rule_code         VARCHAR(30)  NOT NULL UNIQUE,   -- e.g. LAB-WH-001, CBA-STAFF-001
    rule_category     VARCHAR(20)  NOT NULL,          -- LABOR / CBAHI / HOSPITAL
    rule_subcategory  VARCHAR(40),                    -- WORKING_HOURS/REST/OVERTIME/LEAVE/CONTRACT/LICENSE/...
    rule_name         VARCHAR(200) NOT NULL,
    rule_description  TEXT,
    legal_reference   VARCHAR(200),                   -- Saudi Labor Law article / CBAHI std / policy ref
    effective_date    DATE         NOT NULL DEFAULT current_date,
    expiry_date       DATE,
    severity_default  VARCHAR(20)  NOT NULL,          -- ADVISORY/WARNING/BLOCK (fallback if no override)
    default_action    VARCHAR(40),                    -- ALLOW/INFORM/WARN/BLOCK/ESCALATE + optional routing
    exception_allowed BOOLEAN      NOT NULL DEFAULT FALSE,
    audit_required    BOOLEAN      NOT NULL DEFAULT TRUE,
    active            BOOLEAN      NOT NULL DEFAULT TRUE,
    owner_role        VARCHAR(100)                    -- role accountable for the rule
);

-- Rule applicability: which employee groups / units / depts / positions a rule
-- applies to (a rule may also apply "all"). 0..N per rule.
CREATE TABLE compliance_rule_scope (
    id          BIGSERIAL PRIMARY KEY,
    rule_id     BIGINT  NOT NULL REFERENCES compliance_rule(rule_id) ON DELETE CASCADE,
    scope_type  VARCHAR(20) NOT NULL,   -- EMPLOYEE_GROUP/DEPARTMENT/UNIT/POSITION/NATIONALITY/ALL
    scope_value VARCHAR(100) NOT NULL,  -- group code, dept code, unit code, position code, nationality, '*'
    UNIQUE (rule_id, scope_type, scope_value)
);

-- Configurable numeric/state threshold + a named parameter key so rules are
-- tunable without code changes (defaults seeded from rule catalog; MUST be
-- validated by HR/Legal/Don against current law & hospital policy).
CREATE TABLE compliance_rule_parameter (
    id           BIGSERIAL PRIMARY KEY,
    rule_id      BIGINT  NOT NULL REFERENCES compliance_rule(rule_id) ON DELETE CASCADE,
    param_key    VARCHAR(60)  NOT NULL,               -- e.g. daily_max_hours, rest_min_hours, ratio_rn_per_pt
    param_value  NUMERIC,
    param_unit   VARCHAR(20),                        -- HOURS/DAYS/PERCENT/RATIO/COUNT
    warn_value   NUMERIC,                            -- value at/below which a WARNING is raised
    effective_from DATE,
    effective_to   DATE,                              -- supports Ramadan season, policy changes
    UNIQUE (rule_id, param_key, effective_from)
);

-- Seasonal / calendar adjustments (e.g., Ramadan reduced working hours,
-- public holidays) — drives automatic recalculation the spec calls for.
CREATE TABLE working_calendar_adjustment (
    id            BIGSERIAL PRIMARY KEY,
    dept_unit_id  BIGINT,             -- null = facility-wide
    adj_type      VARCHAR(20) NOT NULL, -- RAMADAN / PUBLIC_HOLIDAY / WEEKEND
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    daily_hour_limit  NUMERIC,
    weekly_hour_limit NUMERIC,
    apply_to      VARCHAR(30) DEFAULT 'ALL', -- EMPLOYEE_GROUP to limit (e.g., Muslims)
    apply_group   VARCHAR(60),
    active        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------
-- 2. Employee / professional eligibility snapshot (read-side views the
--    engine evaluates). These are NOT duplicates — they are thin references
--    into the Staff Nurse Master + M3 (license/credential) + M8 (competency).
-- ---------------------------------------------------------------
CREATE TABLE eligibility_snapshot (
    id                 BIGSERIAL PRIMARY KEY,
    staff_id           BIGINT NOT NULL,               -- Staff Nurse Master id
    as_of              TIMESTAMPTZ NOT NULL DEFAULT now(),
    employment_active  BOOLEAN,
    license_valid      BOOLEAN,
    license_expiry     DATE,
    credentials_valid  BOOLEAN,
    competency_valid   BOOLEAN,
    competency_expiry  DATE,
    mandatory_training_ok BOOLEAN,
    dept_authorized    BOOLEAN,
    fte                NUMERIC(5,2)
);

-- ---------------------------------------------------------------
-- 3. EVALUATION / DECISION (the compliance decision + result log)
--    Each evaluated transaction (a proposed shift, an OT approval, a leave
--    request, a deployment) runs the applicable rules.
-- ---------------------------------------------------------------
CREATE TABLE evaluation_run (
    run_id         BIGSERIAL PRIMARY KEY,
    eval_target_type VARCHAR(20) NOT NULL,  -- SHIFT/OT/LEAVE/DEPLOYMENT/ASSIGNMENT/PUNCH
    target_ref     VARCHAR(60),             -- reference to the candidate transaction id
    staff_id       BIGINT,
    triggered_by   VARCHAR(100),
    triggered_by_role VARCHAR(100),
    ran_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    overall_verdict VARCHAR(20),            -- ALLOW / WARN / BLOCK  (lowest severity that applies)
    outcome_notes  TEXT
);

CREATE TABLE evaluation_rule_result (
    id               BIGSERIAL PRIMARY KEY,
    run_id           BIGINT NOT NULL REFERENCES evaluation_run(run_id) ON DELETE CASCADE,
    rule_id          BIGINT NOT NULL REFERENCES compliance_rule(rule_id),
    rule_code        VARCHAR(30) NOT NULL,
    severity         VARCHAR(20) NOT NULL,   -- ADVISORY/WARNING/BLOCK
    computed_value   NUMERIC,
    threshold_value  NUMERIC,
    result           VARCHAR(20) NOT NULL,   -- PASS / WARN / FAIL
    message          TEXT,
    evaluated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- 4. EXCEPTION MANAGEMENT ("no bypass by clicking override")
-- ---------------------------------------------------------------
CREATE TABLE guardrail_exception_request (
    exception_id   BIGSERIAL PRIMARY KEY,
    run_id         BIGINT REFERENCES evaluation_run(run_id),
    rule_id        BIGINT NOT NULL REFERENCES compliance_rule(rule_id),
    rule_code      VARCHAR(30) NOT NULL,
    requested_by   VARCHAR(100) NOT NULL,
    requested_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason_required TEXT NOT NULL,            -- free text reason (mandatory)
    risk_assessment TEXT,                     -- documented risk
    mitigation     TEXT,                      -- documented mitigation
    start_time     TIMESTAMPTZ NOT NULL,      -- time-limited window
    end_time       TIMESTAMPTZ NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING/APPROVED/REJECTED/EXPIRED/CANCELLED
    approver_level1 VARCHAR(100),
    approver_level2 VARCHAR(100),            -- depends on severity/rule
    decision_at    TIMESTAMPTZ,
    decision_note  TEXT
);

CREATE TABLE guardrail_exception_approval (
    id               BIGSERIAL PRIMARY KEY,
    exception_id     BIGINT NOT NULL REFERENCES guardrail_exception_request(exception_id) ON DELETE CASCADE,
    approver         VARCHAR(100) NOT NULL,
    approver_role    VARCHAR(100),
    step            INT,
    decision        VARCHAR(20) NOT NULL,    -- APPROVE/REJECT/ESCALATE
    note            TEXT,
    decided_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- 5. AUDIT (immutable trail of every guardrail decision + override)
-- ---------------------------------------------------------------
CREATE TABLE compliance_audit_log (
    id            BIGSERIAL PRIMARY KEY,
    event_time    TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type    VARCHAR(30) NOT NULL,   -- RULE_EVAL / ALLOW / WARN / BLOCK / EXCEPTION_REQUEST / EXCEPTION_APPROVE / EXCEPTION_REJECT / PARAM_CHANGE / RULE_TOGGLE
    actor         VARCHAR(100),
    actor_role    VARCHAR(100),
    rule_code     VARCHAR(30),
    target_type   VARCHAR(20),
    target_ref    VARCHAR(60),
    staff_id      BIGINT,
    before_json   JSONB,
    after_json    JSONB,
    reason        TEXT,
    source        VARCHAR(20)             -- UI / API / SCHEDULER / ENGINE
);
CREATE INDEX idx_comp_audit_time ON compliance_audit_log(event_time);
CREATE INDEX idx_comp_audit_staff ON compliance_audit_log(staff_id);
CREATE INDEX idx_comp_audit_rule  ON compliance_audit_log(rule_code);

-- ---------------------------------------------------------------
-- 6. COMPLIANCE STATUS / SCORE (per employee + per shift aggregate) feeding
--    Module 9 dashboards and the automated compliance status indicators.
-- ---------------------------------------------------------------
CREATE TABLE employee_compliance_status (
    id             BIGSERIAL PRIMARY KEY,
    staff_id       BIGINT NOT NULL,
    as_of          DATE NOT NULL,
    labor_law      VARCHAR(20),    -- COMPLIANT/ADVISORY/WARNING/BLOCKED or per domain status
    contract       VARCHAR(20),
    license        VARCHAR(20),
    credential     VARCHAR(20),
    competency     VARCHAR(20),
    leave          VARCHAR(20),
    training       VARCHAR(20),
    overall_status VARCHAR(20),     -- overall NOT_COMPLIANT/BLOCKED etc.
    overall_score  NUMERIC(5,2),   -- 0..100
    recompute_at   TIMESTAMPTZ,
    UNIQUE (staff_id, as_of)
);

CREATE TABLE shift_compliance_status (
    id             BIGSERIAL PRIMARY KEY,
    shift_ref      VARCHAR(60) NOT NULL,
    unit_code      VARCHAR(30),
    shift_date     DATE NOT NULL,
    working_hours  VARCHAR(20),
    rest_period    VARCHAR(20),
    overtime       VARCHAR(20),
    license        VARCHAR(20),
    competency     VARCHAR(20),
    skill_mix      VARCHAR(20),
    staffing_level VARCHAR(20),
    overall_status VARCHAR(20),     -- e.g. BLOCKED / COMPLIANT
    UNIQUE (shift_ref, shift_date)
);

-- ---------------------------------------------------------------
-- 7. Minimum staffing / skill-mix reference (demand side). Feeds the
--    CBA-STAFF-* and CBA-SKILL-* guardrails. Source: census+acuity (EMR) and
--    approved manpower plan (M1). Stored here as the evaluated requirement.
-- ---------------------------------------------------------------
CREATE TABLE staffing_requirement (
    id             BIGSERIAL PRIMARY KEY,
    unit_code      VARCHAR(30) NOT NULL,
    shift          VARCHAR(20) NOT NULL,        -- MORNING/EVENING/NIGHT/...
    date           DATE NOT NULL,
    census         INT,
    acuity         NUMERIC(4,2),
    required_rn    INT,
    required_senior_rn INT,
    required_charge   INT,
    required_specialty INT,                     -- specialty-qualified count
    required_total INT,
    source_ref     VARCHAR(60),                 -- EMR census / M1 plan reference
    effective_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE skill_mix_rule (
    id             BIGSERIAL PRIMARY KEY,
    unit_code      VARCHAR(30) NOT NULL,
    position_level VARCHAR(10) NOT NULL,        -- e.g. RN / SENIOR_RN / CHARGE / SPECIALTY
    min_required   INT NOT NULL,
    required_qualification VARCHAR(100),
    active         BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------
-- 8. Guardrail reference tables for the transaction being guarded
-- ---------------------------------------------------------------
CREATE TABLE shift_candidate (           -- proposed schedule row BEFORE publish
    id               BIGSERIAL PRIMARY KEY,
    staff_id         BIGINT NOT NULL,
    unit_code        VARCHAR(30) NOT NULL,
    shift_type       VARCHAR(20) NOT NULL,
    shift_date       DATE NOT NULL,
    start_time       TIME,
    end_time         TIME,
    is_overtime      BOOLEAN DEFAULT FALSE,
    status           VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT/EVALUATED/PUBLISHED/BLOCKED
    eval_run_id      BIGINT REFERENCES evaluation_run(run_id)
);

CREATE TABLE leave_request_candidate (
    id          BIGSERIAL PRIMARY KEY,
    staff_id    BIGINT NOT NULL,
    leave_type  VARCHAR(30) NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    days        NUMERIC(4,1),
    status      VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT/EVALUATED/APPROVED/BLOCKED
    eval_run_id BIGINT REFERENCES evaluation_run(run_id)
);
