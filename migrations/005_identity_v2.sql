-- Migration 005: Identity v2 shadow schema (additive — does not alter v1 tables)
-- Apply:   sqlite3 org_directory.db < 005_identity_v2.sql
-- Rollback: see 005_identity_v2_rollback.sql
-- Source:  rbac-v2/part-2-identity/identity_schema.sql

PRAGMA foreign_keys = ON;

-- ─── Core identity tables ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS identity_account_v2 (
    user_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_uuid         TEXT NOT NULL UNIQUE,
    legacy_app_user_id   INTEGER UNIQUE REFERENCES app_user(user_id),
    account_type         TEXT NOT NULL DEFAULT 'HUMAN',
    email                TEXT,
    email_normalized     TEXT UNIQUE,
    email_verified_at    TEXT,
    auth_provider        TEXT NOT NULL,
    external_subject     TEXT,
    account_status       TEXT NOT NULL DEFAULT 'PENDING_VERIFICATION',
    mfa_required         INTEGER NOT NULL DEFAULT 0,
    auth_version         INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    CHECK (account_type IN ('HUMAN','SERVICE','RECOVERY_ADMIN')),
    CHECK (auth_provider IN ('SSO','LOCAL','LEGACY_LOCAL')),
    CHECK (account_status IN ('PENDING_VERIFICATION','ACTIVE','LOCKED','DISABLED','ARCHIVED')),
    CHECK (mfa_required IN (0,1)),
    CHECK (auth_version >= 1),
    CHECK (
      (email IS NULL AND email_normalized IS NULL)
      OR (email IS NOT NULL AND email_normalized = lower(trim(email)))
    ),
    CHECK (auth_provider <> 'SSO' OR length(trim(COALESCE(external_subject, ''))) > 0),
    CHECK (
      account_type <> 'HUMAN' OR account_status <> 'ACTIVE'
      OR (email_normalized IS NOT NULL AND email_verified_at IS NOT NULL)
    ),
    CHECK (account_type <> 'SERVICE' OR email_normalized IS NULL),
    UNIQUE (auth_provider, external_subject)
);

