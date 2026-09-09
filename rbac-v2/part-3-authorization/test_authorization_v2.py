#!/usr/bin/env python3
"""Executable Part 3 schema and engine acceptance tests."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from engine_v2 import RbacV2Engine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NOW = "2026-09-09T12:00:00Z"
START = "2026-01-01T00:00:00Z"
END = "2027-01-01T00:00:00Z"


def expect_integrity(conn: sqlite3.Connection, sql: str, params=()) -> None:
    try:
        conn.execute(sql, params)
    except sqlite3.IntegrityError:
        return
    raise AssertionError(f"Expected integrity failure: {sql}")


def account(conn: sqlite3.Connection, name: str) -> int:
    conn.execute(
        """INSERT INTO identity_account_v2
           (account_uuid,account_type,email,email_normalized,email_verified_at,
            auth_provider,external_subject,account_status,mfa_required,created_at,updated_at)
           VALUES (?,'HUMAN',?,?,?,'SSO',?,'ACTIVE',1,?,?)""",
        (name, f"{name}@aigh.sa", f"{name}@aigh.sa", NOW, f"idp-{name}", NOW, NOW),
    )
    return conn.execute("SELECT user_id FROM identity_account_v2 WHERE account_uuid=?", (name,)).fetchone()[0]


def grant(
    conn: sqlite3.Connection, *, tag: str, user_id: int, role_id: int, scope_id: int,
    requester: int, approver: int, activator: int, policy_id: int,
    start: str = START, end: str | None = END, dual: int = 0,
) -> int:
    conn.execute(
        """INSERT INTO access_grant_request_v2
           (request_uuid,user_id,role_id,scope_id,requested_by_user_id,requested_at,
            requested_from,requested_to,reason_code,justification,requires_dual_control,
            approved_by_user_id,decided_at,decision_reason,status)
           VALUES (?,?,?,?,?,?,?,?,?,'test fixture',?,?,?,'approved for test','APPROVED')""",
        (f"req-{tag}", user_id, role_id, scope_id, requester, NOW, start, end,
         "TEST", dual, approver, NOW),
    )
    request_id = conn.execute(
        "SELECT request_id FROM access_grant_request_v2 WHERE request_uuid=?", (f"req-{tag}",)
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO access_grant_v2
           (grant_uuid,policy_id,request_id,user_id,role_id,scope_id,
            requested_by_user_id,approved_by_user_id,activated_by_user_id,
            effective_from,effective_to,reason_code,justification,
            requires_dual_control,status,activated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ACTIVE',?)""",
        (f"grant-{tag}", policy_id, request_id, user_id, role_id, scope_id,
         requester, approver, activator, start, end, "TEST", "test fixture", dual, NOW),
    )
    return conn.execute("SELECT grant_id FROM access_grant_v2 WHERE grant_uuid=?", (f"grant-{tag}",)).fetchone()[0]


