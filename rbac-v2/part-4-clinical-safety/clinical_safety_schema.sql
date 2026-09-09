-- HNWMS RBAC v2 Part 4: additive clinical-safety shadow schema for SQLite.
-- Reuses Part 2 identity, Part 3 authorization, and external compliance rules.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clinical_safety_policy_v2 (
    safety_policy_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    version_code           TEXT NOT NULL UNIQUE,
    authorization_policy_id INTEGER NOT NULL REFERENCES authorization_policy_v2(policy_id),
    compliance_ruleset_version TEXT NOT NULL,
    status                 TEXT NOT NULL DEFAULT 'DRAFT',
    effective_from         TEXT,
    effective_to           TEXT,
    authorization_decision_ttl_seconds INTEGER NOT NULL,
    max_break_glass_seconds INTEGER NOT NULL DEFAULT 14400,
    review_sla_seconds     INTEGER NOT NULL DEFAULT 86400,
    approved_by_user_id    INTEGER REFERENCES identity_account_v2(user_id),
    approved_at            TEXT,
    published_at           TEXT,
    CHECK (status IN ('DRAFT','ACTIVE','RETIRED','REJECTED')),
    CHECK (authorization_decision_ttl_seconds > 0),
    CHECK (max_break_glass_seconds > 0),
    CHECK (review_sla_seconds > 0),
    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from),
    CHECK (status <> 'ACTIVE' OR (
      effective_from IS NOT NULL AND approved_by_user_id IS NOT NULL
      AND approved_at IS NOT NULL AND published_at IS NOT NULL
    ))
);

CREATE TRIGGER IF NOT EXISTS clinical_safety_policy_published_core_immutable_v2
BEFORE UPDATE OF version_code, authorization_policy_id, compliance_ruleset_version,
  effective_from, authorization_decision_ttl_seconds, max_break_glass_seconds,
  review_sla_seconds, approved_by_user_id, approved_at, published_at
ON clinical_safety_policy_v2
WHEN OLD.status IN ('ACTIVE','RETIRED')
BEGIN SELECT RAISE(ABORT, 'published safety policy core is immutable'); END;

CREATE TRIGGER IF NOT EXISTS clinical_safety_policy_active_transition_v2
BEFORE UPDATE OF status ON clinical_safety_policy_v2
WHEN OLD.status='ACTIVE' AND NEW.status<>'RETIRED'
BEGIN SELECT RAISE(ABORT, 'active safety policy may only transition to retired'); END;

CREATE TABLE IF NOT EXISTS safety_permission_profile_v2 (
    profile_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    safety_policy_id       INTEGER NOT NULL REFERENCES clinical_safety_policy_v2(safety_policy_id),
    authorization_policy_id INTEGER NOT NULL,
    permission_id          INTEGER NOT NULL,
    requires_eligibility   INTEGER NOT NULL DEFAULT 0,
    requires_guardrails    INTEGER NOT NULL DEFAULT 0,
    allows_remediation     INTEGER NOT NULL DEFAULT 0,
    status                 TEXT NOT NULL DEFAULT 'ACTIVE',
    CHECK (requires_eligibility IN (0,1)),
    CHECK (requires_guardrails IN (0,1)),
    CHECK (allows_remediation IN (0,1)),
    CHECK (status IN ('ACTIVE','INACTIVE')),
    CHECK (allows_remediation=0 OR (requires_eligibility=0 AND requires_guardrails=0)),
    UNIQUE (safety_policy_id, permission_id),
    FOREIGN KEY (authorization_policy_id, permission_id)
      REFERENCES authorization_permission_v2(policy_id, permission_id)
);

CREATE TRIGGER IF NOT EXISTS safety_permission_policy_match_v2
BEFORE INSERT ON safety_permission_profile_v2
WHEN NOT EXISTS (
  SELECT 1 FROM clinical_safety_policy_v2
  WHERE safety_policy_id=NEW.safety_policy_id
    AND authorization_policy_id=NEW.authorization_policy_id
    AND status='DRAFT'
)
BEGIN SELECT RAISE(ABORT, 'permission profile requires matching draft safety policy'); END;

