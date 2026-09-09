-- User management (login, profile, recommended documents).
-- Linked to RBAC persona slots. Not SSO / MFA / Staff Master.

CREATE TABLE IF NOT EXISTS app_user (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id    INTEGER NOT NULL UNIQUE REFERENCES persona(persona_id),
    username      TEXT NOT NULL UNIQUE,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'ACTIVE',
    must_change   INTEGER NOT NULL DEFAULT 0,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS app_session (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES app_user(user_id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staff_profile (
    persona_id        INTEGER PRIMARY KEY REFERENCES persona(persona_id),
    mobile            TEXT,
    national_id       TEXT,
    nationality       TEXT,
    gender            TEXT,
    date_of_birth     TEXT,
    license_no        TEXT,
    license_authority TEXT,
    license_expiry    TEXT,
    scfhs_no          TEXT,
    employment_type   TEXT,
    fte               TEXT,
    hire_date         TEXT,
    emergency_name    TEXT,
    emergency_phone   TEXT,
    updated_at        TEXT
);

CREATE TABLE IF NOT EXISTS doc_type (
    doc_code   TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    category   TEXT NOT NULL,  -- MANDATORY / REQUIRED / ADDITIONAL
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS staff_document (
    document_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id    INTEGER NOT NULL REFERENCES persona(persona_id),
    doc_code      TEXT NOT NULL REFERENCES doc_type(doc_code),
    original_name TEXT NOT NULL,
    stored_name   TEXT NOT NULL,
    mime          TEXT,
    size_bytes    INTEGER NOT NULL,
    uploaded_at   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'SUBMITTED'
);
