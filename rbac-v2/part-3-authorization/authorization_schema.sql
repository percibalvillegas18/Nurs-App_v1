-- HNWMS RBAC v2 Part 3: additive authorization shadow schema for SQLite.
-- Not loaded by the current seed or runtime API.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS authorization_policy_v2 (
    policy_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    version_code         TEXT NOT NULL UNIQUE,
    status               TEXT NOT NULL DEFAULT 'DRAFT',
    effective_from       TEXT,
    effective_to         TEXT,
    approved_by_user_id  INTEGER REFERENCES identity_account_v2(user_id),
    approved_at          TEXT,
    published_at         TEXT,
    notes                TEXT,
    CHECK (status IN ('DRAFT','ACTIVE','RETIRED','REJECTED')),
    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from),
    CHECK (status <> 'ACTIVE' OR (
      approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL
      AND published_at IS NOT NULL AND effective_from IS NOT NULL
    ))
);

CREATE TRIGGER IF NOT EXISTS authorization_policy_published_core_immutable_v2
BEFORE UPDATE OF version_code, effective_from, approved_by_user_id, approved_at, published_at
ON authorization_policy_v2
WHEN OLD.status IN ('ACTIVE','RETIRED')
BEGIN SELECT RAISE(ABORT, 'published policy core is immutable'); END;

CREATE TRIGGER IF NOT EXISTS authorization_policy_active_transition_v2
BEFORE UPDATE OF status ON authorization_policy_v2
WHEN OLD.status='ACTIVE' AND NEW.status<>'RETIRED'
BEGIN SELECT RAISE(ABORT, 'active policy may only transition to retired'); END;

CREATE TRIGGER IF NOT EXISTS authorization_policy_retired_immutable_v2
BEFORE UPDATE ON authorization_policy_v2
WHEN OLD.status='RETIRED'
BEGIN SELECT RAISE(ABORT, 'retired policy is immutable'); END;

CREATE TABLE IF NOT EXISTS authorization_role_v2 (
    role_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id            INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    role_code            TEXT NOT NULL,
    title                TEXT NOT NULL,
    risk_class           TEXT NOT NULL DEFAULT 'STANDARD',
    status               TEXT NOT NULL DEFAULT 'ACTIVE',
    CHECK (risk_class IN ('STANDARD','ELEVATED','PRIVILEGED')),
    CHECK (status IN ('ACTIVE','INACTIVE')),
    UNIQUE (policy_id, role_code),
    UNIQUE (policy_id, role_id)
);

CREATE TABLE IF NOT EXISTS authorization_permission_v2 (
    permission_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id            INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    perm_code            TEXT NOT NULL,
    module               TEXT NOT NULL,
    description          TEXT NOT NULL,
    risk_class           TEXT NOT NULL DEFAULT 'STANDARD',
    requires_mfa         INTEGER NOT NULL DEFAULT 0,
    requires_part4       INTEGER NOT NULL DEFAULT 0,
    delegable            INTEGER NOT NULL DEFAULT 0,
    status               TEXT NOT NULL DEFAULT 'ACTIVE',
    CHECK (risk_class IN ('STANDARD','ELEVATED','HIGH','CRITICAL')),
    CHECK (requires_mfa IN (0,1)),
    CHECK (requires_part4 IN (0,1)),
    CHECK (delegable IN (0,1)),
    CHECK (status IN ('ACTIVE','INACTIVE')),
    UNIQUE (policy_id, perm_code),
    UNIQUE (policy_id, permission_id)
);

CREATE TABLE IF NOT EXISTS authorization_role_permission_v2 (
    policy_id            INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    role_id              INTEGER NOT NULL,
    permission_id        INTEGER NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (policy_id, role_id)
      REFERENCES authorization_role_v2(policy_id, role_id),
    FOREIGN KEY (policy_id, permission_id)
      REFERENCES authorization_permission_v2(policy_id, permission_id)
);

