#!/usr/bin/env python3
"""Executable acceptance tests for the additive Part 2 SQLite schema."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def expect_integrity(conn: sqlite3.Connection, sql: str, params=()) -> None:
    try:
        conn.execute(sql, params)
    except sqlite3.IntegrityError:
        return
    raise AssertionError(f"Expected integrity failure: {sql}")


def base_database(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((ROOT / "org-directory" / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript((ROOT / "rbac" / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript((ROOT / "org-directory" / "um_schema.sql").read_text(encoding="utf-8"))
    conn.executescript((HERE / "identity_schema.sql").read_text(encoding="utf-8"))
    conn.executescript((HERE / "identity_schema.sql").read_text(encoding="utf-8"))
    return conn


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        conn = base_database(Path(tmp) / "identity-test.db")
        now = "2026-09-09T12:00:00Z"
        conn.execute("INSERT INTO facility (facility_code,name,status) VALUES ('AIGH','AIGH','ACTIVE')")
        facility = conn.execute("SELECT facility_id FROM facility").fetchone()[0]
        conn.execute(
            "INSERT INTO department (department_code,facility_id,name,department_type,status) VALUES ('GENS',?,'General','CLINICAL','ACTIVE')",
            (facility,),
        )
        conn.execute(
            "INSERT INTO department (department_code,facility_id,name,department_type,status) VALUES ('CRIT',?,'Critical','CLINICAL','ACTIVE')",
            (facility,),
        )
        gens, crit = [row[0] for row in conn.execute("SELECT department_id FROM department ORDER BY department_code DESC")]
        conn.execute("INSERT INTO unit_group (department_id,name,care_setting,status) VALUES (?,'Ward','INPATIENT','ACTIVE')", (gens,))
        group_id = conn.execute("SELECT unit_group_id FROM unit_group").fetchone()[0]
        conn.execute(
            """INSERT INTO nursing_unit
               (unit_code,department_id,unit_group_id,unit_name,unit_type,care_setting,capacity_class,resource_capacity,licensed_capacity,is_bedded,status)
               VALUES ('W3A',?,?, 'Ward 3A','WARD','INPATIENT','INPATIENT_LICENSED',10,10,1,'ACTIVE')""",
            (gens, group_id),
        )
        unit_id = conn.execute("SELECT unit_id FROM nursing_unit").fetchone()[0]
        conn.execute("INSERT INTO org_node (org_code,name,status) VALUES ('NURS','Nursing','ACTIVE')")
        org_id = conn.execute("SELECT org_node_id FROM org_node").fetchone()[0]
        conn.execute("INSERT INTO workforce_position (position_code,org_node_id,title,position_level) VALUES ('RN',?,'Staff Nurse','L6')", (org_id,))
        position_id = conn.execute("SELECT position_id FROM workforce_position").fetchone()[0]

        conn.execute(
            """INSERT INTO identity_account_v2
               (account_uuid,account_type,email,email_normalized,email_verified_at,auth_provider,external_subject,account_status,mfa_required,created_at,updated_at)
               VALUES ('acct-reviewer','HUMAN','reviewer@aigh.sa','reviewer@aigh.sa',?,'SSO','idp-reviewer','ACTIVE',1,?,?)""",
            (now, now, now),
        )
        reviewer = conn.execute("SELECT user_id FROM identity_account_v2 WHERE account_uuid='acct-reviewer'").fetchone()[0]
        conn.execute(
            """INSERT INTO identity_account_v2
               (account_uuid,account_type,email,email_normalized,email_verified_at,auth_provider,external_subject,account_status,mfa_required,created_at,updated_at)
               VALUES ('acct-nurse','HUMAN','Nurse@AIGH.sa','nurse@aigh.sa',?,'SSO','idp-nurse','ACTIVE',1,?,?)""",
            (now, now, now),
        )
        nurse_user = conn.execute("SELECT user_id FROM identity_account_v2 WHERE account_uuid='acct-nurse'").fetchone()[0]

        expect_integrity(
            conn,
            """INSERT INTO local_auth_credential_v2
               (user_id,encoded_hash,algorithm,parameter_version,changed_at)
               VALUES (?,'encoded','PBKDF2-SHA256','v1',?)""",
            (nurse_user, now),
        )

        expect_integrity(
            conn,
            """INSERT INTO identity_account_v2
               (account_uuid,email,email_normalized,email_verified_at,auth_provider,external_subject,account_status,created_at,updated_at)
               VALUES ('bad-email','user@aigh.sa','UPPER@AIGH.SA',?,'SSO','bad-email-subject','ACTIVE',?,?)""",
            (now, now, now),
        )
        expect_integrity(
            conn,
            """INSERT INTO identity_account_v2
               (account_uuid,auth_provider,external_subject,account_status,created_at,updated_at)
               VALUES ('active-human-no-email','SSO','no-email-subject','ACTIVE',?,?)""",
            (now, now),
        )
        expect_integrity(
            conn,
            """INSERT INTO identity_account_v2
               (account_uuid,auth_provider,account_status,created_at,updated_at)
               VALUES ('bad-sso','SSO','ACTIVE',?,?)""",
            (now, now),
        )
        expect_integrity(
            conn,
            """INSERT INTO identity_account_v2
               (account_uuid,email,email_normalized,email_verified_at,auth_provider,external_subject,account_status,created_at,updated_at)
               VALUES ('duplicate-email','nurse@aigh.sa','nurse@aigh.sa',?,'SSO','new-subject','ACTIVE',?,?)""",
            (now, now, now),
        )

        conn.execute(
            """INSERT INTO staff_member_v2
               (staff_uuid,employee_number,display_name,source_system,source_updated_at,record_status,is_demo)
               VALUES ('staff-nurse','E-100','Test Nurse','HRIS',?,'ACTIVE',0)""",
            (now,),
        )
        staff = conn.execute("SELECT staff_id FROM staff_member_v2").fetchone()[0]
        conn.execute(
            "INSERT INTO identity_staff_link_v2 (user_id,staff_id,linked_at,linked_by_user_id,verification_method) VALUES (?,?,?,?, 'AUTHORITATIVE_KEY')",
            (nurse_user, staff, now, reviewer),
        )
        expect_integrity(
            conn,
            "INSERT INTO identity_staff_link_v2 (user_id,staff_id,linked_at,linked_by_user_id,verification_method) VALUES (?,?,?,?, 'AUTHORITATIVE_KEY')",
            (reviewer, staff, now, reviewer),
        )

        conn.execute(
            """INSERT INTO employment_assignment_v2
               (staff_id,position_id,department_id,unit_id,fte,assignment_type,employment_status,effective_from,recorded_at)
               VALUES (?,?,?,?,1.0,'PRIMARY','ACTIVE',?,?)""",
            (staff, position_id, gens, unit_id, now, now),
        )
        expect_integrity(
            conn,
            """INSERT INTO employment_assignment_v2
               (staff_id,position_id,department_id,unit_id,fte,assignment_type,employment_status,effective_from,recorded_at)
               VALUES (?,?,?,?,1.0,'PRIMARY','ACTIVE',?,?)""",
            (staff, position_id, gens, unit_id, "2026-10-01T00:00:00Z", now),
        )
        expect_integrity(
            conn,
            """INSERT INTO employment_assignment_v2
               (staff_id,position_id,department_id,unit_id,fte,assignment_type,employment_status,effective_from,recorded_at)
               VALUES (?,?,?,?,1.0,'PRIMARY','ACTIVE',?,?)""",
            (staff, position_id, crit, unit_id, now, now),
        )

        expect_integrity(
            conn,
            """INSERT INTO professional_credential_v2
               (staff_id,credential_type,credential_number,issuing_authority,issue_date,expiry_date,verification_status,submitted_by_user_id,submitted_at,verified_by_user_id,verified_at,source_checked_at)
               VALUES (?,'RN_LICENSE','RN-1','SCFHS','2026-01-01','2027-01-01','VERIFIED',?,?,?, ?,?)""",
            (staff, nurse_user, now, nurse_user, now, now),
        )
        conn.execute(
            """INSERT INTO professional_credential_v2
               (staff_id,credential_type,credential_number,issuing_authority,issue_date,expiry_date,verification_status,submitted_by_user_id,submitted_at,verified_by_user_id,verified_at,source_checked_at)
               VALUES (?,'RN_LICENSE','RN-1','SCFHS','2026-01-01','2027-01-01','VERIFIED',?,?,?, ?,?)""",
            (staff, nurse_user, now, reviewer, now, now),
        )

        conn.execute(
            """INSERT INTO identity_session_v2
               (session_id,token_hash,user_id,auth_version,assurance_level,issued_at,last_seen_at,expires_at)
               VALUES ('session-1','hash-1',?,1,'AAL2',?,?,?)""",
            (nurse_user, now, now, "2026-09-09T20:00:00Z"),
        )
        expect_integrity(
            conn,
            """INSERT INTO identity_session_v2
               (session_id,token_hash,user_id,auth_version,assurance_level,issued_at,last_seen_at,expires_at)
               VALUES ('session-stale','hash-stale',?,2,'AAL2',?,?,?)""",
            (nurse_user, now, now, "2026-09-09T20:00:00Z"),
        )
        conn.execute("UPDATE identity_account_v2 SET account_status='DISABLED' WHERE user_id=?", (nurse_user,))
        expect_integrity(
            conn,
            """INSERT INTO identity_session_v2
               (session_id,token_hash,user_id,auth_version,assurance_level,issued_at,last_seen_at,expires_at)
               VALUES ('session-disabled','hash-disabled',?,1,'AAL2',?,?,?)""",
            (nurse_user, now, now, "2026-09-09T20:00:00Z"),
        )
        conn.execute("UPDATE identity_account_v2 SET account_status='ACTIVE' WHERE user_id=?", (nurse_user,))
        expect_integrity(
            conn,
            """INSERT INTO identity_session_v2
               (session_id,token_hash,user_id,auth_version,assurance_level,issued_at,last_seen_at,expires_at)
               VALUES ('session-2','hash-2',?,1,'AAL2',?,?,?)""",
            (nurse_user, now, now, "2026-09-09T11:00:00Z"),
        )

        conn.execute(
            """INSERT INTO authentication_event_v2
               (event_uuid,user_id,occurred_at,event_type,outcome,auth_provider,assurance_level,correlation_id)
               VALUES ('auth-event-1',? ,?,'LOGIN_SUCCESS','SUCCESS','SSO','AAL2','corr-1')""",
            (nurse_user, now),
        )
        expect_integrity(conn, "UPDATE authentication_event_v2 SET outcome='INFO' WHERE event_uuid='auth-event-1'")
        expect_integrity(conn, "DELETE FROM authentication_event_v2 WHERE event_uuid='auth-event-1'")

        conn.execute(
            """INSERT INTO identity_lifecycle_event_v2
               (event_uuid,user_id,staff_id,occurred_at,event_type,actor_user_id,source_system,correlation_id)
               VALUES ('life-event-1',?,?,?,'ACCOUNT_LINKED',?,'HNWMS','corr-2')""",
            (nurse_user, staff, now, reviewer),
        )
        expect_integrity(conn, "DELETE FROM identity_lifecycle_event_v2 WHERE event_uuid='life-event-1'")

        conn.commit()
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert not fk_errors, fk_errors
        existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for required in {
            "identity_account_v2", "staff_member_v2", "identity_staff_link_v2",
            "local_auth_credential_v2", "employment_assignment_v2",
            "professional_credential_v2", "identity_session_v2",
            "authentication_event_v2", "identity_lifecycle_event_v2",
            "identity_reconciliation_issue_v2",
        }:
            assert required in existing
        conn.close()

    print("Part 2 schema idempotency: PASS")
    print("Part 2 identity uniqueness and provider constraints: PASS")
    print("Part 2 one-to-one account/staff linkage: PASS")
    print("Part 2 unit/department integrity: PASS")
    print("Part 2 primary-assignment overlap prevention: PASS")
    print("Part 2 independent credential verification: PASS")
    print("Part 2 local-credential provider restriction: PASS")
    print("Part 2 session lifetime and auth-version constraints: PASS")
    print("Part 2 append-only event controls: PASS")
    print("Part 2 foreign-key validation: PASS")


if __name__ == "__main__":
    main()