CREATE TABLE IF NOT EXISTS staff_member_v2 (
    staff_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_uuid           TEXT NOT NULL UNIQUE,
    legacy_persona_id    INTEGER UNIQUE REFERENCES persona(persona_id),
    employee_number      TEXT UNIQUE,
    display_name         TEXT NOT NULL,
    source_system        TEXT NOT NULL,
    source_updated_at    TEXT NOT NULL,
    record_status        TEXT NOT NULL,
    is_demo              INTEGER NOT NULL DEFAULT 0,
    CHECK (record_status IN ('MIGRATION_PENDING','ACTIVE','SUSPENDED','ENDED','ARCHIVED')),
    CHECK (is_demo IN (0,1)),
    CHECK (is_demo = 1 OR employee_number IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS identity_staff_link_v2 (
    user_id              INTEGER PRIMARY KEY REFERENCES identity_account_v2(user_id),
    staff_id             INTEGER NOT NULL UNIQUE REFERENCES staff_member_v2(staff_id),
    linked_at            TEXT NOT NULL,
    linked_by_user_id    INTEGER REFERENCES identity_account_v2(user_id),
    verification_method  TEXT NOT NULL,
    CHECK (verification_method IN ('AUTHORITATIVE_KEY','MANUAL_DUAL_REVIEW','LEGACY_DEMO'))
);

CREATE TABLE IF NOT EXISTS local_auth_credential_v2 (
    user_id              INTEGER PRIMARY KEY REFERENCES identity_account_v2(user_id),
    encoded_hash         TEXT NOT NULL,
    algorithm            TEXT NOT NULL,
    parameter_version    TEXT NOT NULL,
    changed_at           TEXT NOT NULL,
    must_change          INTEGER NOT NULL DEFAULT 0,
    CHECK (must_change IN (0,1))
);

-- ─── Employment & credentials ───────────────────────────────────

CREATE TABLE IF NOT EXISTS employment_assignment_v2 (
    assignment_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id             INTEGER NOT NULL REFERENCES staff_member_v2(staff_id),
    position_id          INTEGER REFERENCES workforce_position(position_id),
    department_id        INTEGER REFERENCES department(department_id),
    unit_id              INTEGER REFERENCES nursing_unit(unit_id),
    fte                  NUMERIC,
    assignment_type      TEXT NOT NULL DEFAULT 'PRIMARY',
    employment_status    TEXT NOT NULL,
    effective_from       TEXT NOT NULL,
    effective_to         TEXT,
    source_reference     TEXT,
    recorded_at          TEXT NOT NULL,
    CHECK (assignment_type IN ('PRIMARY','SECONDARY','TEMPORARY')),
    CHECK (employment_status IN ('PENDING','ACTIVE','ON_LEAVE','SUSPENDED','ENDED')),
    CHECK (fte IS NULL OR (fte > 0 AND fte <= 1.5)),
    CHECK (department_id IS NOT NULL OR unit_id IS NOT NULL),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS professional_credential_v2 (
    credential_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id             INTEGER NOT NULL REFERENCES staff_member_v2(staff_id),
    credential_type      TEXT NOT NULL,
    credential_number    TEXT NOT NULL,
    issuing_authority    TEXT NOT NULL,
    issue_date           TEXT,
    expiry_date          TEXT,
    verification_status  TEXT NOT NULL DEFAULT 'PENDING',
    submitted_by_user_id INTEGER REFERENCES identity_account_v2(user_id),
    submitted_at         TEXT NOT NULL,
    verified_by_user_id  INTEGER REFERENCES identity_account_v2(user_id),
    verified_at          TEXT,
    evidence_document_id INTEGER REFERENCES staff_document(document_id),
    source_checked_at    TEXT,
    CHECK (verification_status IN ('PENDING','VERIFIED','EXPIRED','SUSPENDED','REVOKED','REJECTED')),
    CHECK (expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date),
    CHECK (
      verification_status <> 'VERIFIED'
      OR (verified_by_user_id IS NOT NULL AND verified_at IS NOT NULL AND source_checked_at IS NOT NULL)
    ),
    UNIQUE (issuing_authority, credential_number)
);

-- ─── Sessions ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS identity_session_v2 (
    session_id           TEXT PRIMARY KEY,
    token_hash           TEXT NOT NULL UNIQUE,
    user_id              INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    auth_version         INTEGER NOT NULL,
    assurance_level      TEXT NOT NULL,
    issued_at            TEXT NOT NULL,
    last_seen_at         TEXT NOT NULL,
    expires_at           TEXT NOT NULL,
    revoked_at           TEXT,
    revocation_reason    TEXT,
    CHECK (assurance_level IN ('AAL1','AAL2','STEP_UP')),
    CHECK (expires_at > issued_at),
    CHECK (revoked_at IS NULL OR revocation_reason IS NOT NULL)
);

-- ─── Audit / lifecycle (append-only) ────────────────────────────

CREATE TABLE IF NOT EXISTS authentication_event_v2 (
    event_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uuid           TEXT NOT NULL UNIQUE,
    user_id              INTEGER REFERENCES identity_account_v2(user_id),
    occurred_at          TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    outcome              TEXT NOT NULL,
    reason_code          TEXT,
    auth_provider        TEXT,
    assurance_level      TEXT,
    correlation_id       TEXT NOT NULL,
    client_context_json  TEXT,
    CHECK (outcome IN ('SUCCESS','FAILURE','DENIED','INFO'))
);

CREATE TABLE IF NOT EXISTS identity_lifecycle_event_v2 (
    event_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uuid           TEXT NOT NULL UNIQUE,
    user_id              INTEGER REFERENCES identity_account_v2(user_id),
    staff_id             INTEGER REFERENCES staff_member_v2(staff_id),
    occurred_at          TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    actor_user_id        INTEGER REFERENCES identity_account_v2(user_id),
    source_system        TEXT NOT NULL,
    reason_code          TEXT,
    before_json          TEXT,
    after_json           TEXT,
    correlation_id       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_reconciliation_issue_v2 (
    issue_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_uuid           TEXT NOT NULL UNIQUE,
    issue_type           TEXT NOT NULL,
    severity             TEXT NOT NULL,
    source_reference     TEXT,
    details_json         TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'OPEN',
    opened_at            TEXT NOT NULL,
    resolved_at          TEXT,
    resolved_by_user_id  INTEGER REFERENCES identity_account_v2(user_id),
    resolution_notes     TEXT,
    CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CHECK (status IN ('OPEN','IN_REVIEW','RESOLVED','ACCEPTED_RISK')),
    CHECK (status NOT IN ('RESOLVED','ACCEPTED_RISK') OR (resolved_at IS NOT NULL AND resolved_by_user_id IS NOT NULL AND resolution_notes IS NOT NULL))
);

-- ─── Triggers: business rules ───────────────────────────────────

CREATE TRIGGER IF NOT EXISTS local_credential_provider_insert_v2
BEFORE INSERT ON local_auth_credential_v2
WHEN NOT EXISTS (
  SELECT 1 FROM identity_account_v2
  WHERE user_id = NEW.user_id AND auth_provider IN ('LOCAL','LEGACY_LOCAL')
)
BEGIN
  SELECT RAISE(ABORT, 'local credential requires a local authentication provider');
END;

CREATE TRIGGER IF NOT EXISTS local_credential_provider_update_v2
BEFORE UPDATE OF user_id ON local_auth_credential_v2
WHEN NOT EXISTS (
  SELECT 1 FROM identity_account_v2
  WHERE user_id = NEW.user_id AND auth_provider IN ('LOCAL','LEGACY_LOCAL')
)
BEGIN
  SELECT RAISE(ABORT, 'local credential requires a local authentication provider');
END;

CREATE TRIGGER IF NOT EXISTS employment_unit_department_insert_v2
BEFORE INSERT ON employment_assignment_v2
WHEN NEW.unit_id IS NOT NULL AND NEW.department_id IS NOT NULL
 AND NOT EXISTS (
   SELECT 1 FROM nursing_unit
   WHERE unit_id = NEW.unit_id AND department_id = NEW.department_id
 )
BEGIN
  SELECT RAISE(ABORT, 'unit does not belong to department');
END;

CREATE TRIGGER IF NOT EXISTS employment_unit_department_update_v2
BEFORE UPDATE OF unit_id, department_id ON employment_assignment_v2
WHEN NEW.unit_id IS NOT NULL AND NEW.department_id IS NOT NULL
 AND NOT EXISTS (
   SELECT 1 FROM nursing_unit
   WHERE unit_id = NEW.unit_id AND department_id = NEW.department_id
 )
BEGIN
  SELECT RAISE(ABORT, 'unit does not belong to department');
END;

CREATE TRIGGER IF NOT EXISTS employment_primary_overlap_insert_v2
BEFORE INSERT ON employment_assignment_v2
WHEN NEW.assignment_type = 'PRIMARY'
 AND NEW.employment_status IN ('PENDING','ACTIVE','ON_LEAVE','SUSPENDED')
 AND EXISTS (
   SELECT 1 FROM employment_assignment_v2 old
   WHERE old.staff_id = NEW.staff_id
     AND old.assignment_type = 'PRIMARY'
     AND old.employment_status IN ('PENDING','ACTIVE','ON_LEAVE','SUSPENDED')
     AND COALESCE(old.effective_to, '9999-12-31T23:59:59Z') > NEW.effective_from
     AND COALESCE(NEW.effective_to, '9999-12-31T23:59:59Z') > old.effective_from
 )
BEGIN
  SELECT RAISE(ABORT, 'overlapping primary employment assignment');
END;

CREATE TRIGGER IF NOT EXISTS employment_primary_overlap_update_v2
BEFORE UPDATE OF staff_id, assignment_type, employment_status, effective_from, effective_to
ON employment_assignment_v2
WHEN NEW.assignment_type = 'PRIMARY'
 AND NEW.employment_status IN ('PENDING','ACTIVE','ON_LEAVE','SUSPENDED')
 AND EXISTS (
   SELECT 1 FROM employment_assignment_v2 old
   WHERE old.assignment_id <> NEW.assignment_id
     AND old.staff_id = NEW.staff_id
     AND old.assignment_type = 'PRIMARY'
     AND old.employment_status IN ('PENDING','ACTIVE','ON_LEAVE','SUSPENDED')
     AND COALESCE(old.effective_to, '9999-12-31T23:59:59Z') > NEW.effective_from
     AND COALESCE(NEW.effective_to, '9999-12-31T23:59:59Z') > old.effective_from
 )
BEGIN
  SELECT RAISE(ABORT, 'overlapping primary employment assignment');
END;

CREATE TRIGGER IF NOT EXISTS credential_independent_verifier_insert_v2
BEFORE INSERT ON professional_credential_v2
WHEN NEW.verification_status = 'VERIFIED'
 AND NEW.submitted_by_user_id IS NOT NULL
 AND NEW.submitted_by_user_id = NEW.verified_by_user_id
BEGIN
  SELECT RAISE(ABORT, 'credential submitter cannot verify own credential');
END;

CREATE TRIGGER IF NOT EXISTS credential_independent_verifier_update_v2
BEFORE UPDATE OF verification_status, verified_by_user_id ON professional_credential_v2
WHEN NEW.verification_status = 'VERIFIED'
 AND NEW.submitted_by_user_id IS NOT NULL
 AND NEW.submitted_by_user_id = NEW.verified_by_user_id
BEGIN
  SELECT RAISE(ABORT, 'credential submitter cannot verify own credential');
END;

-- Session triggers (account must be active + version match)
CREATE TRIGGER IF NOT EXISTS identity_session_account_insert_v2
BEFORE INSERT ON identity_session_v2
WHEN NOT EXISTS (
  SELECT 1 FROM identity_account_v2
  WHERE user_id = NEW.user_id
    AND account_status = 'ACTIVE'
    AND auth_version = NEW.auth_version
)
BEGIN
  SELECT RAISE(ABORT, 'session requires active account and current auth version');
END;

CREATE TRIGGER IF NOT EXISTS identity_session_account_update_v2
BEFORE UPDATE OF user_id, auth_version ON identity_session_v2
WHEN NOT EXISTS (
  SELECT 1 FROM identity_account_v2
  WHERE user_id = NEW.user_id
    AND account_status = 'ACTIVE'
    AND auth_version = NEW.auth_version
)
BEGIN
  SELECT RAISE(ABORT, 'session requires active account and current auth version');
END;

-- Append-only triggers
CREATE TRIGGER IF NOT EXISTS authentication_event_no_update_v2
BEFORE UPDATE ON authentication_event_v2
BEGIN SELECT RAISE(ABORT, 'authentication events are append-only'); END;

CREATE TRIGGER IF NOT EXISTS authentication_event_no_delete_v2
BEFORE DELETE ON authentication_event_v2
BEGIN SELECT RAISE(ABORT, 'authentication events are append-only'); END;

CREATE TRIGGER IF NOT EXISTS identity_lifecycle_event_no_update_v2
BEFORE UPDATE ON identity_lifecycle_event_v2
BEGIN SELECT RAISE(ABORT, 'identity lifecycle events are append-only'); END;

CREATE TRIGGER IF NOT EXISTS identity_lifecycle_event_no_delete_v2
BEFORE DELETE ON identity_lifecycle_event_v2
BEGIN SELECT RAISE(ABORT, 'identity lifecycle events are append-only'); END;

-- ─── Indexes ────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_identity_account_status_v2
ON identity_account_v2 (account_status, account_type);

CREATE INDEX IF NOT EXISTS idx_employment_staff_effective_v2
ON employment_assignment_v2 (staff_id, effective_from, effective_to, employment_status);

CREATE INDEX IF NOT EXISTS idx_credential_staff_expiry_v2
ON professional_credential_v2 (staff_id, verification_status, expiry_date);

CREATE INDEX IF NOT EXISTS idx_session_user_expiry_v2
ON identity_session_v2 (user_id, expires_at, revoked_at);

CREATE INDEX IF NOT EXISTS idx_auth_event_user_time_v2
ON authentication_event_v2 (user_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_lifecycle_staff_time_v2
ON identity_lifecycle_event_v2 (staff_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_reconciliation_open_v2
ON identity_reconciliation_issue_v2 (status, severity, opened_at);

-- ─── Version stamp ──────────────────────────────────────────────

INSERT INTO schema_version (version, description) VALUES
    (5, 'Identity v2 shadow schema — accounts, staff, sessions, lifecycle audit');