def build_database(path: Path) -> tuple[sqlite3.Connection, dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for script in (
        ROOT / "org-directory" / "schema.sql",
        ROOT / "rbac" / "schema.sql",
        ROOT / "org-directory" / "um_schema.sql",
        ROOT / "rbac-v2" / "part-2-identity" / "identity_schema.sql",
        HERE / "authorization_schema.sql",
        HERE / "authorization_schema.sql",
    ):
        conn.executescript(script.read_text(encoding="utf-8"))

    conn.execute("INSERT INTO facility (facility_code,name,status) VALUES ('AIGH','AIGH','ACTIVE')")
    conn.execute("INSERT INTO facility (facility_code,name,status) VALUES ('BIGH','BIGH','ACTIVE')")
    aigh = conn.execute("SELECT facility_id FROM facility WHERE facility_code='AIGH'").fetchone()[0]
    bigh = conn.execute("SELECT facility_id FROM facility WHERE facility_code='BIGH'").fetchone()[0]
    conn.execute("INSERT INTO department (department_code,facility_id,name,department_type,status) VALUES ('CRIT',?,'Critical','CLINICAL','ACTIVE')", (aigh,))
    conn.execute("INSERT INTO department (department_code,facility_id,name,department_type,status) VALUES ('BCRT',?,'B Critical','CLINICAL','ACTIVE')", (bigh,))
    crit = conn.execute("SELECT department_id FROM department WHERE department_code='CRIT'").fetchone()[0]
    bcrit = conn.execute("SELECT department_id FROM department WHERE department_code='BCRT'").fetchone()[0]
    conn.execute("INSERT INTO unit_group (department_id,name,care_setting,status) VALUES (?,'ICU','CRITICAL','ACTIVE')", (crit,))
    conn.execute("INSERT INTO unit_group (department_id,name,care_setting,status) VALUES (?,'B ICU','CRITICAL','ACTIVE')", (bcrit,))
    group_a = conn.execute("SELECT unit_group_id FROM unit_group WHERE department_id=?", (crit,)).fetchone()[0]
    group_b = conn.execute("SELECT unit_group_id FROM unit_group WHERE department_id=?", (bcrit,)).fetchone()[0]
    conn.execute("""INSERT INTO nursing_unit
        (unit_code,department_id,unit_group_id,unit_name,unit_type,care_setting,
         capacity_class,resource_capacity,licensed_capacity,is_bedded,status)
        VALUES ('ICU-MAIN',?,?,'ICU Main','ICU','CRITICAL','INPATIENT_LICENSED',10,10,1,'ACTIVE')""", (crit, group_a))
    conn.execute("""INSERT INTO nursing_unit
        (unit_code,department_id,unit_group_id,unit_name,unit_type,care_setting,
         capacity_class,resource_capacity,licensed_capacity,is_bedded,status)
        VALUES ('B-ICU',?,?,'B ICU','ICU','CRITICAL','INPATIENT_LICENSED',10,10,1,'ACTIVE')""", (bcrit, group_b))
    unit_a = conn.execute("SELECT unit_id FROM nursing_unit WHERE unit_code='ICU-MAIN'").fetchone()[0]
    unit_b = conn.execute("SELECT unit_id FROM nursing_unit WHERE unit_code='B-ICU'").fetchone()[0]

    ids = {name: account(conn, name) for name in (
        "requester", "approver", "activator", "charge", "scheduler",
        "manager", "delegate", "conflicted", "care-user",
    )}

    conn.execute(
        """INSERT INTO authorization_policy_v2
           (version_code,status,effective_from,approved_by_user_id,approved_at,published_at,notes)
           VALUES ('RBAC-V2-DRAFT-1','DRAFT',NULL,NULL,NULL,NULL,'test-only draft')""",
    )
    policy = conn.execute("SELECT policy_id FROM authorization_policy_v2").fetchone()[0]
    permissions = [
        ("BED_CONTROL", "Bed", "Place or release physical bed", "CRITICAL", 1, 1, 1),
        ("SCHED_PUBLISH", "Schedule", "Publish roster", "HIGH", 1, 1, 0),
        ("BED_BLOCK", "Bed", "Block bed", "HIGH", 1, 1, 1),
        ("ORG_READ", "Org", "Read directory", "STANDARD", 0, 0, 1),
        ("CARE_ASSIGNMENT_WRITE", "Clinical", "Assign care", "CRITICAL", 1, 1, 0),
        ("AUDIT_ADMIN", "Audit", "Administer audit policy", "CRITICAL", 1, 0, 0),
    ]
    conn.executemany(
        """INSERT INTO authorization_permission_v2
           (policy_id,perm_code,module,description,risk_class,requires_mfa,requires_part4,delegable)
           VALUES (?,?,?,?,?,?,?,?)""",
        [(policy, *p) for p in permissions],
    )
    perm = {row["perm_code"]: row["permission_id"] for row in conn.execute("SELECT * FROM authorization_permission_v2")}
    roles = {
        "CHARGE": ["BED_CONTROL", "BED_BLOCK", "ORG_READ"],
        "SCHEDULER": ["SCHED_PUBLISH", "ORG_READ"],
        "UNIT_MGR": ["BED_BLOCK", "ORG_READ"],
        "CARE": ["CARE_ASSIGNMENT_WRITE", "ORG_READ"],
        "BED_COORD": ["BED_CONTROL", "BED_BLOCK", "ORG_READ"],
        "AUDIT_ADMIN": ["AUDIT_ADMIN", "ORG_READ"],
    }
    for code in roles:
        conn.execute(
            "INSERT INTO authorization_role_v2 (policy_id,role_code,title,risk_class,status) VALUES (?,?,?,'ELEVATED','ACTIVE')",
            (policy, code, code),
        )
    role = {row["role_code"]: row["role_id"] for row in conn.execute("SELECT * FROM authorization_role_v2")}
    for code, codes in roles.items():
        conn.executemany(
            "INSERT INTO authorization_role_permission_v2 (policy_id,role_id,permission_id) VALUES (?,?,?)",
            [(policy, role[code], perm[p]) for p in codes],
        )

    for code, first, second in (
        ("SOD-BED-SCHED-001", "BED_CONTROL", "SCHED_PUBLISH"),
        ("SOD-BED-CARE-TEST", "BED_CONTROL", "CARE_ASSIGNMENT_WRITE"),
    ):
        low, high = sorted((perm[first], perm[second]))
        conn.execute(
            """INSERT INTO sod_rule_v2
               (policy_id,rule_code,permission_a_id,permission_b_id,overlap_mode,enforcement,accountable_owner,status)
               VALUES (?,?,?,?,'SAME_SCOPE_OR_CONTAINED','BLOCK','DON and Security','ACTIVE')""",
            (policy, code, low, high),
        )
    low, high = sorted((perm["BED_CONTROL"], perm["AUDIT_ADMIN"]))
    conn.execute(
        """INSERT INTO sod_rule_v2
           (policy_id,rule_code,permission_a_id,permission_b_id,overlap_mode,enforcement,accountable_owner,status)
           VALUES (?,?,?,?,'ANY_SCOPE','BLOCK','Internal Audit and Security','ACTIVE')""",
        (policy, "SOD-AUDIT-INDEPENDENCE-TEST", low, high),
    )

    conn.execute(
        """UPDATE authorization_policy_v2
           SET status='ACTIVE',effective_from=?,approved_by_user_id=?,approved_at=?,published_at=?
           WHERE policy_id=?""",
        (START, ids["approver"], NOW, NOW, policy),
    )

    scopes = [
        ("scope-aigh", "FACILITY", aigh, None, None),
        ("scope-bigh", "FACILITY", bigh, None, None),
        ("scope-crit", "DEPARTMENT", None, crit, None),
        ("scope-bcrit", "DEPARTMENT", None, bcrit, None),
        ("scope-icu", "UNIT", None, None, unit_a),
        ("scope-bicu", "UNIT", None, None, unit_b),
    ]
    conn.executemany(
        """INSERT INTO authorization_scope_v2
           (scope_uuid,scope_type,facility_id,department_id,unit_id,status,created_at)
           VALUES (?,?,?,?,?,'ACTIVE',?)""",
        [(*s, NOW) for s in scopes],
    )
    scope = {row["scope_uuid"]: row["scope_id"] for row in conn.execute("SELECT * FROM authorization_scope_v2")}
    conn.commit()
    return conn, {"ids": ids, "policy": policy, "perm": perm, "role": role, "scope": scope}


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        conn, x = build_database(Path(tmp) / "part3.db")
        ids, policy, role, scope = x["ids"], x["policy"], x["role"], x["scope"]
        engine = RbacV2Engine(conn)

        charge_grant = grant(
            conn, tag="charge", user_id=ids["charge"], role_id=role["CHARGE"],
            scope_id=scope["scope-icu"], requester=ids["requester"],
            approver=ids["approver"], activator=ids["activator"], policy_id=policy, dual=1,
        )
        manager_grant = grant(
            conn, tag="manager", user_id=ids["manager"], role_id=role["UNIT_MGR"],
            scope_id=scope["scope-crit"], requester=ids["requester"],
            approver=ids["approver"], activator=ids["activator"], policy_id=policy,
        )
        grant(
            conn, tag="scheduler", user_id=ids["scheduler"], role_id=role["SCHEDULER"],
            scope_id=scope["scope-crit"], requester=ids["requester"],
            approver=ids["approver"], activator=ids["activator"], policy_id=policy,
        )
        grant(
            conn, tag="facility", user_id=ids["care-user"], role_id=role["BED_COORD"],
            scope_id=scope["scope-aigh"], requester=ids["requester"],
            approver=ids["approver"], activator=ids["activator"], policy_id=policy,
        )

        allow = engine.evaluate(account_uuid="charge", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-allow", at=NOW)
        assert allow["allow"] and allow["matched_grant_id"] == charge_grant and allow["requires_part4"]
        assert engine.evaluate(account_uuid="charge", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="B-ICU", policy_version="RBAC-V2-DRAFT-1", request_id="eval-cross-unit", at=NOW)["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"
        assert engine.evaluate(account_uuid="care-user", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="B-ICU", policy_version="RBAC-V2-DRAFT-1", request_id="eval-cross-facility", at=NOW)["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"
        assert engine.evaluate(account_uuid="manager", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-manager-bed", at=NOW)["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"
        assert engine.evaluate(account_uuid="scheduler", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-scheduler-bed", at=NOW)["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"

        assert engine.evaluate(account_uuid="missing", permission_code="ORG_READ", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-unknown-user", at=NOW)["reason_code"] == "ACCOUNT_NOT_ACTIVE"
        assert engine.evaluate(account_uuid="charge", permission_code="MISSING", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-unknown-perm", at=NOW)["reason_code"] == "PERMISSION_UNKNOWN"
        assert engine.evaluate(account_uuid="charge", permission_code="ORG_READ", resource_type="WARD", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-unknown-type", at=NOW)["reason_code"] == "RESOURCE_NOT_ACTIVE"
        assert engine.evaluate(account_uuid="charge", permission_code="ORG_READ", resource_type="UNIT", resource_code="NOPE", policy_version="RBAC-V2-DRAFT-1", request_id="eval-unknown-resource", at=NOW)["reason_code"] == "RESOURCE_NOT_ACTIVE"
        assert engine.evaluate(account_uuid="charge", permission_code="ORG_READ", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="NOPE", request_id="eval-unknown-policy", at=NOW)["reason_code"] == "POLICY_NOT_ACTIVE"

        # Delegation: bounded permission, unit scope, and source-grant window.
        conn.execute(
            """INSERT INTO delegation_v2
               (delegation_uuid,policy_id,source_grant_id,delegator_user_id,delegate_user_id,
                scope_id,requested_by_user_id,approved_by_user_id,requested_at,decided_at,
                starts_at,expires_at,reason_code,justification,status)
               VALUES ('del-valid',?,?,?,?,?,?,?,?,?,?,?,?,?,'ACTIVE')""",
            (policy, manager_grant, ids["manager"], ids["delegate"], scope["scope-icu"],
             ids["manager"], ids["approver"], NOW, NOW, START, END, "LEAVE", "coverage"),
        )
        delegation = conn.execute("SELECT delegation_id FROM delegation_v2 WHERE delegation_uuid='del-valid'").fetchone()[0]
        conn.execute("INSERT INTO delegation_permission_v2 (delegation_id,permission_id) VALUES (?,?)", (delegation, x["perm"]["BED_BLOCK"]))
        delegated = engine.evaluate(account_uuid="delegate", permission_code="BED_BLOCK", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-delegated", at=NOW)
        assert delegated["allow"] and delegated["delegation_id"] == delegation and delegated["matched_grant_id"] == manager_grant
        assert engine.evaluate(account_uuid="delegate", permission_code="BED_BLOCK", resource_type="UNIT", resource_code="B-ICU", policy_version="RBAC-V2-DRAFT-1", request_id="eval-delegated-cross", at=NOW)["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"
        assert engine.evaluate(account_uuid="delegate", permission_code="BED_BLOCK", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-delegated-expired", at="2027-02-01T00:00:00Z")["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"

        expect_integrity(
            conn,
            """INSERT INTO delegation_v2
               (delegation_uuid,policy_id,source_grant_id,delegator_user_id,delegate_user_id,
                scope_id,requested_by_user_id,approved_by_user_id,requested_at,decided_at,
                starts_at,expires_at,reason_code,justification,status)
               VALUES ('del-cross',?,?,?,?,?,?,?,?,?,?,?,?,?,'ACTIVE')""",
            (policy, manager_grant, ids["manager"], ids["delegate"], scope["scope-bicu"],
             ids["manager"], ids["approver"], NOW, NOW, START, END, "LEAVE", "bad scope"),
        )
        expect_integrity(conn, "INSERT INTO delegation_permission_v2 (delegation_id,permission_id) VALUES (?,?)", (delegation, x["perm"]["SCHED_PUBLISH"]))
        expect_integrity(conn, "UPDATE delegation_v2 SET expires_at='2028-01-01T00:00:00Z' WHERE delegation_id=?", (delegation,))
        expect_integrity(conn, "DELETE FROM delegation_permission_v2 WHERE delegation_id=?", (delegation,))

        # Published policy catalogues and active grant cores are immutable.
        expect_integrity(conn, "UPDATE authorization_permission_v2 SET delegable=0 WHERE permission_id=?", (x["perm"]["BED_BLOCK"],))
        expect_integrity(conn, "UPDATE access_grant_v2 SET scope_id=? WHERE grant_id=?", (scope["scope-bicu"], manager_grant))

        # Self-approval and dual-control protections.
        expect_integrity(
            conn,
            """INSERT INTO access_grant_request_v2
               (request_uuid,user_id,role_id,scope_id,requested_by_user_id,requested_at,
                requested_from,reason_code,justification,approved_by_user_id,decided_at,decision_reason,status)
               VALUES ('req-self',?,?,?,?,?,'2026-01-01T00:00:00Z','TEST','bad',?,?,'bad','APPROVED')""",
            (ids["charge"], role["CHARGE"], scope["scope-icu"], ids["requester"], NOW, ids["requester"], NOW),
        )

        # Two applicable SoD rules must both be returned, not only the first.
        grant(conn, tag="conflict-bed", user_id=ids["conflicted"], role_id=role["CHARGE"], scope_id=scope["scope-icu"], requester=ids["requester"], approver=ids["approver"], activator=ids["activator"], policy_id=policy)
        grant(conn, tag="conflict-sched", user_id=ids["conflicted"], role_id=role["SCHEDULER"], scope_id=scope["scope-crit"], requester=ids["requester"], approver=ids["approver"], activator=ids["activator"], policy_id=policy)
        grant(conn, tag="conflict-care", user_id=ids["conflicted"], role_id=role["CARE"], scope_id=scope["scope-aigh"], requester=ids["requester"], approver=ids["approver"], activator=ids["activator"], policy_id=policy)
        grant(conn, tag="conflict-audit", user_id=ids["conflicted"], role_id=role["AUDIT_ADMIN"], scope_id=scope["scope-bigh"], requester=ids["requester"], approver=ids["approver"], activator=ids["activator"], policy_id=policy)
        conflict = engine.evaluate(account_uuid="conflicted", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-conflict", at=NOW)
        assert conflict["reason_code"] == "SOD_CONFLICT"
        assert conflict["sod_rule_ids"] == ["SOD-AUDIT-INDEPENDENCE-TEST", "SOD-BED-CARE-TEST", "SOD-BED-SCHED-001"]

        # Activation preview catches all conflicts before a grant is created.
        conn.execute(
            """INSERT INTO access_grant_request_v2
               (request_uuid,user_id,role_id,scope_id,requested_by_user_id,requested_at,
                requested_from,requested_to,reason_code,justification,requires_dual_control,
                approved_by_user_id,decided_at,decision_reason,status)
               VALUES ('req-preview',?,?,?,?,?,?,?,?,?,1,?,?,'approved','APPROVED')""",
            (ids["conflicted"], role["CHARGE"], scope["scope-icu"], ids["requester"], NOW,
             START, END, "TEST", "preview", ids["approver"], NOW),
        )
        preview = engine.validate_grant_activation(request_uuid="req-preview", activated_by_account_uuid="activator", at=NOW)
        assert not preview["allow"] and preview["sod_rule_ids"] == ["SOD-AUDIT-INDEPENDENCE-TEST", "SOD-BED-CARE-TEST", "SOD-BED-SCHED-001"]
        dual = engine.validate_grant_activation(request_uuid="req-preview", activated_by_account_uuid="approver", at=NOW)
        assert not dual["allow"] and dual["reason_code"] == "DUAL_CONTROL_REQUIRED"

        # Revocation is honored immediately and prior request IDs are idempotent.
        conn.execute("UPDATE access_grant_v2 SET status='REVOKED',revoked_at=?,revoked_by_user_id=?,revocation_reason='ended' WHERE grant_id=?", (NOW, ids["approver"], charge_grant))
        assert engine.evaluate(account_uuid="charge", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-revoked", at=NOW)["reason_code"] == "NO_EFFECTIVE_ENTITLEMENT"
        assert engine.evaluate(account_uuid="charge", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-allow", at=NOW)["decision_id"] == allow["decision_id"]
        reused = engine.evaluate(account_uuid="manager", permission_code="BED_CONTROL", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-allow", at=NOW)
        assert not reused["allow"] and reused["decision"] == "ERROR" and reused["reason_code"] == "REQUEST_ID_REUSE"

        # Decision evidence and linked SoD evidence cannot be rewritten or deleted.
        expect_integrity(conn, "UPDATE authorization_decision_v2 SET decision='ALLOW' WHERE request_id='eval-conflict'")
        expect_integrity(conn, "DELETE FROM authorization_decision_v2 WHERE request_id='eval-conflict'")
        decision_id = conflict["decision_id"]
        expect_integrity(conn, "DELETE FROM authorization_decision_sod_v2 WHERE decision_id=?", (decision_id,))
        conn.execute(
            """INSERT INTO authorization_lifecycle_event_v2
               (event_id,occurred_at,event_type,actor_user_id,grant_id,reason_code)
               VALUES ('life-1',?,'GRANT_REVOKED',?,?,'ENDED')""",
            (NOW, ids["approver"], charge_grant),
        )
        expect_integrity(conn, "DELETE FROM authorization_lifecycle_event_v2 WHERE event_id='life-1'")

        # Inactive authoritative resources deny even if an old scope/grant remains.
        conn.execute("UPDATE nursing_unit SET status='INACTIVE' WHERE unit_code='ICU-MAIN'")
        assert engine.evaluate(account_uuid="manager", permission_code="BED_BLOCK", resource_type="UNIT", resource_code="ICU-MAIN", policy_version="RBAC-V2-DRAFT-1", request_id="eval-inactive", at=NOW)["reason_code"] == "RESOURCE_NOT_ACTIVE"

        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        conn.commit()
        conn.close()

    print("Part 3 schema idempotency and foreign keys: PASS")
    print("Part 3 default-deny and inactive-resource behavior: PASS")
    print("Part 3 facility/department/unit containment: PASS")
    print("Part 3 role boundary checks: PASS")
    print("Part 3 grant approval, expiry, and revocation: PASS")
    print("Part 3 all-conflict SoD evaluation: PASS")
    print("Part 3 delegation permission/scope/time subset: PASS")
    print("Part 3 append-only and idempotent decisions: PASS")


if __name__ == "__main__":
    main()
