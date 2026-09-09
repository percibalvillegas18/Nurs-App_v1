-- Portable RBAC (SQLite / PostgreSQL-friendly types)
-- Org Directory already has role / permission / role_permission.
-- These extra tables bind a role to a location scope.

-- persona_code is a STABLE SLOT (demo.slot.charge.w3a).
-- display_name is the current person — swap to a real employee later.
-- Login lives in Org Directory UM (not SSO/MFA). This schema is grants only.

CREATE TABLE IF NOT EXISTS persona (
    persona_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    job_title    TEXT,
    category     TEXT,
    is_demo      INTEGER NOT NULL DEFAULT 1,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS role_grant (
    grant_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id   INTEGER NOT NULL REFERENCES persona(persona_id),
    role_id      INTEGER NOT NULL REFERENCES role(role_id),
    scope_type   TEXT NOT NULL,   -- FACILITY / DEPARTMENT / UNIT
    scope_code   TEXT NOT NULL,   -- AIGH / EMRG / W3A
    effective_from TEXT NOT NULL,
    effective_to   TEXT,
    status       TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS sod_rule (
    sod_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    perm_a   TEXT NOT NULL,
    perm_b   TEXT NOT NULL,
    message  TEXT NOT NULL,
    waive_roles TEXT NOT NULL DEFAULT ''  -- comma list, e.g. SYS_ADMIN
);

CREATE TABLE IF NOT EXISTS rbac_decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decided_at TEXT NOT NULL,
    subject TEXT NOT NULL,
    permission TEXT NOT NULL,
    resource_type TEXT,
    resource_code TEXT,
    allow INTEGER NOT NULL,
    reason TEXT NOT NULL
);
