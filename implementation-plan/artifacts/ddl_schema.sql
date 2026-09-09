-- =============================================================
-- Org Structure, Department Registry & Bed Capacity — DDL (PostgreSQL)
-- Companion to implementation-plan/01..06_*.md
-- Dialect: PostgreSQL 14+. Adjust types for target RDBMS.
-- =============================================================

-- ---- Location / operational domain (system of record) ----
CREATE TABLE facility (
    facility_id   BIGSERIAL PRIMARY KEY,
    facility_code VARCHAR(20)  NOT NULL UNIQUE,
    name          VARCHAR(200) NOT NULL,
    region        VARCHAR(100),
    city          VARCHAR(100),
    mrn_prefix    VARCHAR(10),
    licensor      VARCHAR(100),
    status        VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE department (
    department_id   BIGSERIAL PRIMARY KEY,
    department_code VARCHAR(20)  NOT NULL UNIQUE,
    facility_id     BIGINT NOT NULL REFERENCES facility(facility_id),
    name            VARCHAR(200) NOT NULL,
    department_type VARCHAR(20)  NOT NULL, -- BEDDED / NON_BEDDED
    status          VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE unit_group (
    unit_group_id BIGSERIAL PRIMARY KEY,
    department_id BIGINT NOT NULL REFERENCES department(department_id),
    name          VARCHAR(200) NOT NULL,
    care_setting  VARCHAR(40)  NOT NULL, -- INPATIENT_WARD / CRITICAL_CARE / EMERGENCY / PERIOPERATIVE / AMBULATORY / DIAGNOSTIC / SUPPORT
    status        VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE nursing_unit (
    unit_id            BIGSERIAL PRIMARY KEY,
    unit_code          VARCHAR(20)  NOT NULL UNIQUE, -- W3A, ICU-MAIN, ED-RESUS, …
    department_id      BIGINT NOT NULL REFERENCES department(department_id),
    unit_group_id      BIGINT NOT NULL REFERENCES unit_group(unit_group_id),
    unit_name          VARCHAR(200) NOT NULL,
    unit_type          VARCHAR(20)  NOT NULL, -- WARD/SECURE_WARD/ICU/HDU/LDR/ED/UCC/OR/PACU/CLINIC/DIAGNOSTIC/PROCEDURE/THERAPY/SUPPORT
    care_setting       VARCHAR(40)  NOT NULL,
    capacity_class     VARCHAR(30)  NOT NULL, -- INPATIENT_LICENSED / ED_STRETCHER / PACU_BAY / OR_TABLE / PROCEDURE_ROOM / AMBULATORY_CHAIR / SUPPORT
    source_bed_count   INTEGER CHECK (source_bed_count IS NULL OR source_bed_count >= 0),
    resource_capacity  INTEGER      NOT NULL DEFAULT 0 CHECK (resource_capacity >= 0),
    licensed_capacity  INTEGER      NOT NULL DEFAULT 0 CHECK (licensed_capacity >= 0), -- INPATIENT_LICENSED only; else 0
    is_bedded          BOOLEAN      NOT NULL DEFAULT FALSE, -- patient-placeable (inpatient, ED stretcher, PACU)
    dq_flag            VARCHAR(40),
    effective_from     DATE,
    effective_to       DATE,
    status             VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    CHECK (licensed_capacity = 0 OR capacity_class = 'INPATIENT_LICENSED')
);

CREATE TABLE room (
    room_id           BIGSERIAL PRIMARY KEY,
    unit_id           BIGINT NOT NULL REFERENCES nursing_unit(unit_id),
    room_number       VARCHAR(20) NOT NULL,
    room_type         VARCHAR(20),          -- PRIVATE / SHARED / BAY
    isolation_capable BOOLEAN DEFAULT FALSE,
    UNIQUE (unit_id, room_number)
);

CREATE TABLE bed (
    bed_id        BIGSERIAL PRIMARY KEY,
    unit_id       BIGINT NOT NULL REFERENCES nursing_unit(unit_id),
    room_id       BIGINT REFERENCES room(room_id),
    bed_number    VARCHAR(20) NOT NULL,
    bed_class     VARCHAR(20) NOT NULL DEFAULT 'SHARED', -- PRIVATE/SHARED/ISOLATION
    care_features VARCHAR(100) DEFAULT '',                -- comma list TELEMETRY/VENTILATED/NEG_PRESSURE/BARIATRIC
    is_licensed   BOOLEAN NOT NULL DEFAULT TRUE,
    is_operative  BOOLEAN NOT NULL DEFAULT TRUE,
    bed_status    VARCHAR(20) NOT NULL DEFAULT 'READY',   -- READY/RESERVED/OCCUPIED/CLEANING/OUT_OF_SERVICE/BLOCKED
    UNIQUE (unit_id, bed_number)
);

CREATE TABLE bed_state_log (
    id         BIGSERIAL PRIMARY KEY,
    bed_id     BIGINT NOT NULL REFERENCES bed(bed_id),
    from_state VARCHAR(20),
    to_state   VARCHAR(20) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by BIGINT,                 -- user id (external)
    reason     VARCHAR(255),
    source     VARCHAR(20)             -- UI / API / SYSTEM
);
CREATE INDEX idx_bed_state_log_bed ON bed_state_log(bed_id, changed_at);

-- ---- Workforce / accountability domain (mirror from HR/HNWMS) ----
CREATE TABLE person (
    person_id  BIGSERIAL PRIMARY KEY,
    staff_code VARCHAR(30) NOT NULL UNIQUE,
    name       VARCHAR(200) NOT NULL,
    license_no VARCHAR(50),
    status     VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE org_node (
    org_node_id       BIGSERIAL PRIMARY KEY,
    parent_org_node_id BIGINT REFERENCES org_node(org_node_id),
    org_code          VARCHAR(30) NOT NULL UNIQUE,
    name              VARCHAR(200) NOT NULL,
    node_type         VARCHAR(30),     -- EXEC/NURSING_LINE/FUNCTION/LOCATION_HOME
    status            VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE workforce_position (
    position_id    BIGSERIAL PRIMARY KEY,
    position_code  VARCHAR(30) NOT NULL UNIQUE, -- DON/ADON/.../CHARGE_NURSE/STAFF_NURSE
    org_node_id    BIGINT REFERENCES org_node(org_node_id),
    title          VARCHAR(200) NOT NULL,
    position_level VARCHAR(5)   NOT NULL       -- L1..L7 (E1/E2 for exec)
);

CREATE TABLE assignment (
    assignment_id  BIGSERIAL PRIMARY KEY,
    person_id      BIGINT NOT NULL REFERENCES person(person_id),
    position_id    BIGINT NOT NULL REFERENCES workforce_position(position_id),
    scope_type     VARCHAR(20) NOT NULL, -- FACILITY / DEPARTMENT / UNIT
    scope_id       BIGINT NOT NULL,      -- references respective location table
    effective_from DATE NOT NULL,
    effective_to   DATE,
    status         VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

-- ---- Encounter / ADT domain (mirror/consume from EMR) ----
CREATE TABLE encounter (
    encounter_id    BIGSERIAL PRIMARY KEY,
    patient_id      BIGINT,             -- MPI external id
    encounter_number VARCHAR(30) NOT NULL UNIQUE,
    current_unit_id BIGINT REFERENCES nursing_unit(unit_id),
    admitted_at     TIMESTAMPTZ,
    discharged_at   TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' -- ADMITTED/TRANSFERRING/DISCHARGED
);

CREATE TABLE bed_occupancy (
    id              BIGSERIAL PRIMARY KEY,
    bed_id          BIGINT NOT NULL REFERENCES bed(bed_id),
    encounter_id    BIGINT NOT NULL REFERENCES encounter(encounter_id),
    occupied_from   TIMESTAMPTZ NOT NULL DEFAULT now(),
    occupied_until  TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'OCCUPIED' -- OCCUPIED/RELEASED
);
CREATE INDEX idx_bed_occupancy_bed ON bed_occupancy(bed_id, status);
CREATE INDEX idx_bed_occupancy_enc ON bed_occupancy(encounter_id);