CREATE TRIGGER IF NOT EXISTS safety_permission_profile_published_update_v2
BEFORE UPDATE ON safety_permission_profile_v2
WHEN NOT EXISTS (SELECT 1 FROM clinical_safety_policy_v2 WHERE safety_policy_id=OLD.safety_policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published safety permission profile is immutable'); END;
CREATE TRIGGER IF NOT EXISTS safety_permission_profile_published_delete_v2
BEFORE DELETE ON safety_permission_profile_v2
WHEN NOT EXISTS (SELECT 1 FROM clinical_safety_policy_v2 WHERE safety_policy_id=OLD.safety_policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published safety permission profile is immutable'); END;

CREATE TABLE IF NOT EXISTS clinical_eligibility_snapshot_v2 (
    eligibility_snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_uuid          TEXT NOT NULL UNIQUE,
    staff_id               INTEGER NOT NULL REFERENCES staff_member_v2(staff_id),
    unit_id                INTEGER NOT NULL REFERENCES nursing_unit(unit_id),
    worker_type            TEXT NOT NULL,
    employment_state       TEXT NOT NULL,
    license_state          TEXT NOT NULL,
    credential_state       TEXT NOT NULL,
    competency_state       TEXT NOT NULL,
    training_state         TEXT NOT NULL,
    unit_authorization_state TEXT NOT NULL,
    occupational_state     TEXT NOT NULL DEFAULT 'PASS',
    shift_context_state    TEXT NOT NULL DEFAULT 'PASS',
    source_state           TEXT NOT NULL,
    captured_at            TEXT NOT NULL,
    valid_until            TEXT NOT NULL,
    evidence_version       TEXT NOT NULL,
    source_refs_json       TEXT NOT NULL DEFAULT '{}',
    created_by_service     TEXT NOT NULL,
    CHECK (worker_type IN ('EMPLOYEE','AGENCY')),
    CHECK (employment_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (license_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (credential_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (competency_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (training_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (unit_authorization_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (occupational_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (shift_context_state IN ('PASS','FAIL','UNKNOWN')),
    CHECK (source_state IN ('AVAILABLE','DEGRADED','UNAVAILABLE')),
    CHECK (valid_until > captured_at)
);

CREATE TRIGGER IF NOT EXISTS eligibility_unit_active_insert_v2
BEFORE INSERT ON clinical_eligibility_snapshot_v2
WHEN NOT EXISTS (
  SELECT 1 FROM nursing_unit u JOIN department d ON d.department_id=u.department_id
  JOIN facility f ON f.facility_id=d.facility_id
  WHERE u.unit_id=NEW.unit_id AND u.status='ACTIVE' AND d.status='ACTIVE' AND f.status='ACTIVE'
)
BEGIN SELECT RAISE(ABORT, 'eligibility snapshot requires active unit ancestry'); END;

CREATE TABLE IF NOT EXISTS guardrail_rule_adapter_v2 (
    rule_adapter_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    safety_policy_id      INTEGER NOT NULL REFERENCES clinical_safety_policy_v2(safety_policy_id),
    external_rule_code    TEXT NOT NULL,
    external_ruleset_version TEXT NOT NULL,
    rule_domain           TEXT NOT NULL,
    default_effect        TEXT NOT NULL,
    exception_allowed     INTEGER NOT NULL DEFAULT 0,
    owner_role            TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'ACTIVE',
    CHECK (default_effect IN ('INFORM','WARN','BLOCK')),
    CHECK (exception_allowed IN (0,1)),
    CHECK (status IN ('ACTIVE','INACTIVE')),
    UNIQUE (safety_policy_id, external_rule_code)
);

CREATE TRIGGER IF NOT EXISTS guardrail_adapter_draft_insert_v2
BEFORE INSERT ON guardrail_rule_adapter_v2
WHEN NOT EXISTS (
  SELECT 1 FROM clinical_safety_policy_v2
  WHERE safety_policy_id=NEW.safety_policy_id AND status='DRAFT'
    AND compliance_ruleset_version=NEW.external_ruleset_version
)
BEGIN SELECT RAISE(ABORT, 'rule adapter requires matching draft ruleset'); END;

CREATE TRIGGER IF NOT EXISTS guardrail_adapter_published_update_v2
BEFORE UPDATE ON guardrail_rule_adapter_v2
WHEN NOT EXISTS (SELECT 1 FROM clinical_safety_policy_v2 WHERE safety_policy_id=OLD.safety_policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published rule adapter is immutable'); END;
CREATE TRIGGER IF NOT EXISTS guardrail_adapter_published_delete_v2
BEFORE DELETE ON guardrail_rule_adapter_v2
WHEN NOT EXISTS (SELECT 1 FROM clinical_safety_policy_v2 WHERE safety_policy_id=OLD.safety_policy_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'published rule adapter is immutable'); END;

CREATE TABLE IF NOT EXISTS guardrail_evaluation_v2 (
    guardrail_evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_uuid        TEXT NOT NULL UNIQUE,
    safety_policy_id       INTEGER NOT NULL REFERENCES clinical_safety_policy_v2(safety_policy_id),
    target_type            TEXT NOT NULL,
    target_reference       TEXT NOT NULL,
    candidate_hash         TEXT NOT NULL,
    staff_id               INTEGER NOT NULL REFERENCES staff_member_v2(staff_id),
    unit_id                INTEGER NOT NULL REFERENCES nursing_unit(unit_id),
    ruleset_version        TEXT NOT NULL,
    evaluated_at           TEXT NOT NULL,
    valid_until            TEXT NOT NULL,
    source_state           TEXT NOT NULL,
    status                 TEXT NOT NULL,
    declared_verdict       TEXT NOT NULL,
    input_refs_json        TEXT NOT NULL DEFAULT '{}',
    evaluator_version      TEXT NOT NULL,
    CHECK (target_type IN ('SHIFT','DEPLOYMENT','CARE_ASSIGNMENT','BED_ACTION','OT','LEAVE','OTHER')),
    CHECK (source_state IN ('AVAILABLE','DEGRADED','UNAVAILABLE')),
    CHECK (status IN ('COMPLETE','ERROR')),
    CHECK (declared_verdict IN ('ALLOW','INFORM','WARN','BLOCK','ERROR')),
    CHECK (valid_until > evaluated_at),
    UNIQUE (safety_policy_id, target_reference, candidate_hash)
);

CREATE TRIGGER IF NOT EXISTS guardrail_evaluation_policy_match_v2
BEFORE INSERT ON guardrail_evaluation_v2
WHEN NOT EXISTS (
  SELECT 1 FROM clinical_safety_policy_v2
  WHERE safety_policy_id=NEW.safety_policy_id
    AND compliance_ruleset_version=NEW.ruleset_version
)
BEGIN SELECT RAISE(ABORT, 'guardrail evaluation ruleset mismatch'); END;

CREATE TABLE IF NOT EXISTS guardrail_rule_result_v2 (
    rule_result_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guardrail_evaluation_id INTEGER NOT NULL REFERENCES guardrail_evaluation_v2(guardrail_evaluation_id),
    rule_adapter_id        INTEGER NOT NULL REFERENCES guardrail_rule_adapter_v2(rule_adapter_id),
    external_rule_code     TEXT NOT NULL,
    result                 TEXT NOT NULL,
    effective_verdict      TEXT NOT NULL,
    message                TEXT NOT NULL,
    evidence_json          TEXT NOT NULL DEFAULT '{}',
    CHECK (result IN ('PASS','INFORM','WARN','FAIL','ERROR')),
    CHECK (effective_verdict IN ('ALLOW','INFORM','WARN','BLOCK','ERROR')),
    UNIQUE (guardrail_evaluation_id, rule_adapter_id)
);

CREATE TRIGGER IF NOT EXISTS guardrail_result_match_insert_v2
BEFORE INSERT ON guardrail_rule_result_v2
WHEN NOT EXISTS (
  SELECT 1 FROM guardrail_evaluation_v2 e
  JOIN guardrail_rule_adapter_v2 r ON r.rule_adapter_id=NEW.rule_adapter_id
  WHERE e.guardrail_evaluation_id=NEW.guardrail_evaluation_id
    AND e.safety_policy_id=r.safety_policy_id
    AND r.external_rule_code=NEW.external_rule_code AND r.status='ACTIVE'
)
BEGIN SELECT RAISE(ABORT, 'guardrail result must match active rule adapter and evaluation'); END;

CREATE TABLE IF NOT EXISTS guardrail_exception_request_v2 (
    exception_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_uuid        TEXT NOT NULL UNIQUE,
    rule_result_id        INTEGER NOT NULL REFERENCES guardrail_rule_result_v2(rule_result_id),
    candidate_hash        TEXT NOT NULL,
    staff_id              INTEGER NOT NULL REFERENCES staff_member_v2(staff_id),
    unit_id               INTEGER NOT NULL REFERENCES nursing_unit(unit_id),
    requested_by_user_id  INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    requested_at          TEXT NOT NULL,
    starts_at             TEXT NOT NULL,
    expires_at            TEXT NOT NULL,
    reason_code           TEXT NOT NULL,
    justification         TEXT NOT NULL,
    risk_assessment       TEXT NOT NULL,
    mitigation            TEXT NOT NULL,
    corrective_action     TEXT NOT NULL,
    required_approvals    INTEGER NOT NULL DEFAULT 1,
    status                TEXT NOT NULL DEFAULT 'PENDING',
    revoked_at            TEXT,
    revoked_by_user_id    INTEGER REFERENCES identity_account_v2(user_id),
    revocation_reason     TEXT,
    CHECK (expires_at > starts_at),
    CHECK (required_approvals BETWEEN 1 AND 4),
    CHECK (length(trim(justification)) >= 10),
    CHECK (length(trim(risk_assessment)) >= 10),
    CHECK (length(trim(mitigation)) >= 10),
    CHECK (length(trim(corrective_action)) >= 10),
    CHECK (status IN ('PENDING','APPROVED','REJECTED','REVOKED','EXPIRED')),
    CHECK (status <> 'REVOKED' OR (
      revoked_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revocation_reason IS NOT NULL
    ))
);

CREATE TRIGGER IF NOT EXISTS guardrail_exception_result_match_insert_v2
BEFORE INSERT ON guardrail_exception_request_v2
WHEN NOT EXISTS (
  SELECT 1 FROM guardrail_rule_result_v2 rr
  JOIN guardrail_evaluation_v2 e ON e.guardrail_evaluation_id=rr.guardrail_evaluation_id
  JOIN guardrail_rule_adapter_v2 r ON r.rule_adapter_id=rr.rule_adapter_id
  WHERE rr.rule_result_id=NEW.rule_result_id AND rr.effective_verdict='BLOCK'
    AND r.exception_allowed=1
    AND e.candidate_hash=NEW.candidate_hash AND e.staff_id=NEW.staff_id AND e.unit_id=NEW.unit_id
)
BEGIN SELECT RAISE(ABORT, 'exception must match an exceptionable blocking result'); END;

CREATE TABLE IF NOT EXISTS guardrail_exception_approval_v2 (
    approval_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_id          INTEGER NOT NULL REFERENCES guardrail_exception_request_v2(exception_id),
    approval_step         INTEGER NOT NULL,
    approver_user_id      INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    authorization_decision_id TEXT NOT NULL REFERENCES authorization_decision_v2(decision_id),
    decision              TEXT NOT NULL,
    decision_note         TEXT NOT NULL,
    decided_at            TEXT NOT NULL,
    CHECK (approval_step BETWEEN 1 AND 4),
    CHECK (decision IN ('APPROVE','REJECT')),
    UNIQUE (exception_id, approval_step),
    UNIQUE (exception_id, approver_user_id)
);

CREATE TRIGGER IF NOT EXISTS guardrail_exception_core_immutable_v2
BEFORE UPDATE OF rule_result_id, candidate_hash, staff_id, unit_id,
  requested_by_user_id, requested_at, starts_at, expires_at, reason_code,
  justification, risk_assessment, mitigation, corrective_action, required_approvals
ON guardrail_exception_request_v2
BEGIN SELECT RAISE(ABORT, 'guardrail exception core is immutable'); END;

CREATE TRIGGER IF NOT EXISTS guardrail_exception_self_approval_v2
BEFORE INSERT ON guardrail_exception_approval_v2
WHEN EXISTS (
  SELECT 1 FROM guardrail_exception_request_v2
  WHERE exception_id=NEW.exception_id AND requested_by_user_id=NEW.approver_user_id
)
BEGIN SELECT RAISE(ABORT, 'guardrail exception requester cannot approve'); END;

CREATE TRIGGER IF NOT EXISTS guardrail_exception_approval_authorized_v2
BEFORE INSERT ON guardrail_exception_approval_v2
WHEN NOT EXISTS (
  SELECT 1 FROM guardrail_exception_request_v2 x
  JOIN guardrail_rule_result_v2 rr ON rr.rule_result_id=x.rule_result_id
  JOIN guardrail_evaluation_v2 e ON e.guardrail_evaluation_id=rr.guardrail_evaluation_id
  JOIN clinical_safety_policy_v2 sp ON sp.safety_policy_id=e.safety_policy_id
  JOIN nursing_unit u ON u.unit_id=x.unit_id
  JOIN authorization_decision_v2 d ON d.decision_id=NEW.authorization_decision_id
  WHERE x.exception_id=NEW.exception_id
    AND d.user_id=NEW.approver_user_id AND d.decision='ALLOW'
    AND d.permission_code='GUARDRAIL_EXCEPTION_APPROVE'
    AND d.resource_type='UNIT' AND d.resource_code=u.unit_code
    AND d.policy_id=sp.authorization_policy_id
)
BEGIN SELECT RAISE(ABORT, 'guardrail exception approval lacks matching authorization'); END;

CREATE TRIGGER IF NOT EXISTS guardrail_exception_approve_state_v2
BEFORE UPDATE OF status ON guardrail_exception_request_v2
WHEN NEW.status='APPROVED' AND (
  (SELECT COUNT(*) FROM guardrail_exception_approval_v2
   WHERE exception_id=OLD.exception_id AND decision='APPROVE') < OLD.required_approvals
  OR EXISTS (SELECT 1 FROM guardrail_exception_approval_v2
             WHERE exception_id=OLD.exception_id AND decision='REJECT')
)
BEGIN SELECT RAISE(ABORT, 'exception requires all independent approvals and no rejection'); END;

CREATE TABLE IF NOT EXISTS break_glass_bundle_v2 (
    bundle_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_code           TEXT NOT NULL,
    safety_policy_id      INTEGER NOT NULL REFERENCES clinical_safety_policy_v2(safety_policy_id),
    title                 TEXT NOT NULL,
    clinical_bundle       INTEGER NOT NULL DEFAULT 1,
    max_duration_seconds  INTEGER NOT NULL,
    status                TEXT NOT NULL DEFAULT 'DRAFT',
    approved_by_user_id   INTEGER REFERENCES identity_account_v2(user_id),
    approved_at           TEXT,
    CHECK (clinical_bundle IN (0,1)),
    CHECK (max_duration_seconds > 0),
    CHECK (status IN ('DRAFT','APPROVED','RETIRED','REJECTED')),
    CHECK (status <> 'APPROVED' OR (approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL)),
    UNIQUE (safety_policy_id, bundle_code)
);

CREATE TABLE IF NOT EXISTS break_glass_bundle_permission_v2 (
    bundle_id             INTEGER NOT NULL REFERENCES break_glass_bundle_v2(bundle_id),
    permission_id         INTEGER NOT NULL REFERENCES authorization_permission_v2(permission_id),
    PRIMARY KEY (bundle_id, permission_id)
);

CREATE TRIGGER IF NOT EXISTS break_glass_bundle_approved_core_immutable_v2
BEFORE UPDATE OF bundle_code, safety_policy_id, title, clinical_bundle,
  max_duration_seconds, approved_by_user_id, approved_at
ON break_glass_bundle_v2
WHEN OLD.status IN ('APPROVED','RETIRED')
BEGIN SELECT RAISE(ABORT, 'approved break-glass bundle core is immutable'); END;

CREATE TRIGGER IF NOT EXISTS break_glass_bundle_active_transition_v2
BEFORE UPDATE OF status ON break_glass_bundle_v2
WHEN OLD.status='APPROVED' AND NEW.status<>'RETIRED'
BEGIN SELECT RAISE(ABORT, 'approved break-glass bundle may only transition to retired'); END;

CREATE TRIGGER IF NOT EXISTS break_glass_permission_allowed_insert_v2
BEFORE INSERT ON break_glass_bundle_permission_v2
WHEN NOT EXISTS (
  SELECT 1 FROM break_glass_bundle_v2 b
  JOIN clinical_safety_policy_v2 sp ON sp.safety_policy_id=b.safety_policy_id
  JOIN authorization_permission_v2 p
    ON p.permission_id=NEW.permission_id AND p.policy_id=sp.authorization_policy_id
  WHERE b.bundle_id=NEW.bundle_id AND b.status='DRAFT' AND p.status='ACTIVE'
    AND p.perm_code NOT IN (
      'AUDIT_ADMIN','CREDENTIAL_VERIFY','LICENSE_EXCEPTION_APPROVE',
      'GRANT_APPROVE','GRANT_ACTIVATE','DELEGATION_APPROVE','BREAK_GLASS_REVIEW'
    )
    AND p.perm_code NOT LIKE 'IDENTITY_%'
    AND p.perm_code NOT LIKE 'ROLE_%'
    AND p.perm_code NOT LIKE 'POLICY_%'
)
BEGIN SELECT RAISE(ABORT, 'permission is not allowed in break-glass bundle'); END;

CREATE TRIGGER IF NOT EXISTS break_glass_permission_published_update_v2
BEFORE UPDATE ON break_glass_bundle_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM break_glass_bundle_v2 WHERE bundle_id=OLD.bundle_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'approved break-glass permissions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS break_glass_permission_published_delete_v2
BEFORE DELETE ON break_glass_bundle_permission_v2
WHEN NOT EXISTS (SELECT 1 FROM break_glass_bundle_v2 WHERE bundle_id=OLD.bundle_id AND status='DRAFT')
BEGIN SELECT RAISE(ABORT, 'approved break-glass permissions are immutable'); END;

CREATE TABLE IF NOT EXISTS break_glass_event_v2 (
    break_glass_event_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uuid            TEXT NOT NULL UNIQUE,
    safety_policy_id      INTEGER NOT NULL REFERENCES clinical_safety_policy_v2(safety_policy_id),
    bundle_id             INTEGER NOT NULL REFERENCES break_glass_bundle_v2(bundle_id),
    user_id               INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    staff_id              INTEGER NOT NULL REFERENCES staff_member_v2(staff_id),
    scope_id              INTEGER NOT NULL REFERENCES authorization_scope_v2(scope_id),
    target_unit_id        INTEGER NOT NULL REFERENCES nursing_unit(unit_id),
    requested_at          TEXT NOT NULL,
    activated_at          TEXT,
    expires_at            TEXT NOT NULL,
    review_due_at         TEXT NOT NULL,
    authentication_assurance TEXT NOT NULL,
    reason_code           TEXT NOT NULL,
    justification         TEXT NOT NULL,
    incident_reference    TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'REQUESTED',
    revoked_at            TEXT,
    revoked_by_user_id    INTEGER REFERENCES identity_account_v2(user_id),
    revocation_reason     TEXT,
    CHECK (authentication_assurance IN ('AAL2','STEP_UP')),
    CHECK (expires_at > requested_at),
    CHECK (review_due_at > expires_at),
    CHECK (length(trim(justification)) >= 10),
    CHECK (status IN ('REQUESTED','ACTIVE','DENIED','REVOKED','EXPIRED','PENDING_REVIEW','CLOSED','FLAGGED')),
    CHECK (status <> 'ACTIVE' OR (activated_at IS NOT NULL AND authentication_assurance='STEP_UP')),
    CHECK (status <> 'REVOKED' OR (
      revoked_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revocation_reason IS NOT NULL
    ))
);

CREATE TRIGGER IF NOT EXISTS break_glass_activation_insert_v2
BEFORE INSERT ON break_glass_event_v2
WHEN NEW.status='ACTIVE' AND NOT EXISTS (
  SELECT 1 FROM clinical_safety_policy_v2 sp
  JOIN break_glass_bundle_v2 b ON b.safety_policy_id=sp.safety_policy_id
  JOIN identity_account_v2 a ON a.user_id=NEW.user_id
  JOIN identity_staff_link_v2 l ON l.user_id=a.user_id AND l.staff_id=NEW.staff_id
  JOIN staff_member_v2 sm ON sm.staff_id=l.staff_id
  JOIN authorization_scope_v2 s ON s.scope_id=NEW.scope_id
  JOIN nursing_unit tu ON tu.unit_id=NEW.target_unit_id AND tu.status='ACTIVE'
  JOIN department td ON td.department_id=tu.department_id AND td.status='ACTIVE'
  WHERE sp.safety_policy_id=NEW.safety_policy_id AND sp.status='ACTIVE'
    AND b.bundle_id=NEW.bundle_id AND b.status='APPROVED'
    AND a.account_type='HUMAN' AND a.account_status='ACTIVE'
    AND sm.record_status='ACTIVE' AND s.status='ACTIVE'
    AND (
      (s.scope_type='UNIT' AND s.unit_id=tu.unit_id) OR
      (s.scope_type='DEPARTMENT' AND s.department_id=tu.department_id) OR
      (s.scope_type='FACILITY' AND s.facility_id=td.facility_id)
    )
    AND (
      b.clinical_bundle=0 OR EXISTS (
        SELECT 1 FROM clinical_eligibility_snapshot_v2 es
        WHERE es.staff_id=NEW.staff_id AND es.unit_id=NEW.target_unit_id
          AND es.source_state='AVAILABLE'
          AND es.captured_at<=NEW.activated_at AND es.valid_until>NEW.activated_at
          AND es.employment_state='PASS' AND es.license_state='PASS'
          AND es.credential_state='PASS' AND es.competency_state='PASS'
          AND es.training_state='PASS' AND es.unit_authorization_state='PASS'
          AND es.occupational_state='PASS' AND es.shift_context_state='PASS'
          AND NOT EXISTS (
            SELECT 1 FROM clinical_eligibility_snapshot_v2 newer
            WHERE newer.staff_id=es.staff_id AND newer.unit_id=es.unit_id
              AND newer.captured_at<=NEW.activated_at AND newer.captured_at>es.captured_at
          )
      )
    )
    AND NEW.authentication_assurance='STEP_UP'
    AND (julianday(NEW.expires_at)-julianday(NEW.activated_at))*86400.0
        <= MIN(sp.max_break_glass_seconds,b.max_duration_seconds)+0.5
)
BEGIN SELECT RAISE(ABORT, 'break-glass activation controls failed'); END;

CREATE TRIGGER IF NOT EXISTS break_glass_activation_update_v2
BEFORE UPDATE OF status ON break_glass_event_v2
WHEN NEW.status='ACTIVE' AND NOT EXISTS (
  SELECT 1 FROM clinical_safety_policy_v2 sp
  JOIN break_glass_bundle_v2 b ON b.safety_policy_id=sp.safety_policy_id
  JOIN identity_account_v2 a ON a.user_id=NEW.user_id
  JOIN identity_staff_link_v2 l ON l.user_id=a.user_id AND l.staff_id=NEW.staff_id
  JOIN staff_member_v2 sm ON sm.staff_id=l.staff_id
  JOIN authorization_scope_v2 s ON s.scope_id=NEW.scope_id
  JOIN nursing_unit tu ON tu.unit_id=NEW.target_unit_id AND tu.status='ACTIVE'
  JOIN department td ON td.department_id=tu.department_id AND td.status='ACTIVE'
  WHERE sp.safety_policy_id=NEW.safety_policy_id AND sp.status='ACTIVE'
    AND b.bundle_id=NEW.bundle_id AND b.status='APPROVED'
    AND a.account_type='HUMAN' AND a.account_status='ACTIVE'
    AND sm.record_status='ACTIVE' AND s.status='ACTIVE'
    AND (
      (s.scope_type='UNIT' AND s.unit_id=tu.unit_id) OR
      (s.scope_type='DEPARTMENT' AND s.department_id=tu.department_id) OR
      (s.scope_type='FACILITY' AND s.facility_id=td.facility_id)
    )
    AND (
      b.clinical_bundle=0 OR EXISTS (
        SELECT 1 FROM clinical_eligibility_snapshot_v2 es
        WHERE es.staff_id=NEW.staff_id AND es.unit_id=NEW.target_unit_id
          AND es.source_state='AVAILABLE'
          AND es.captured_at<=NEW.activated_at AND es.valid_until>NEW.activated_at
          AND es.employment_state='PASS' AND es.license_state='PASS'
          AND es.credential_state='PASS' AND es.competency_state='PASS'
          AND es.training_state='PASS' AND es.unit_authorization_state='PASS'
          AND es.occupational_state='PASS' AND es.shift_context_state='PASS'
          AND NOT EXISTS (
            SELECT 1 FROM clinical_eligibility_snapshot_v2 newer
            WHERE newer.staff_id=es.staff_id AND newer.unit_id=es.unit_id
              AND newer.captured_at<=NEW.activated_at AND newer.captured_at>es.captured_at
          )
      )
    )
    AND NEW.authentication_assurance='STEP_UP'
    AND NEW.activated_at IS NOT NULL
    AND (julianday(NEW.expires_at)-julianday(NEW.activated_at))*86400.0
        <= MIN(sp.max_break_glass_seconds,b.max_duration_seconds)+0.5
)
BEGIN SELECT RAISE(ABORT, 'break-glass activation controls failed'); END;

CREATE TABLE IF NOT EXISTS clinical_safety_decision_v2 (
    safety_decision_id    TEXT PRIMARY KEY,
    request_id            TEXT NOT NULL UNIQUE,
    decided_at            TEXT NOT NULL,
    authorization_decision_id TEXT REFERENCES authorization_decision_v2(decision_id),
    break_glass_event_id  INTEGER REFERENCES break_glass_event_v2(break_glass_event_id),
    staff_id              INTEGER REFERENCES staff_member_v2(staff_id),
    permission_code       TEXT NOT NULL,
    unit_id               INTEGER REFERENCES nursing_unit(unit_id),
    candidate_hash        TEXT NOT NULL,
    eligibility_snapshot_id INTEGER REFERENCES clinical_eligibility_snapshot_v2(eligibility_snapshot_id),
    guardrail_evaluation_id INTEGER REFERENCES guardrail_evaluation_v2(guardrail_evaluation_id),
    result                 TEXT NOT NULL,
    reason_code            TEXT NOT NULL,
    reason_detail          TEXT NOT NULL,
    safety_policy_id       INTEGER REFERENCES clinical_safety_policy_v2(safety_policy_id),
    safety_policy_version  TEXT NOT NULL,
    CHECK (result IN ('ALLOW','WARN','BLOCK','ERROR')),
    CHECK (result NOT IN ('ALLOW','WARN') OR authorization_decision_id IS NOT NULL OR break_glass_event_id IS NOT NULL)
);

CREATE TRIGGER IF NOT EXISTS break_glass_active_core_immutable_v2
BEFORE UPDATE OF safety_policy_id, bundle_id, user_id, staff_id, scope_id,
  target_unit_id, requested_at, expires_at, review_due_at,
  authentication_assurance, reason_code, justification, incident_reference
ON break_glass_event_v2
WHEN OLD.status <> 'REQUESTED'
BEGIN SELECT RAISE(ABORT, 'active break-glass event core is immutable'); END;

CREATE TABLE IF NOT EXISTS clinical_safety_decision_exception_v2 (
    safety_decision_id    TEXT NOT NULL REFERENCES clinical_safety_decision_v2(safety_decision_id),
    exception_id          INTEGER NOT NULL REFERENCES guardrail_exception_request_v2(exception_id),
    PRIMARY KEY (safety_decision_id, exception_id)
);

CREATE TABLE IF NOT EXISTS break_glass_use_v2 (
    use_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    break_glass_event_id  INTEGER NOT NULL REFERENCES break_glass_event_v2(break_glass_event_id),
    safety_decision_id    TEXT NOT NULL UNIQUE REFERENCES clinical_safety_decision_v2(safety_decision_id),
    used_at               TEXT NOT NULL,
    permission_code       TEXT NOT NULL,
    resource_type         TEXT NOT NULL,
    resource_code         TEXT NOT NULL,
    outcome               TEXT NOT NULL,
    CHECK (outcome IN ('ALLOW','WARN','BLOCK','ERROR'))
);

CREATE TABLE IF NOT EXISTS break_glass_review_v2 (
    review_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    break_glass_event_id  INTEGER NOT NULL REFERENCES break_glass_event_v2(break_glass_event_id),
    reviewer_user_id      INTEGER NOT NULL REFERENCES identity_account_v2(user_id),
    authorization_decision_id TEXT NOT NULL REFERENCES authorization_decision_v2(decision_id),
    decision              TEXT NOT NULL,
    notes                 TEXT NOT NULL,
    reviewed_at           TEXT NOT NULL,
    CHECK (decision IN ('CLOSE','FLAG','ESCALATE')),
    UNIQUE (break_glass_event_id, reviewer_user_id)
);

CREATE TRIGGER IF NOT EXISTS break_glass_review_independent_v2
BEFORE INSERT ON break_glass_review_v2
WHEN EXISTS (
  SELECT 1 FROM break_glass_event_v2
  WHERE break_glass_event_id=NEW.break_glass_event_id AND user_id=NEW.reviewer_user_id
)
BEGIN SELECT RAISE(ABORT, 'break-glass activator cannot review own event'); END;

CREATE TRIGGER IF NOT EXISTS break_glass_review_authorized_v2
BEFORE INSERT ON break_glass_review_v2
WHEN NOT EXISTS (
  SELECT 1 FROM break_glass_event_v2 e
  JOIN clinical_safety_policy_v2 sp ON sp.safety_policy_id=e.safety_policy_id
  JOIN nursing_unit u ON u.unit_id=e.target_unit_id
  JOIN authorization_decision_v2 d ON d.decision_id=NEW.authorization_decision_id
  WHERE e.break_glass_event_id=NEW.break_glass_event_id
    AND d.user_id=NEW.reviewer_user_id AND d.decision='ALLOW'
    AND d.permission_code='BREAK_GLASS_REVIEW'
    AND d.resource_type='UNIT' AND d.resource_code=u.unit_code
    AND d.policy_id=sp.authorization_policy_id
)
BEGIN SELECT RAISE(ABORT, 'break-glass review lacks matching authorization'); END;

CREATE TABLE IF NOT EXISTS safety_alert_v2 (
    alert_id              TEXT PRIMARY KEY,
    alert_type            TEXT NOT NULL,
    severity              TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    break_glass_event_id  INTEGER REFERENCES break_glass_event_v2(break_glass_event_id),
    guardrail_evaluation_id INTEGER REFERENCES guardrail_evaluation_v2(guardrail_evaluation_id),
    eligibility_snapshot_id INTEGER REFERENCES clinical_eligibility_snapshot_v2(eligibility_snapshot_id),
    routing_key           TEXT NOT NULL,
    detail_json           TEXT NOT NULL DEFAULT '{}',
    CHECK (severity IN ('INFO','WARNING','HIGH','CRITICAL')),
    CHECK (break_glass_event_id IS NOT NULL OR guardrail_evaluation_id IS NOT NULL OR eligibility_snapshot_id IS NOT NULL)
);

CREATE TRIGGER IF NOT EXISTS break_glass_activation_alert_v2
AFTER INSERT ON break_glass_event_v2
WHEN NEW.status='ACTIVE'
BEGIN
  INSERT INTO safety_alert_v2
    (alert_id,alert_type,severity,created_at,break_glass_event_id,routing_key,detail_json)
  VALUES
    ('BG-ACT-' || NEW.event_uuid,'BREAK_GLASS_ACTIVATED','CRITICAL',NEW.activated_at,
     NEW.break_glass_event_id,'DON_RISK_SECURITY_AUDIT','{}');
END;

CREATE TRIGGER IF NOT EXISTS break_glass_activation_alert_update_v2
AFTER UPDATE OF status ON break_glass_event_v2
WHEN OLD.status<>'ACTIVE' AND NEW.status='ACTIVE'
BEGIN
  INSERT INTO safety_alert_v2
    (alert_id,alert_type,severity,created_at,break_glass_event_id,routing_key,detail_json)
  VALUES
    ('BG-ACT-' || NEW.event_uuid,'BREAK_GLASS_ACTIVATED','CRITICAL',NEW.activated_at,
     NEW.break_glass_event_id,'DON_RISK_SECURITY_AUDIT','{}');
END;

-- Immutable evidence tables.
CREATE TRIGGER IF NOT EXISTS eligibility_snapshot_no_update_v2 BEFORE UPDATE ON clinical_eligibility_snapshot_v2
BEGIN SELECT RAISE(ABORT, 'eligibility snapshots are append-only'); END;
CREATE TRIGGER IF NOT EXISTS eligibility_snapshot_no_delete_v2 BEFORE DELETE ON clinical_eligibility_snapshot_v2
BEGIN SELECT RAISE(ABORT, 'eligibility snapshots are append-only'); END;
CREATE TRIGGER IF NOT EXISTS guardrail_evaluation_no_update_v2 BEFORE UPDATE ON guardrail_evaluation_v2
BEGIN SELECT RAISE(ABORT, 'guardrail evaluations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS guardrail_evaluation_no_delete_v2 BEFORE DELETE ON guardrail_evaluation_v2
BEGIN SELECT RAISE(ABORT, 'guardrail evaluations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS guardrail_result_no_update_v2 BEFORE UPDATE ON guardrail_rule_result_v2
BEGIN SELECT RAISE(ABORT, 'guardrail results are append-only'); END;
CREATE TRIGGER IF NOT EXISTS guardrail_result_no_delete_v2 BEFORE DELETE ON guardrail_rule_result_v2
BEGIN SELECT RAISE(ABORT, 'guardrail results are append-only'); END;
CREATE TRIGGER IF NOT EXISTS exception_approval_no_update_v2 BEFORE UPDATE ON guardrail_exception_approval_v2
BEGIN SELECT RAISE(ABORT, 'exception approvals are append-only'); END;
CREATE TRIGGER IF NOT EXISTS exception_approval_no_delete_v2 BEFORE DELETE ON guardrail_exception_approval_v2
BEGIN SELECT RAISE(ABORT, 'exception approvals are append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_decision_no_update_v2 BEFORE UPDATE ON clinical_safety_decision_v2
BEGIN SELECT RAISE(ABORT, 'clinical safety decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_decision_no_delete_v2 BEFORE DELETE ON clinical_safety_decision_v2
BEGIN SELECT RAISE(ABORT, 'clinical safety decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_decision_exception_no_update_v2 BEFORE UPDATE ON clinical_safety_decision_exception_v2
BEGIN SELECT RAISE(ABORT, 'decision exception evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_decision_exception_no_delete_v2 BEFORE DELETE ON clinical_safety_decision_exception_v2
BEGIN SELECT RAISE(ABORT, 'decision exception evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS break_glass_use_no_update_v2 BEFORE UPDATE ON break_glass_use_v2
BEGIN SELECT RAISE(ABORT, 'break-glass use is append-only'); END;
CREATE TRIGGER IF NOT EXISTS break_glass_use_no_delete_v2 BEFORE DELETE ON break_glass_use_v2
BEGIN SELECT RAISE(ABORT, 'break-glass use is append-only'); END;
CREATE TRIGGER IF NOT EXISTS break_glass_review_no_update_v2 BEFORE UPDATE ON break_glass_review_v2
BEGIN SELECT RAISE(ABORT, 'break-glass review is append-only'); END;
CREATE TRIGGER IF NOT EXISTS break_glass_review_no_delete_v2 BEFORE DELETE ON break_glass_review_v2
BEGIN SELECT RAISE(ABORT, 'break-glass review is append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_alert_no_update_v2 BEFORE UPDATE ON safety_alert_v2
BEGIN SELECT RAISE(ABORT, 'safety alerts are append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_alert_no_delete_v2 BEFORE DELETE ON safety_alert_v2
BEGIN SELECT RAISE(ABORT, 'safety alerts are append-only'); END;

CREATE INDEX IF NOT EXISTS idx_eligibility_staff_unit_time_v2
ON clinical_eligibility_snapshot_v2(staff_id,unit_id,captured_at,valid_until);
CREATE INDEX IF NOT EXISTS idx_guardrail_candidate_time_v2
ON guardrail_evaluation_v2(candidate_hash,staff_id,unit_id,evaluated_at,valid_until);
CREATE INDEX IF NOT EXISTS idx_exception_effective_v2
ON guardrail_exception_request_v2(rule_result_id,status,starts_at,expires_at);
CREATE INDEX IF NOT EXISTS idx_break_glass_user_time_v2
ON break_glass_event_v2(user_id,status,activated_at,expires_at);
CREATE INDEX IF NOT EXISTS idx_safety_decision_lookup_v2
ON clinical_safety_decision_v2(staff_id,permission_code,decided_at);
CREATE INDEX IF NOT EXISTS idx_safety_alert_type_time_v2
ON safety_alert_v2(alert_type,created_at);
