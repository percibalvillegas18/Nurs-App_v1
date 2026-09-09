-- Wave P1 Org Directory — SQLite
PRAGMA foreign_keys = ON;

CREATE TABLE facility (
    facility_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_code TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    region        TEXT,
    city          TEXT,
    mrn_prefix    TEXT,
    licensor      TEXT,
    status        TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE department (
    department_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    department_code TEXT NOT NULL UNIQUE,
    facility_id     INTEGER NOT NULL REFERENCES facility(facility_id),
    name            TEXT NOT NULL,
    department_type TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE unit_group (
    unit_group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL REFERENCES department(department_id),
    name          TEXT NOT NULL,
    care_setting  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'ACTIVE',
    UNIQUE (department_id, name)
);

CREATE TABLE nursing_unit (
    unit_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_code          TEXT NOT NULL UNIQUE,
    department_id      INTEGER NOT NULL REFERENCES department(department_id),
    unit_group_id      INTEGER NOT NULL REFERENCES unit_group(unit_group_id),
    unit_name          TEXT NOT NULL,
    unit_type          TEXT NOT NULL,
    care_setting       TEXT NOT NULL,
    capacity_class     TEXT NOT NULL,
    source_bed_count   INTEGER,
    resource_capacity  INTEGER NOT NULL DEFAULT 0,
    licensed_capacity  INTEGER NOT NULL DEFAULT 0,
    is_bedded          INTEGER NOT NULL DEFAULT 0,
    dq_flag            TEXT,
    effective_from     TEXT,
    effective_to       TEXT,
    status             TEXT NOT NULL DEFAULT 'ACTIVE',
    CHECK (licensed_capacity = 0 OR capacity_class = 'INPATIENT_LICENSED')
);

CREATE TABLE org_node (
    org_node_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_org_node_id INTEGER REFERENCES org_node(org_node_id),
    org_code           TEXT NOT NULL UNIQUE,
    name               TEXT NOT NULL,
    node_type          TEXT,
    status             TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE workforce_position (
    position_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    position_code  TEXT NOT NULL UNIQUE,
    org_node_id    INTEGER REFERENCES org_node(org_node_id),
    title          TEXT NOT NULL,
    position_level TEXT NOT NULL
);

-- Proposed coverage (DQ-14). No person rows — catalogue only until HR loads Staff Master.
CREATE TABLE coverage_template (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    clinical_line   TEXT NOT NULL,
    position_code   TEXT NOT NULL,
    scope_type      TEXT NOT NULL,
    unit_code       TEXT REFERENCES nursing_unit(unit_code),
    department_code TEXT,
    status          TEXT NOT NULL DEFAULT 'PROPOSED',
    notes           TEXT
);

CREATE TABLE role (
    role_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    role_code TEXT NOT NULL UNIQUE,
    title     TEXT NOT NULL,
    level     TEXT,
    data_scope TEXT NOT NULL
);

CREATE TABLE permission (
    permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    perm_code     TEXT NOT NULL UNIQUE,
    module        TEXT NOT NULL,
    description   TEXT
);

CREATE TABLE role_permission (
    role_id       INTEGER NOT NULL REFERENCES role(role_id),
    permission_id INTEGER NOT NULL REFERENCES permission(permission_id),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE vocabulary (
    vocab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain   TEXT NOT NULL,
    code     TEXT NOT NULL,
    label    TEXT NOT NULL,
    UNIQUE (domain, code)
);

CREATE TABLE desk_audit (
    unit_code            TEXT PRIMARY KEY REFERENCES nursing_unit(unit_code),
    walk_status          TEXT NOT NULL,
    physical_exists      TEXT NOT NULL,
    separate_footprint   TEXT NOT NULL,
    physical_beds        TEXT,
    licensed_from_register TEXT,
    operational_today    TEXT,
    clinical_or_support  TEXT,
    second_site          TEXT,
    desk_recommendation  TEXT,
    notes                TEXT
);

CREATE TABLE registry_event (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor      TEXT,
    detail     TEXT
);