CREATE TRIGGER IF NOT EXISTS authorization_role_draft_insert_v2
BEFORE INSERT ON authorization_role_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=NEW.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'role catalogue changes require draft policy'); END;
CREATE TRIGGER IF NOT EXISTS authorization_role_draft_update_v2
BEFORE UPDATE ON authorization_role_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published role catalogue is immutable'); END;
CREATE TRIGGER IF NOT EXISTS authorization_role_draft_delete_v2
BEFORE DELETE ON authorization_role_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published role catalogue is immutable'); END;

CREATE TRIGGER IF NOT EXISTS authorization_permission_draft_insert_v2
BEFORE INSERT ON authorization_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=NEW.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'permission catalogue changes require draft policy'); END;
CREATE TRIGGER IF NOT EXISTS authorization_permission_draft_update_v2
BEFORE UPDATE ON authorization_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published permission catalogue is immutable'); END;
CREATE TRIGGER IF NOT EXISTS authorization_permission_draft_delete_v2
BEFORE DELETE ON authorization_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published permission catalogue is immutable'); END;

CREATE TRIGGER IF NOT EXISTS authorization_role_permission_draft_insert_v2
BEFORE INSERT ON authorization_role_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=NEW.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'role-permission changes require draft policy'); END;
CREATE TRIGGER IF NOT EXISTS authorization_role_permission_draft_update_v2
BEFORE UPDATE ON authorization_role_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published role-permission catalogue is immutable'); END;
CREATE TRIGGER IF NOT EXISTS authorization_role_permission_draft_delete_v2
BEFORE DELETE ON authorization_role_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published role-permission catalogue is immutable'); END;

