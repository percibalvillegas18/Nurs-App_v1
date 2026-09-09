#!/usr/bin/env python3
"""Executable Part 4 clinical-safety acceptance tests."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "rbac-v2" / "part-3-authorization"))

from engine_v2 import RbacV2Engine  # noqa: E402
from safety_engine import ClinicalSafetyEngine  # noqa: E402

NOW = "2026-09-09T12:00:00Z"
START = "2026-09-09T00:00:00Z"
END = "2026-09-10T00:00:00Z"


def expect_integrity(conn: sqlite3.Connection, sql: str, params=()) -> None:
    try:
        conn.execute(sql, params)
    except sqlite3.IntegrityError:
        return
    raise AssertionError(f"Expected integrity failure: {sql}")


def add_account(conn: sqlite3.Connection, name: str, account_type: str = "HUMAN") -> int:
    if account_type == "SERVICE":
        conn.execute(
            """INSERT INTO identity_account_v2
               (account_uuid,account_type,auth_provider,external_subject,account_status,
                mfa_required,created_at,updated_at)
               VALUES (?,'SERVICE','SSO',?,'ACTIVE',1,?,?)""",
            (name, f"svc-{name}", NOW, NOW),
        )
    else:
        email = f"{name}@aigh.sa"
        conn.execute(
            """INSERT INTO identity_account_v2
               (account_uuid,account_type,email,email_normalized,email_verified_at,
                auth_provider,external_subject,account_status,mfa_required,created_at,updated_at)
               VALUES (?,'HUMAN',?,?,?,'SSO',?,'ACTIVE',1,?,?)""",
            (name, email, email, NOW, f"idp-{name}", NOW, NOW),
        )
    return conn.execute("SELECT user_id FROM identity_account_v2 WHERE account_uuid=?", (name,)).fetchone()[0]


def add_staff(conn: sqlite3.Connection, name: str, employee_number: str) -> int:
    conn.execute(
        """INSERT INTO staff_member_v2
           (staff_uuid,employee_number,display_name,source_system,source_updated_at,record_status,is_demo)
           VALUES (?,?,?,'HRIS',?,'ACTIVE',0)""",
        (name, employee_number, name, NOW),
    )
    return conn.execute("SELECT staff_id FROM staff_member_v2 WHERE staff_uuid=?", (name,)).fetchone()[0]


def link(conn: sqlite3.Connection, user_id: int, staff_id: int, reviewer: int) -> None:
    conn.execute(
        """INSERT INTO identity_staff_link_v2
           (user_id,staff_id,linked_at,linked_by_user_id,verification_method)
           VALUES (?,?,?,?,'AUTHORITATIVE_KEY')""",
        (user_id, staff_id, NOW, reviewer),
    )


def add_grant(conn: sqlite3.Connection, tag: str, user_id: int, role_id: int,
              scope_id: int, policy_id: int, requester: int, approver: int,
              activator: int) -> int:
    conn.execute(
        """INSERT INTO access_grant_request_v2
           (request_uuid,user_id,role_id,scope_id,requested_by_user_id,requested_at,
            requested_from,requested_to,reason_code,justification,requires_dual_control,
            approved_by_user_id,decided_at,decision_reason,status)
           VALUES (?,?,?,?,?,?,?,?,?,'test grant',1,?,?,'approved','APPROVED')""",
        (f"req-{tag}", user_id, role_id, scope_id, requester, NOW, START, END,
         "TEST", approver, NOW),
    )
    request_id = conn.execute("SELECT request_id FROM access_grant_request_v2 WHERE request_uuid=?", (f"req-{tag}",)).fetchone()[0]
    conn.execute(
        """INSERT INTO access_grant_v2
           (grant_uuid,policy_id,request_id,user_id,role_id,scope_id,requested_by_user_id,
            approved_by_user_id,activated_by_user_id,effective_from,effective_to,
            reason_code,justification,requires_dual_control,status,activated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1,'ACTIVE',?)""",
        (f"grant-{tag}", policy_id, request_id, user_id, role_id, scope_id,
         requester, approver, activator, START, END, "TEST", "test grant", NOW),
    )
    return conn.execute("SELECT grant_id FROM access_grant_v2 WHERE grant_uuid=?", (f"grant-{tag}",)).fetchone()[0]


def eligibility(conn: sqlite3.Connection, tag: str, staff_id: int, unit_id: int,
                *, worker: str = "EMPLOYEE", license_state: str = "PASS",
                source: str = "AVAILABLE", captured: str = "2026-09-09T10:00:00Z",
                valid_until: str = "2026-09-09T18:00:00Z") -> int:
    conn.execute(
        """INSERT INTO clinical_eligibility_snapshot_v2
           (snapshot_uuid,staff_id,unit_id,worker_type,employment_state,license_state,
            credential_state,competency_state,training_state,unit_authorization_state,
            occupational_state,shift_context_state,source_state,captured_at,valid_until,
            evidence_version,created_by_service)
           VALUES (?,?,?,?,'PASS',?,'PASS','PASS','PASS','PASS','PASS','PASS',?,?,?,'E1','test-adapter')""",
        (tag, staff_id, unit_id, worker, license_state, source, captured, valid_until),
    )
    return conn.execute("SELECT eligibility_snapshot_id FROM clinical_eligibility_snapshot_v2 WHERE snapshot_uuid=?", (tag,)).fetchone()[0]


def guardrail_eval(conn: sqlite3.Connection, tag: str, safety_policy_id: int,
                   staff_id: int, unit_id: int, candidate: str,
                   results: list[tuple[int, str, str, str]], declared: str) -> tuple[int, list[int]]:
    conn.execute(
        """INSERT INTO guardrail_evaluation_v2
           (evaluation_uuid,safety_policy_id,target_type,target_reference,candidate_hash,
            staff_id,unit_id,ruleset_version,evaluated_at,valid_until,source_state,status,
            declared_verdict,evaluator_version)
           VALUES (?,?,'SHIFT',?,?,?,?,'RULESET-TEST-1',?,'2026-09-09T18:00:00Z',
                   'AVAILABLE','COMPLETE',?,'test-1')""",
        (f"eval-{tag}", safety_policy_id, f"shift-{tag}", candidate, staff_id, unit_id, NOW, declared),
    )
    evaluation_id = conn.execute("SELECT guardrail_evaluation_id FROM guardrail_evaluation_v2 WHERE evaluation_uuid=?", (f"eval-{tag}",)).fetchone()[0]
    result_ids = []
    for adapter_id, code, result, verdict in results:
        conn.execute(
            """INSERT INTO guardrail_rule_result_v2
               (guardrail_evaluation_id,rule_adapter_id,external_rule_code,result,
                effective_verdict,message)
               VALUES (?,?,?,?,?,'test result')""",
            (evaluation_id, adapter_id, code, result, verdict),
        )
        result_ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    return evaluation_id, result_ids


def build(path: Path) -> tuple[sqlite3.Connection, dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    for script in (
        ROOT / "org-directory" / "schema.sql",
        ROOT / "rbac" / "schema.sql",
        ROOT / "org-directory" / "um_schema.sql",
        ROOT / "rbac-v2" / "part-2-identity" / "identity_schema.sql",
        ROOT / "rbac-v2" / "part-3-authorization" / "authorization_schema.sql",
        HERE / "clinical_safety_schema.sql",
        HERE / "clinical_safety_schema.sql",
    ):
        conn.executescript(script.read_text(encoding="utf-8"))

    conn.execute("INSERT INTO facility(facility_code,name,status) VALUES('AIGH','AIGH','ACTIVE')")
    facility = conn.execute("SELECT facility_id FROM facility").fetchone()[0]
    conn.execute("INSERT INTO department(department_code,facility_id,name,department_type,status) VALUES('CRIT',?,'Critical','CLINICAL','ACTIVE')", (facility,))
    department = conn.execute("SELECT department_id FROM department").fetchone()[0]
    conn.execute("INSERT INTO unit_group(department_id,name,care_setting,status) VALUES(?,'ICU','CRITICAL','ACTIVE')", (department,))
    group_id = conn.execute("SELECT unit_group_id FROM unit_group").fetchone()[0]
    conn.execute("""INSERT INTO nursing_unit
        (unit_code,department_id,unit_group_id,unit_name,unit_type,care_setting,
         capacity_class,resource_capacity,licensed_capacity,is_bedded,status)
        VALUES('ICU-MAIN',?,?,'ICU Main','ICU','CRITICAL','INPATIENT_LICENSED',10,10,1,'ACTIVE')""", (department, group_id))
    unit = conn.execute("SELECT unit_id FROM nursing_unit").fetchone()[0]

    users = {name: add_account(conn, name) for name in (
        "requester", "approver", "activator", "reviewer", "nurse", "expired",
        "stale", "agency", "nogrant",
    )}
    users["service"] = add_account(conn, "service", "SERVICE")
    staff = {name: add_staff(conn, name, f"E-{i:03d}") for i, name in enumerate(
        ("nurse", "expired", "stale", "agency", "nogrant"), start=1
    )}
    for name in staff:
        link(conn, users[name], staff[name], users["reviewer"])

    conn.execute("INSERT INTO authorization_policy_v2(version_code,status,notes) VALUES('AUTH-P4-TEST','DRAFT','test')")
    auth_policy = conn.execute("SELECT policy_id FROM authorization_policy_v2").fetchone()[0]
    permission_defs = [
        ("BED_CONTROL", "Clinical bed control", 1),
        ("LICENSE_REMEDIATION", "License remediation", 0),
        ("GUARDRAIL_EXCEPTION_APPROVE", "Guardrail approval", 0),
        ("BREAK_GLASS_REVIEW", "Break-glass review", 0),
        ("CREDENTIAL_VERIFY", "Credential verification", 0),
    ]
    for code, desc, part4 in permission_defs:
        conn.execute(
            """INSERT INTO authorization_permission_v2
               (policy_id,perm_code,module,description,risk_class,requires_mfa,
                requires_part4,delegable,status)
               VALUES (?,?,'Safety',?,'CRITICAL',1,?,0,'ACTIVE')""",
            (auth_policy, code, desc, part4),
        )
    perms = {r["perm_code"]: r["permission_id"] for r in conn.execute("SELECT * FROM authorization_permission_v2")}
    role_defs = {
        "CLINICAL": ["BED_CONTROL"], "REMEDIATION": ["LICENSE_REMEDIATION"],
        "EXCEPTION_APPROVER": ["GUARDRAIL_EXCEPTION_APPROVE"],
        "BG_REVIEWER": ["BREAK_GLASS_REVIEW"],
    }
    for code, codes in role_defs.items():
        conn.execute("INSERT INTO authorization_role_v2(policy_id,role_code,title,risk_class,status) VALUES(?,?,?,'PRIVILEGED','ACTIVE')", (auth_policy, code, code))
        role_id = conn.execute("SELECT role_id FROM authorization_role_v2 WHERE role_code=?", (code,)).fetchone()[0]
        for perm_code in codes:
            conn.execute("INSERT INTO authorization_role_permission_v2(policy_id,role_id,permission_id) VALUES(?,?,?)", (auth_policy, role_id, perms[perm_code]))
    roles = {r["role_code"]: r["role_id"] for r in conn.execute("SELECT * FROM authorization_role_v2")}
    conn.execute("INSERT INTO authorization_scope_v2(scope_uuid,scope_type,unit_id,status,created_at) VALUES('scope-icu','UNIT',?,'ACTIVE',?)", (unit, NOW))
    scope = conn.execute("SELECT scope_id FROM authorization_scope_v2").fetchone()[0]

    conn.execute(
        """INSERT INTO clinical_safety_policy_v2
           (version_code,authorization_policy_id,compliance_ruleset_version,status,
            authorization_decision_ttl_seconds,max_break_glass_seconds,review_sla_seconds)
           VALUES('SAFETY-P4-TEST',?,'RULESET-TEST-1','DRAFT',60,3600,86400)""",
        (auth_policy,),
    )
    safety_policy = conn.execute("SELECT safety_policy_id FROM clinical_safety_policy_v2").fetchone()[0]
    for code, eligibility_required, guardrails_required, remediation in (
        ("BED_CONTROL", 1, 1, 0),
        ("LICENSE_REMEDIATION", 0, 0, 1),
    ):
        conn.execute(
            """INSERT INTO safety_permission_profile_v2
               (safety_policy_id,authorization_policy_id,permission_id,requires_eligibility,
                requires_guardrails,allows_remediation,status)
               VALUES (?,?,?,?,?,?,'ACTIVE')""",
            (safety_policy, auth_policy, perms[code], eligibility_required, guardrails_required, remediation),
        )
    for code, domain, exception_allowed in (
        ("CBA-STAFF-001", "STAFFING", 1),
        ("CBA-SAFE-001", "PATIENT_SAFETY", 0),
    ):
        conn.execute(
            """INSERT INTO guardrail_rule_adapter_v2
               (safety_policy_id,external_rule_code,external_ruleset_version,rule_domain,
                default_effect,exception_allowed,owner_role,status)
               VALUES (?,?,'RULESET-TEST-1',?,'BLOCK',?,'DON and Quality','ACTIVE')""",
            (safety_policy, code, domain, exception_allowed),
        )
    adapters = {r["external_rule_code"]: r["rule_adapter_id"] for r in conn.execute("SELECT * FROM guardrail_rule_adapter_v2")}
    conn.execute("INSERT INTO break_glass_bundle_v2(bundle_code,safety_policy_id,title,clinical_bundle,max_duration_seconds,status) VALUES('CLINICAL-UNIT',?,'Clinical unit emergency',1,3600,'DRAFT')", (safety_policy,))
    bundle = conn.execute("SELECT bundle_id FROM break_glass_bundle_v2").fetchone()[0]
    conn.execute("INSERT INTO break_glass_bundle_permission_v2(bundle_id,permission_id) VALUES(?,?)", (bundle, perms["BED_CONTROL"]))
    expect_integrity(conn, "INSERT INTO break_glass_bundle_permission_v2(bundle_id,permission_id) VALUES(?,?)", (bundle, perms["CREDENTIAL_VERIFY"]))
    conn.execute("UPDATE break_glass_bundle_v2 SET status='APPROVED',approved_by_user_id=?,approved_at=? WHERE bundle_id=?", (users["approver"], NOW, bundle))
    conn.execute("UPDATE authorization_policy_v2 SET status='ACTIVE',effective_from=?,approved_by_user_id=?,approved_at=?,published_at=? WHERE policy_id=?", (START, users["approver"], NOW, NOW, auth_policy))
    conn.execute("UPDATE clinical_safety_policy_v2 SET status='ACTIVE',effective_from=?,approved_by_user_id=?,approved_at=?,published_at=? WHERE safety_policy_id=?", (START, users["approver"], NOW, NOW, safety_policy))

    for name in ("nurse", "expired", "stale", "agency"):
        for role_code in ("CLINICAL", "REMEDIATION"):
            add_grant(conn, f"{name}-{role_code}", users[name], roles[role_code], scope,
                      auth_policy, users["requester"], users["approver"], users["activator"])
    add_grant(conn, "approver-ex", users["approver"], roles["EXCEPTION_APPROVER"], scope,
              auth_policy, users["requester"], users["reviewer"], users["activator"])
    add_grant(conn, "reviewer-bg", users["reviewer"], roles["BG_REVIEWER"], scope,
              auth_policy, users["requester"], users["approver"], users["activator"])
    conn.commit()
    return conn, {"users": users, "staff": staff, "unit": unit, "scope": scope,
                  "auth_policy": auth_policy, "safety_policy": safety_policy,
                  "perms": perms, "roles": roles, "adapters": adapters, "bundle": bundle}


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        conn, x = build(Path(tmp) / "part4.db")
        auth_engine = RbacV2Engine(conn)
        safety = ClinicalSafetyEngine(conn)
        users, staff = x["users"], x["staff"]

        eligibility(conn, "elig-nurse", staff["nurse"], x["unit"])
        eligibility(conn, "elig-expired", staff["expired"], x["unit"], license_state="FAIL")
        eligibility(conn, "elig-stale", staff["stale"], x["unit"], valid_until="2026-09-09T11:00:00Z")
        eligibility(conn, "elig-agency", staff["agency"], x["unit"], worker="AGENCY")
        eligibility(conn, "elig-nogrant", staff["nogrant"], x["unit"])

        staff_rule = x["adapters"]["CBA-STAFF-001"]
        safety_rule = x["adapters"]["CBA-SAFE-001"]
        guardrail_eval(conn, "pass", x["safety_policy"], staff["nurse"], x["unit"], "cand-pass", [(staff_rule, "CBA-STAFF-001", "PASS", "ALLOW")], "ALLOW")
        guardrail_eval(conn, "warn", x["safety_policy"], staff["nurse"], x["unit"], "cand-warn", [(staff_rule, "CBA-STAFF-001", "WARN", "WARN")], "WARN")
        _, block_results = guardrail_eval(conn, "block", x["safety_policy"], staff["nurse"], x["unit"], "cand-block", [(staff_rule, "CBA-STAFF-001", "FAIL", "BLOCK")], "BLOCK")
        _, two_results = guardrail_eval(conn, "two", x["safety_policy"], staff["nurse"], x["unit"], "cand-two", [(staff_rule, "CBA-STAFF-001", "FAIL", "BLOCK"), (safety_rule, "CBA-SAFE-001", "FAIL", "BLOCK")], "BLOCK")
        guardrail_eval(conn, "mismatch", x["safety_policy"], staff["nurse"], x["unit"], "cand-mismatch", [(staff_rule, "CBA-STAFF-001", "FAIL", "BLOCK")], "ALLOW")
        guardrail_eval(conn, "agency-pass", x["safety_policy"], staff["agency"], x["unit"], "cand-agency", [(staff_rule, "CBA-STAFF-001", "PASS", "ALLOW")], "ALLOW")
        guardrail_eval(conn, "expired-pass", x["safety_policy"], staff["expired"], x["unit"], "cand-expired", [(staff_rule, "CBA-STAFF-001", "PASS", "ALLOW")], "ALLOW")
        guardrail_eval(conn, "stale-pass", x["safety_policy"], staff["stale"], x["unit"], "cand-stale", [(staff_rule, "CBA-STAFF-001", "PASS", "ALLOW")], "ALLOW")
        guardrail_eval(conn, "nogrant-pass", x["safety_policy"], staff["nogrant"], x["unit"], "cand-nogrant", [(staff_rule, "CBA-STAFF-001", "PASS", "ALLOW")], "ALLOW")
        guardrail_eval(conn, "nogrant-block", x["safety_policy"], staff["nogrant"], x["unit"], "cand-bg-block", [(staff_rule, "CBA-STAFF-001", "FAIL", "BLOCK")], "BLOCK")

        def auth(user: str, permission: str, tag: str) -> str:
            decision = auth_engine.evaluate(account_uuid=user, permission_code=permission,
                resource_type="UNIT", resource_code="ICU-MAIN", policy_version="AUTH-P4-TEST",
                request_id=f"auth-{tag}", at=NOW)
            assert decision["allow"], decision
            return decision["decision_id"]

        nurse_auth = auth("nurse", "BED_CONTROL", "nurse-bed")
        result = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-pass", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-pass", at=NOW, authorization_decision_id=nurse_auth)
        assert result["allow"] and result["reason_code"] == "SAFETY_CONTROLS_PASS"
        stale_auth_decision = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-pass", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-auth-too-old", at="2026-09-09T12:02:00Z", authorization_decision_id=nurse_auth)
        assert stale_auth_decision["reason_code"] == "AUTHORIZATION_REQUIRED"
        warn = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-warn", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-warn", at=NOW, authorization_decision_id=nurse_auth)
        assert warn["result"] == "WARN" and not warn["allow"]
        blocked = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-block", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-block", at=NOW, authorization_decision_id=nurse_auth)
        assert blocked["reason_code"] == "GUARDRAIL_BLOCK"
        mismatch = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-mismatch", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-mismatch", at=NOW, authorization_decision_id=nurse_auth)
        assert mismatch["reason_code"] == "GUARDRAIL_VERDICT_MISMATCH"

        expired_auth = auth("expired", "BED_CONTROL", "expired-bed")
        expired = safety.evaluate(account_uuid="expired", staff_uuid="expired", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-expired", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-expired", at=NOW, authorization_decision_id=expired_auth)
        assert expired["reason_code"] == "ELIGIBILITY_BLOCK"
        remediation_auth = auth("expired", "LICENSE_REMEDIATION", "expired-remediation")
        remediation = safety.evaluate(account_uuid="expired", staff_uuid="expired", permission_code="LICENSE_REMEDIATION",
            unit_code="ICU-MAIN", candidate_hash="remediation-1", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-remediation", at=NOW, authorization_decision_id=remediation_auth)
        assert remediation["allow"]

        stale_auth = auth("stale", "BED_CONTROL", "stale-bed")
        stale = safety.evaluate(account_uuid="stale", staff_uuid="stale", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-stale", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-stale", at=NOW, authorization_decision_id=stale_auth)
        assert stale["reason_code"] == "ELIGIBILITY_SOURCE_UNAVAILABLE_OR_STALE"
        agency_auth = auth("agency", "BED_CONTROL", "agency-bed")
        agency = safety.evaluate(account_uuid="agency", staff_uuid="agency", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-agency", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-agency", at=NOW, authorization_decision_id=agency_auth)
        assert agency["allow"]
        eligibility(conn, "elig-agency-fail", staff["agency"], x["unit"], worker="AGENCY",
                    license_state="FAIL", captured="2026-09-09T11:30:00Z")
        guardrail_eval(conn, "agency-fail", x["safety_policy"], staff["agency"], x["unit"],
                       "cand-agency-fail", [(staff_rule, "CBA-STAFF-001", "PASS", "ALLOW")], "ALLOW")
        agency_failed = safety.evaluate(account_uuid="agency", staff_uuid="agency", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-agency-fail", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-agency-fail", at=NOW, authorization_decision_id=agency_auth)
        assert agency_failed["reason_code"] == "ELIGIBILITY_BLOCK"

        # Exact, independently authorized exception for one rule result.
        conn.execute(
            """INSERT INTO guardrail_exception_request_v2
               (exception_uuid,rule_result_id,candidate_hash,staff_id,unit_id,requested_by_user_id,
                requested_at,starts_at,expires_at,reason_code,justification,risk_assessment,
                mitigation,corrective_action,required_approvals,status)
               VALUES ('ex-block',?,'cand-block',?,?,?,?,'2026-09-09T11:00:00Z',
                       '2026-09-09T13:00:00Z','SHORTAGE','Emergency coverage request',
                       'Documented clinical risk','Additional supervisor present',
                       'Obtain replacement immediately',1,'PENDING')""",
            (block_results[0], staff["nurse"], x["unit"], users["nurse"], NOW),
        )
        exception_id = conn.execute("SELECT exception_id FROM guardrail_exception_request_v2 WHERE exception_uuid='ex-block'").fetchone()[0]
        approve_auth = auth("approver", "GUARDRAIL_EXCEPTION_APPROVE", "exception-approve")
        expect_integrity(conn, """INSERT INTO guardrail_exception_approval_v2
            (exception_id,approval_step,approver_user_id,authorization_decision_id,decision,decision_note,decided_at)
            VALUES (?,1,?,?,'APPROVE','self','2026-09-09T11:30:00Z')""", (exception_id, users["nurse"], approve_auth))
        conn.execute("""INSERT INTO guardrail_exception_approval_v2
            (exception_id,approval_step,approver_user_id,authorization_decision_id,decision,decision_note,decided_at)
            VALUES (?,1,?,?,'APPROVE','approved','2026-09-09T11:30:00Z')""", (exception_id, users["approver"], approve_auth))
        conn.execute("UPDATE guardrail_exception_request_v2 SET status='APPROVED' WHERE exception_id=?", (exception_id,))
        excepted = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-block", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-excepted", at=NOW, authorization_decision_id=nurse_auth)
        assert excepted["allow"] and excepted["exception_ids"] == [exception_id]
        expect_integrity(conn, """INSERT INTO guardrail_exception_request_v2
            (exception_uuid,rule_result_id,candidate_hash,staff_id,unit_id,requested_by_user_id,
             requested_at,starts_at,expires_at,reason_code,justification,risk_assessment,
             mitigation,corrective_action,status)
            VALUES('ex-wrong',?,'wrong',?,?,?,?,'2026-09-09T11:00:00Z','2026-09-09T13:00:00Z',
             'TEST','Long justification','Long risk assessment','Long mitigation plan','Long corrective action','PENDING')""",
            (block_results[0], staff["nurse"], x["unit"], users["nurse"], NOW))
        expect_integrity(conn, """INSERT INTO guardrail_exception_request_v2
            (exception_uuid,rule_result_id,candidate_hash,staff_id,unit_id,requested_by_user_id,
             requested_at,starts_at,expires_at,reason_code,justification,risk_assessment,
             mitigation,corrective_action,status)
            VALUES('ex-hard',?,'cand-two',?,?,?,?,'2026-09-09T11:00:00Z','2026-09-09T13:00:00Z',
             'TEST','Long justification','Long risk assessment','Long mitigation plan','Long corrective action','PENDING')""",
            (two_results[1], staff["nurse"], x["unit"], users["nurse"], NOW))

        # One exception cannot erase a second blocking rule.
        conn.execute("""INSERT INTO guardrail_exception_request_v2
            (exception_uuid,rule_result_id,candidate_hash,staff_id,unit_id,requested_by_user_id,
             requested_at,starts_at,expires_at,reason_code,justification,risk_assessment,
             mitigation,corrective_action,required_approvals,status)
            VALUES('ex-two',?,'cand-two',?,?,?,?,'2026-09-09T11:00:00Z','2026-09-09T13:00:00Z',
             'TEST','Long justification','Long risk assessment','Long mitigation plan','Long corrective action',1,'PENDING')""",
            (two_results[0], staff["nurse"], x["unit"], users["nurse"], NOW))
        ex_two = conn.execute("SELECT exception_id FROM guardrail_exception_request_v2 WHERE exception_uuid='ex-two'").fetchone()[0]
        conn.execute("""INSERT INTO guardrail_exception_approval_v2
            (exception_id,approval_step,approver_user_id,authorization_decision_id,decision,decision_note,decided_at)
            VALUES(?,1,?,?,'APPROVE','approved',?)""", (ex_two, users["approver"], approve_auth, NOW))
        conn.execute("UPDATE guardrail_exception_request_v2 SET status='APPROVED' WHERE exception_id=?", (ex_two,))
        still_blocked = safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-two", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-two", at=NOW, authorization_decision_id=nurse_auth)
        assert still_blocked["reason_code"] == "GUARDRAIL_BLOCK" and still_blocked["exception_ids"] == [ex_two]

        # Guardrail exception cannot create authorization.
        noauth = safety.evaluate(account_uuid="nogrant", staff_uuid="nogrant", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-nogrant", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-noauth", at=NOW)
        assert noauth["reason_code"] == "AUTHORIZATION_REQUIRED"

        expect_integrity(conn, "DELETE FROM break_glass_bundle_permission_v2 WHERE bundle_id=?", (x["bundle"],))
        expect_integrity(conn, "UPDATE guardrail_rule_adapter_v2 SET exception_allowed=0 WHERE rule_adapter_id=?", (staff_rule,))

        # Event-scoped break-glass: validated eligibility, exact unit, step-up, bounded time.
        conn.execute("""INSERT INTO break_glass_event_v2
            (event_uuid,safety_policy_id,bundle_id,user_id,staff_id,scope_id,target_unit_id,
             requested_at,expires_at,review_due_at,authentication_assurance,reason_code,
             justification,incident_reference,status)
            VALUES('bg-valid',?,?,?,?,?,?,?,'2026-09-09T13:00:00Z','2026-09-10T13:00:00Z',
                   'STEP_UP','PATIENT_SAFETY','Immediate patient safety action','INC-1','REQUESTED')""",
            (x["safety_policy"], x["bundle"], users["nogrant"], staff["nogrant"], x["scope"], x["unit"], NOW))
        assert safety.validate_break_glass_activation(event_uuid="bg-valid", unit_code="ICU-MAIN", at=NOW)["allow"]
        conn.execute("UPDATE break_glass_event_v2 SET activated_at=?,status='ACTIVE' WHERE event_uuid='bg-valid'", (NOW,))
        bg = safety.evaluate(account_uuid="nogrant", staff_uuid="nogrant", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-nogrant", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-bg", at=NOW, break_glass_event_uuid="bg-valid")
        assert bg["allow"] and bg["break_glass_event_id"] is not None
        bg_block = safety.evaluate(account_uuid="nogrant", staff_uuid="nogrant", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-bg-block", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-bg-block", at=NOW, break_glass_event_uuid="bg-valid")
        assert bg_block["reason_code"] == "GUARDRAIL_BLOCK"
        assert conn.execute("SELECT COUNT(*) FROM safety_alert_v2 WHERE alert_type='BREAK_GLASS_ACTIVATED'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM break_glass_use_v2 WHERE break_glass_event_id=?", (bg["break_glass_event_id"],)).fetchone()[0] == 2

        # Service identities and excessive windows cannot activate.
        expect_integrity(conn, """INSERT INTO break_glass_event_v2
            (event_uuid,safety_policy_id,bundle_id,user_id,staff_id,scope_id,target_unit_id,
             requested_at,activated_at,expires_at,review_due_at,authentication_assurance,
             reason_code,justification,incident_reference,status)
            VALUES('bg-service',?,?,?,?,?,?,?,?,'2026-09-09T13:00:00Z','2026-09-10T13:00:00Z',
                   'STEP_UP','PATIENT_SAFETY','Immediate patient safety action','INC-S','ACTIVE')""",
            (x["safety_policy"], x["bundle"], users["service"], staff["nogrant"], x["scope"], x["unit"], NOW, NOW))
        expect_integrity(conn, """INSERT INTO break_glass_event_v2
            (event_uuid,safety_policy_id,bundle_id,user_id,staff_id,scope_id,target_unit_id,
             requested_at,activated_at,expires_at,review_due_at,authentication_assurance,
             reason_code,justification,incident_reference,status)
            VALUES('bg-overlong',?,?,?,?,?,?,?,?,'2026-09-09T14:01:00Z','2026-09-10T14:01:00Z',
                   'STEP_UP','PATIENT_SAFETY','Immediate patient safety action','INC-L','ACTIVE')""",
            (x["safety_policy"], x["bundle"], users["nogrant"], staff["nogrant"], x["scope"], x["unit"], NOW, NOW))

        conn.execute("""INSERT INTO break_glass_event_v2
            (event_uuid,safety_policy_id,bundle_id,user_id,staff_id,scope_id,target_unit_id,
             requested_at,expires_at,review_due_at,authentication_assurance,reason_code,
             justification,incident_reference,status)
            VALUES('bg-expired-license',?,?,?,?,?,?,?,'2026-09-09T13:00:00Z','2026-09-10T13:00:00Z',
                   'STEP_UP','PATIENT_SAFETY','Immediate patient safety action','INC-2','REQUESTED')""",
            (x["safety_policy"], x["bundle"], users["expired"], staff["expired"], x["scope"], x["unit"], NOW))
        assert safety.validate_break_glass_activation(event_uuid="bg-expired-license", unit_code="ICU-MAIN", at=NOW)["reason_code"] == "BREAK_GLASS_ELIGIBILITY_BLOCK"
        expect_integrity(conn, "UPDATE break_glass_event_v2 SET activated_at=?,status='ACTIVE' WHERE event_uuid='bg-expired-license'", (NOW,))

        expired_bg = safety.evaluate(account_uuid="nogrant", staff_uuid="nogrant", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-nogrant", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-bg-expired", at="2026-09-09T14:00:00Z", break_glass_event_uuid="bg-valid")
        assert expired_bg["reason_code"] == "AUTHORIZATION_REQUIRED"
        conn.execute("""UPDATE break_glass_event_v2
            SET status='REVOKED',revoked_at='2026-09-09T12:30:00Z',revoked_by_user_id=?,revocation_reason='incident ended'
            WHERE event_uuid='bg-valid'""", (users["approver"],))
        revoked_bg = safety.evaluate(account_uuid="nogrant", staff_uuid="nogrant", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-nogrant", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-bg-revoked", at="2026-09-09T12:30:00Z", break_glass_event_uuid="bg-valid")
        assert revoked_bg["reason_code"] == "AUTHORIZATION_REQUIRED"

        review_auth = auth("reviewer", "BREAK_GLASS_REVIEW", "bg-review")
        expect_integrity(conn, """INSERT INTO break_glass_review_v2
            (break_glass_event_id,reviewer_user_id,authorization_decision_id,decision,notes,reviewed_at)
            VALUES(?,?,?,'CLOSE','self review',?)""", (bg["break_glass_event_id"], users["nogrant"], review_auth, NOW))
        conn.execute("""INSERT INTO break_glass_review_v2
            (break_glass_event_id,reviewer_user_id,authorization_decision_id,decision,notes,reviewed_at)
            VALUES(?,?,?,'CLOSE','independent review',?)""", (bg["break_glass_event_id"], users["reviewer"], review_auth, NOW))

        # Append-only evidence and idempotency.
        expect_integrity(conn, "UPDATE clinical_eligibility_snapshot_v2 SET license_state='PASS' WHERE snapshot_uuid='elig-expired'")
        expect_integrity(conn, "DELETE FROM guardrail_rule_result_v2 WHERE rule_result_id=?", (block_results[0],))
        expect_integrity(conn, "UPDATE clinical_safety_decision_v2 SET result='ALLOW' WHERE request_id='safe-block'")
        expect_integrity(conn, "DELETE FROM break_glass_use_v2 WHERE break_glass_event_id=?", (bg["break_glass_event_id"],))
        expect_integrity(conn, "DELETE FROM safety_alert_v2 WHERE alert_type='BREAK_GLASS_ACTIVATED'")
        assert safety.evaluate(account_uuid="nurse", staff_uuid="nurse", permission_code="BED_CONTROL",
            unit_code="ICU-MAIN", candidate_hash="cand-pass", safety_policy_version="SAFETY-P4-TEST",
            request_id="safe-pass", at=NOW, authorization_decision_id=nurse_auth)["safety_decision_id"] == result["safety_decision_id"]

        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        conn.commit()
        conn.close()

    print("Part 4 schema idempotency and foreign keys: PASS")
    print("Part 4 eligibility failure, staleness, remediation, and agency parity: PASS")
    print("Part 4 strictest guardrail and fingerprint binding: PASS")
    print("Part 4 independent exact-rule exception controls: PASS")
    print("Part 4 authorization/exception separation: PASS")
    print("Part 4 break-glass identity, step-up, scope, duration, and eligibility: PASS")
    print("Part 4 break-glass/guardrail separation and independent review: PASS")
    print("Part 4 append-only evidence and idempotent decisions: PASS")


if __name__ == "__main__":
    main()