CREATE TABLE IF NOT EXISTS authorization_scope_v2 (
    scope_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_uuid           TEXT NOT NULL UNIQUE,
    scope_type           TEXT NOT NULL,
    facility_id          INTEGER REFERENCES facility(facility_id),
    department_id        INTEGER REFERENCES department(department_id),
    unit_id              INTEGER REFERENCES nursing_unit(unit_id),
    status               TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at           TEXT NOT NULL,
    CHECK (scope_type IN ('FACILITY','DEPARTMENT','UNIT')),
    CHECK (status IN ('ACTIVE','INACTIVE')),
    CHECK (
      (scope_type='FACILITY' AND facility_id IS NOT NULL AND department_id IS NULL AND unit_id IS NULL) OR
      (scope_type='DEPARTMENT' AND facility_id IS NULL AND department_id IS NOT NULL AND unit_id IS NULL) OR
      (scope_type='UNIT' AND facility_id IS NULL AND department_id IS NULL AND unit_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_authorization_scope_facility_v2
ON authorization_scope_v2(facility_id) WHERE scope_type='FACILITY';
CREATE UNIQUE INDEX IF NOT EXISTS uq_authorization_scope_department_v2
ON authorization_scope_v2(department_id) WHERE scope_type='DEPARTMENT';
CREATE UNIQUE INDEX IF NOT EXISTS uq_authorization_scope_unit_v2
ON authorization_scope_v2(unit_id) WHERE scope_type='UNIT';

CREATE TRIGGER IF NOT EXISTS authorization_scope_active_insert_v2
BEFORE INSERT ON authorization_scope_v2
WHEN
  (NEW.scope_type='FACILITY' AND NOT EXISTS (
     SELECT 1 FROM facility WHERE facility_id=NEW.facility_id AND status='ACTIVE'))
  OR (NEW.scope_type='DEPARTMENT' AND NOT EXISTS (
     SELECT 1 FROM department WHERE department_id=NEW.department_id AND status='ACTIVE'))
  OR (NEW.scope_type='UNIT' AND NOT EXISTS (
     SELECT 1 FROM nursing_unit u JOIN department d ON d.department_id=u.department_id
     JOIN facility f ON f.facility_id=d.facility_id
     WHERE u.unit_id=NEW.unit_id AND u.status='ACTIVE' AND d.status='ACTIVE' AND f.status='ACTIVE'))
BEGIN
  SELECT RAISE(ABORT, 'authorization scope requires active authoritative resource');
END;

CREATE TRIGGER IF NOT EXISTS authorization_scope_active_update_v2
BEFORE UPDATE OF scope_type, facility_id, department_id, unit_id, status ON authorization_scope_v2
WHEN NEW.status='ACTIVE' AND (
  (NEW.scope_type='FACILITY' AND NOT EXISTS (
     SELECT 1 FROM facility WHERE facility_id=NEW.facility_id AND status='ACTIVE'))
  OR (NEW.scope_type='DEPARTMENT' AND NOT EXISTS (
     SELECT 1 FROM department WHERE department_id=NEW.department_id AND status='ACTIVE'))
  OR (NEW.scope_type='UNIT' AND NOT EXISTS (
     SELECT 1 FROM nursing_unit u JOIN department d ON d.department_id=u.department_id
     JOIN facility f ON f.facility_id=d.facility_id
     WHERE u.unit_id=NEW.unit_id AND u.status='ACTIVE' AND d.status='ACTIVE' AND f.status='ACTIVE'))
)
BEGIN
  SELECT RAISE(ABORT, 'authorization scope requires active authoritative resource');
END;

CREATE TABLE IF NOT EXISTS access_grant_request_v2 (
    request_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    request_uuid         TEXT NOT NULL UNIQUE,
    user_id              INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    role_id              INTEGER NOT NULL REFERENCES authorization_role_v2(role_id),
    scope_id             INTEGER NOT NULL REFERENCES authorization_scope_v2(scope_id),
    requested_by_user_id INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    requested_at         TEXT NOT NULL,
    requested_from       TEXT NOT NULL,
    requested_to         TEXT,
    reason_code          TEXT NOT NULL,
    justification        TEXT NOT NULL,
    requires_dual_control INTEGER NOT NULL DEFAULT 0,
    approved_by_user_id  INTEGER REFERENCES identity_account_v2(user_id),
    decided_at           TEXT,
    decision_reason      TEXT,
    status               TEXT NOT NULL DEFAULT 'REQUESTED',
    CHECK (requires_dual_control IN (0,1)),
    CHECK (status IN ('REQUESTED','APPROVED','REJECTED','CANCELLED')),
    CHECK (requested_to IS NULL OR requested_to > requested_from),
    CHECK (approved_by_user_id IS NULL OR approved_by_user_id <> requested_by_user_id),
    CHECK (requires_dual_control=0 OR approved_by_user_id IS NULL OR approved_by_user_id <> user_id),
    CHECK (status NOT IN ('APPROVED','REJECTED') OR (
      approved_by_user_id IS NOT NULL AND decided_at IS NOT NULL AND decision_reason IS NOT NULL
    ))
);

CREATE TRIGGER IF NOT EXISTS access_grant_request_decided_core_immutable_v2
BEFORE UPDATE OF user_id, role_id, scope_id, requested_by_user_id, requested_at,
  requested_from, requested_to, reason_code, justification, requires_dual_control
ON access_grant_request_v2
WHEN OLD.status <> 'REQUESTED'
BEGIN SELECT RAISE(ABORT, 'decided grant request core is immutable'); END;

CREATE TRIGGER IF NOT EXISTS access_grant_request_decision_immutable_v2
BEFORE UPDATE OF approved_by_user_id, decided_at, decision_reason
ON access_grant_request_v2
WHEN OLD.status <> 'REQUESTED' OR NEW.status NOT IN ('APPROVED','REJECTED')
BEGIN SELECT RAISE(ABORT, 'grant request decision is immutable'); END;

CREATE TABLE IF NOT EXISTS access_grant_v2 (
    grant_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    grant_uuid           TEXT NOT NULL UNIQUE,
    policy_id            INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    request_id           INTEGER NOT NULL UNIQUE REFERENCES access_grant_request_v2(request_id),
    user_id              INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    role_id              INTEGER NOT NULL,
    scope_id             INTEGER NOT NULL REFERENCES authorization_scope_v2(scope_id),
    requested_by_user_id INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    approved_by_user_id  INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    activated_by_user_id INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    effective_from       TEXT NOT NULL,
    effective_to         TEXT,
    reason_code          TEXT NOT NULL,
    justification        TEXT NOT NULL,
    requires_dual_control INTEGER NOT NULL DEFAULT 0,
    status               TEXT NOT NULL DEFAULT 'ACTIVE',
    activated_at         TEXT NOT NULL,
    revoked_at           TEXT,
    revoked_by_user_id   INTEGER REFERENCES identity_account_v2(user_id),
    revocation_reason    TEXT,
    CHECK (requires_dual_control IN (0,1)),
    CHECK (status IN ('ACTIVE','SUSPENDED','REVOKED','EXPIRED')),
    CHECK (effective_to IS NULL OR effective_to > effective_from),
    CHECK (requested_by_user_id <> approved_by_user_id),
    CHECK (requires_dual_control=0 OR activated_by_user_id <> approved_by_user_id),
    CHECK (status <> 'REVOKED' OR (
      revoked_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revocation_reason IS NOT NULL
    )),
    FOREIGN KEY (policy_id, role_id)
      REFERENCES authorization_role_v2(policy_id, role_id)
);

CREATE TRIGGER IF NOT EXISTS access_grant_core_immutable_v2
BEFORE UPDATE OF policy_id, request_id, user_id, role_id, scope_id,
  requested_by_user_id, approved_by_user_id, activated_by_user_id,
  effective_from, effective_to, requires_dual_control
ON access_grant_v2
BEGIN SELECT RAISE(ABORT, 'active grant core fields are immutable'); END;

CREATE TRIGGER IF NOT EXISTS access_grant_request_match_insert_v2
BEFORE INSERT ON access_grant_v2
WHEN NOT EXISTS (
  SELECT 1 FROM access_grant_request_v2 q
  JOIN authorization_role_v2 r ON r.role_id=q.role_id
  WHERE q.request_id=NEW.request_id AND q.status='APPROVED'
    AND q.user_id=NEW.user_id AND q.role_id=NEW.role_id AND q.scope_id=NEW.scope_id
    AND q.requested_by_user_id=NEW.requested_by_user_id
    AND q.approved_by_user_id=NEW.approved_by_user_id
    AND q.requested_from=NEW.effective_from
    AND COALESCE(q.requested_to,'')=COALESCE(NEW.effective_to,'')
    AND q.requires_dual_control=NEW.requires_dual_control
    AND r.policy_id=NEW.policy_id
)
BEGIN
  SELECT RAISE(ABORT, 'active grant must match an approved grant request');
END;

CREATE TABLE IF NOT EXISTS sod_rule_v2 (
    sod_rule_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id            INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    rule_code            TEXT NOT NULL,
    permission_a_id      INTEGER NOT NULL,
    permission_b_id      INTEGER NOT NULL,
    overlap_mode         TEXT NOT NULL DEFAULT 'SAME_SCOPE_OR_CONTAINED',
    enforcement          TEXT NOT NULL DEFAULT 'BLOCK',
    accountable_owner    TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'ACTIVE',
    CHECK (permission_a_id < permission_b_id),
    CHECK (overlap_mode IN ('SAME_SCOPE_OR_CONTAINED','ANY_SCOPE')),
    CHECK (enforcement IN ('BLOCK','ALERT')),
    CHECK (status IN ('ACTIVE','INACTIVE')),
    UNIQUE (policy_id, rule_code),
    UNIQUE (policy_id, permission_a_id, permission_b_id),
    FOREIGN KEY (policy_id, permission_a_id)
      REFERENCES authorization_permission_v2(policy_id, permission_id),
    FOREIGN KEY (policy_id, permission_b_id)
      REFERENCES authorization_permission_v2(policy_id, permission_id)
);

CREATE TRIGGER IF NOT EXISTS sod_rule_draft_insert_v2
BEFORE INSERT ON sod_rule_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=NEW.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'SoD catalogue changes require draft policy'); END;
CREATE TRIGGER IF NOT EXISTS sod_rule_draft_update_v2
BEFORE UPDATE ON sod_rule_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published SoD catalogue is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sod_rule_draft_delete_v2
BEFORE DELETE ON sod_rule_v2
WHEN NOT EXISTS (SELECT 1 FROM authorization_policy_v2 WHERE policy_id=OLD.policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published SoD catalogue is immutable'); END;

CREATE TABLE IF NOT EXISTS delegation_v2 (
    delegation_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    delegation_uuid      TEXT NOT NULL UNIQUE,
    policy_id            INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    source_grant_id      INTEGER NOT NULL REFERENCES access_grant_v2(grant_id),
    delegator_user_id    INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    delegate_user_id     INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    scope_id             INTEGER NOT NULL REFERENCES authorization_scope_v2(scope_id),
    requested_by_user_id INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    approved_by_user_id  INTEGER REFERENCES identity_account_v2(user_id),
    requested_at         TEXT NOT NULL,
    decided_at           TEXT,
    starts_at            TEXT NOT NULL,
    expires_at           TEXT NOT NULL,
    reason_code          TEXT NOT NULL,
    justification        TEXT NOT NULL,
    allow_redelegation   INTEGER NOT NULL DEFAULT 0,
    status               TEXT NOT NULL DEFAULT 'REQUESTED',
    revoked_at           TEXT,
    revoked_by_user_id   INTEGER REFERENCES identity_account_v2(user_id),
    revocation_reason    TEXT,
    CHECK (delegator_user_id <> delegate_user_id),
    CHECK (allow_redelegation=0),
    CHECK (expires_at > starts_at),
    CHECK (status IN ('REQUESTED','APPROVED','ACTIVE','REJECTED','SUSPENDED','REVOKED','EXPIRED')),
    CHECK (approved_by_user_id IS NULL OR (
      approved_by_user_id <> requested_by_user_id
      AND approved_by_user_id <> delegator_user_id
      AND approved_by_user_id <> delegate_user_id
    )),
    CHECK (status NOT IN ('APPROVED','ACTIVE','REJECTED') OR (
      approved_by_user_id IS NOT NULL AND decided_at IS NOT NULL
    )),
    CHECK (status <> 'REVOKED' OR (
      revoked_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revocation_reason IS NOT NULL
    ))
);

CREATE TRIGGER IF NOT EXISTS delegation_source_bounds_insert_v2
BEFORE INSERT ON delegation_v2
WHEN NOT EXISTS (
  SELECT 1
  FROM access_grant_v2 g
  JOIN authorization_scope_v2 gs ON gs.scope_id=g.scope_id AND gs.status='ACTIVE'
  JOIN authorization_scope_v2 ds ON ds.scope_id=NEW.scope_id AND ds.status='ACTIVE'
  LEFT JOIN department dd ON dd.department_id=ds.department_id
  LEFT JOIN nursing_unit du ON du.unit_id=ds.unit_id
  LEFT JOIN department dud ON dud.department_id=du.department_id
  WHERE g.grant_id=NEW.source_grant_id
    AND g.policy_id=NEW.policy_id
    AND g.user_id=NEW.delegator_user_id
    AND g.status='ACTIVE'
    AND g.effective_from <= NEW.starts_at
    AND (g.effective_to IS NULL OR g.effective_to >= NEW.expires_at)
    AND (
      (gs.scope_type='FACILITY' AND (
        (ds.scope_type='FACILITY' AND ds.facility_id=gs.facility_id) OR
        (ds.scope_type='DEPARTMENT' AND dd.facility_id=gs.facility_id) OR
        (ds.scope_type='UNIT' AND dud.facility_id=gs.facility_id)
      )) OR
      (gs.scope_type='DEPARTMENT' AND (
        (ds.scope_type='DEPARTMENT' AND ds.department_id=gs.department_id) OR
        (ds.scope_type='UNIT' AND du.department_id=gs.department_id)
      )) OR
      (gs.scope_type='UNIT' AND ds.scope_type='UNIT' AND ds.unit_id=gs.unit_id)
    )
)
BEGIN
  SELECT RAISE(ABORT, 'delegation must be bounded by active source grant');
END;

CREATE TABLE IF NOT EXISTS delegation_permission_v2 (
    delegation_id        INTEGER NOT NULL REFERENCES delegation_v2(delegation_id),
    permission_id        INTEGER NOT NULL REFERENCES authorization_permission_v2(permission_id),
    PRIMARY KEY (delegation_id, permission_id)
);

CREATE TRIGGER IF NOT EXISTS delegation_core_immutable_v2
BEFORE UPDATE OF policy_id, source_grant_id, delegator_user_id, delegate_user_id,
  scope_id, requested_by_user_id, requested_at,
  starts_at, expires_at, allow_redelegation
ON delegation_v2
BEGIN SELECT RAISE(ABORT, 'delegation core fields are immutable'); END;

CREATE TRIGGER IF NOT EXISTS delegation_decision_immutable_v2
BEFORE UPDATE OF approved_by_user_id, decided_at ON delegation_v2
WHEN OLD.status <> 'REQUESTED' OR NEW.status NOT IN ('APPROVED','REJECTED')
BEGIN SELECT RAISE(ABORT, 'delegation decision is immutable'); END;

CREATE TRIGGER IF NOT EXISTS delegation_permission_subset_insert_v2
BEFORE INSERT ON delegation_permission_v2
WHEN NOT EXISTS (
  SELECT 1 FROM delegation_v2 d
  JOIN access_grant_v2 g ON g.grant_id=d.source_grant_id
  JOIN authorization_permission_v2 p ON p.permission_id=NEW.permission_id
  JOIN authorization_role_permission_v2 rp
    ON rp.role_id=g.role_id AND rp.permission_id=NEW.permission_id AND rp.policy_id=d.policy_id
  WHERE d.delegation_id=NEW.delegation_id
    AND p.policy_id=d.policy_id AND p.status='ACTIVE' AND p.delegable=1
)
BEGIN
  SELECT RAISE(ABORT, 'delegated permission must be delegable subset of source role');
END;

CREATE TRIGGER IF NOT EXISTS delegation_permission_subset_update_v2
BEFORE UPDATE OF delegation_id, permission_id ON delegation_permission_v2
WHEN NOT EXISTS (
  SELECT 1 FROM delegation_v2 d
  JOIN access_grant_v2 g ON g.grant_id=d.source_grant_id
  JOIN authorization_permission_v2 p ON p.permission_id=NEW.permission_id
  JOIN authorization_role_permission_v2 rp
    ON rp.role_id=g.role_id AND rp.permission_id=NEW.permission_id AND rp.policy_id=d.policy_id
  WHERE d.delegation_id=NEW.delegation_id
    AND p.policy_id=d.policy_id AND p.status='ACTIVE' AND p.delegable=1
)
BEGIN
  SELECT RAISE(ABORT, 'delegated permission must be delegable subset of source role');
END;

CREATE TRIGGER IF NOT EXISTS delegation_permission_active_delete_v2
BEFORE DELETE ON delegation_permission_v2
WHEN EXISTS (
  SELECT 1 FROM delegation_v2
  WHERE delegation_id=OLD.delegation_id AND status IN ('APPROVED','ACTIVE')
)
BEGIN
  SELECT RAISE(ABORT, 'active or approved delegation permissions are immutable');
END;

CREATE TABLE IF NOT EXISTS authorization_decision_v2 (
    decision_id          TEXT PRIMARY KEY,
    request_id           TEXT NOT NULL UNIQUE,
    decided_at           TEXT NOT NULL,
    user_id              INTEGER REFERENCES identity_account_v2(user_id),
    permission_code      TEXT NOT NULL,
    resource_type        TEXT NOT NULL,
    resource_code        TEXT NOT NULL,
    resolved_scope_id    INTEGER REFERENCES authorization_scope_v2(scope_id),
    decision             TEXT NOT NULL,
    reason_code          TEXT NOT NULL,
    reason_detail        TEXT NOT NULL,
    matched_grant_id     INTEGER REFERENCES access_grant_v2(grant_id),
    delegation_id        INTEGER REFERENCES delegation_v2(delegation_id),
    policy_id            INTEGER REFERENCES authorization_policy_v2(policy_id),
    policy_version       TEXT NOT NULL,
    requires_part4       INTEGER NOT NULL DEFAULT 0,
    context_json         TEXT NOT NULL DEFAULT '{}',
    engine_version       TEXT NOT NULL,
    CHECK (resource_type IN ('FACILITY','DEPARTMENT','UNIT','UNKNOWN')),
    CHECK (decision IN ('ALLOW','DENY','ERROR')),
    CHECK (requires_part4 IN (0,1))
);

CREATE TABLE IF NOT EXISTS authorization_decision_sod_v2 (
    decision_id          TEXT NOT NULL REFERENCES authorization_decision_v2(decision_id),
    sod_rule_id          INTEGER NOT NULL REFERENCES sod_rule_v2(sod_rule_id),
    outcome              TEXT NOT NULL,
    PRIMARY KEY (decision_id, sod_rule_id),
    CHECK (outcome IN ('PASS','BLOCK','ALERT'))
);

CREATE TABLE IF NOT EXISTS authorization_lifecycle_event_v2 (
    event_id             TEXT PRIMARY KEY,
    occurred_at          TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    actor_user_id        INTEGER REFERENCES identity_account_v2(user_id),
    grant_id             INTEGER REFERENCES access_grant_v2(grant_id),
    delegation_id        INTEGER REFERENCES delegation_v2(delegation_id),
    request_id           INTEGER REFERENCES access_grant_request_v2(request_id),
    reason_code          TEXT NOT NULL,
    detail_json          TEXT NOT NULL DEFAULT '{}',
    CHECK (grant_id IS NOT NULL OR delegation_id IS NOT NULL OR request_id IS NOT NULL)
);

CREATE TRIGGER IF NOT EXISTS authorization_decision_no_update_v2
BEFORE UPDATE ON authorization_decision_v2 BEGIN
  SELECT RAISE(ABORT, 'authorization decisions are append-only');
END;
CREATE TRIGGER IF NOT EXISTS authorization_decision_no_delete_v2
BEFORE DELETE ON authorization_decision_v2 BEGIN
  SELECT RAISE(ABORT, 'authorization decisions are append-only');
END;
CREATE TRIGGER IF NOT EXISTS authorization_decision_sod_no_update_v2
BEFORE UPDATE ON authorization_decision_sod_v2 BEGIN
  SELECT RAISE(ABORT, 'authorization decision SoD evidence is append-only');
END;
CREATE TRIGGER IF NOT EXISTS authorization_decision_sod_no_delete_v2
BEFORE DELETE ON authorization_decision_sod_v2 BEGIN
  SELECT RAISE(ABORT, 'authorization decision SoD evidence is append-only');
END;
CREATE TRIGGER IF NOT EXISTS authorization_lifecycle_no_update_v2
BEFORE UPDATE ON authorization_lifecycle_event_v2 BEGIN
  SELECT RAISE(ABORT, 'authorization lifecycle evidence is append-only');
END;
CREATE TRIGGER IF NOT EXISTS authorization_lifecycle_no_delete_v2
BEFORE DELETE ON authorization_lifecycle_event_v2 BEGIN
  SELECT RAISE(ABORT, 'authorization lifecycle evidence is append-only');
END;

CREATE INDEX IF NOT EXISTS idx_access_grant_user_time_v2
ON access_grant_v2(user_id, policy_id, status, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_access_grant_scope_v2
ON access_grant_v2(scope_id, role_id, status);
CREATE INDEX IF NOT EXISTS idx_delegation_delegate_time_v2
ON delegation_v2(delegate_user_id, policy_id, status, starts_at, expires_at);
CREATE INDEX IF NOT EXISTS idx_delegation_source_v2
ON delegation_v2(source_grant_id, status);
CREATE INDEX IF NOT EXISTS idx_sod_policy_status_v2
ON sod_rule_v2(policy_id, status);
CREATE INDEX IF NOT EXISTS idx_authorization_decision_lookup_v2
ON authorization_decision_v2(user_id, permission_code, decided_at);
CREATE INDEX IF NOT EXISTS idx_authorization_lifecycle_time_v2
ON authorization_lifecycle_event_v2(occurred_at, event_type);
