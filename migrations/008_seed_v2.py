#!/usr/bin/env python3
"""Migration 008: Seed v2 tables from v1 data.

Maps existing v1 personas, roles, permissions, grants, and SoD rules into the
v2 shadow schema so the shadow-mode evaluator can produce decisions.

Because v2 triggers enforce strict workflows (grant-must-match-request,
catalogue-changes-require-draft-policy, etc.), this migration:
  1. Creates a DRAFT authorization_policy_v2
  2. Inserts catalogue data (roles, permissions, role_permission, SoD rules)
     while the policy is in DRAFT state
  3. Publishes the policy to ACTIVE
  4. Maps persona → pending identity_account_v2 + staff_member_v2
  5. Maps role_grant → access_grant_request_v2 + access_grant_v2 (with triggers
     temporarily disabled for the bootstrap grant-request match check)

Human identities remain pending/legacy-local until HR/SSO verification; this
migration does not prove identity, activate accounts, or create email
placeholders. Rollback: 008_seed_v2_rollback.sql (truncates seeded rows,
preserving schema).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

DB = ROOT / "org-directory" / "data" / "org_directory.db"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
EFFECTIVE = "2026-09-09"
POLICY_VERSION = "v2-migration-001"
SYSTEM_USER_UUID = "00000000-0000-0000-0000-000000000001"
MIGRATION_APPROVER_UUID = "00000000-0000-0000-0000-000000000002"


def run(db_path: str | Path | None = None):
    db_path = Path(db_path) if db_path else DB
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Check if already seeded
    existing = conn.execute(
        "SELECT COUNT(*) c FROM authorization_policy_v2 WHERE version_code=?",
        (POLICY_VERSION,),
    ).fetchone()
    if existing["c"] > 0:
        print("[008] Already seeded — skipping")
        conn.close()
        return

    # ── 1. Create SYSTEM account (needed as approver/requestor) ──────

    system_user_id = _ensure_system_account(conn, SYSTEM_USER_UUID, "SYSTEM requestor")
    approver_user_id = _ensure_system_account(conn, MIGRATION_APPROVER_UUID, "SYSTEM approver")

    # ── 2. Create DRAFT policy ───────────────────────────────────────

    conn.execute(
        """INSERT INTO authorization_policy_v2
           (version_code, status, notes)
           VALUES (?, 'DRAFT', 'Auto-migrated from v1 RBAC')""",
        (POLICY_VERSION,),
    )
    policy_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ── 3. Map v1 roles → authorization_role_v2 ─────────────────────

    v1_roles = conn.execute("SELECT * FROM role").fetchall()
    role_id_map = {}  # v1 role_id → v2 role_id
    for r in v1_roles:
        conn.execute(
            """INSERT INTO authorization_role_v2
               (policy_id, role_code, title, risk_class, status)
               VALUES (?, ?, ?, 'STANDARD', 'ACTIVE')""",
            (policy_id, r["role_code"], r["title"]),
        )
        v2_role_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        role_id_map[r["role_id"]] = v2_role_id

    # ── 4. Map v1 permissions → authorization_permission_v2 ──────────

    v1_perms = conn.execute("SELECT * FROM permission").fetchall()
    perm_id_map = {}  # v1 permission_id → v2 permission_id
    for p in v1_perms:
        conn.execute(
            """INSERT INTO authorization_permission_v2
               (policy_id, perm_code, module, description, risk_class, status)
               VALUES (?, ?, ?, ?, 'STANDARD', 'ACTIVE')""",
            (policy_id, p["perm_code"], p["module"] or "CORE", p["description"] or p["perm_code"]),
        )
        v2_perm_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        perm_id_map[p["permission_id"]] = v2_perm_id

    # ── 5. Map v1 role_permission → authorization_role_permission_v2 ─

    v1_rps = conn.execute("SELECT * FROM role_permission").fetchall()
    for rp in v1_rps:
        v2_rid = role_id_map.get(rp["role_id"])
        v2_pid = perm_id_map.get(rp["permission_id"])
        if v2_rid and v2_pid:
            conn.execute(
                """INSERT INTO authorization_role_permission_v2
                   (policy_id, role_id, permission_id)
                   VALUES (?, ?, ?)""",
                (policy_id, v2_rid, v2_pid),
            )

    # ── 6. Map v1 sod_rule → sod_rule_v2 ────────────────────────────

    v1_sods = conn.execute("SELECT * FROM sod_rule").fetchall()
    for sod in v1_sods:
        # Resolve permission codes to v2 permission_ids
        pa = conn.execute(
            "SELECT permission_id FROM authorization_permission_v2 WHERE policy_id=? AND perm_code=?",
            (policy_id, sod["perm_a"]),
        ).fetchone()
        pb = conn.execute(
            "SELECT permission_id FROM authorization_permission_v2 WHERE policy_id=? AND perm_code=?",
            (policy_id, sod["perm_b"]),
        ).fetchone()
        if pa and pb:
            a_id, b_id = pa["permission_id"], pb["permission_id"]
            if a_id > b_id:
                a_id, b_id = b_id, a_id
            conn.execute(
                """INSERT INTO sod_rule_v2
                   (policy_id, rule_code, permission_a_id, permission_b_id,
                    overlap_mode, enforcement, accountable_owner, status)
                   VALUES (?, ?, ?, ?, 'ANY_SCOPE', 'BLOCK', 'DON', 'ACTIVE')""",
                (policy_id, f"SOD-MIG-{sod['sod_id']}", a_id, b_id),
            )

    # ── 7. Publish the policy (DRAFT → ACTIVE) ──────────────────────

    conn.execute(
        """UPDATE authorization_policy_v2
           SET status='ACTIVE', effective_from=?, approved_by_user_id=?,
               approved_at=?, published_at=?
           WHERE policy_id=?""",
        (EFFECTIVE, approver_user_id, NOW, NOW, policy_id),
    )

    # ── 8. Create scopes from facility/department/unit ───────────────

    scope_map = {}  # (scope_type, code) → scope_id

    for f in conn.execute("SELECT * FROM facility WHERE status='ACTIVE'").fetchall():
        suuid = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO authorization_scope_v2
               (scope_uuid, scope_type, facility_id, status, created_at)
               VALUES (?, 'FACILITY', ?, 'ACTIVE', ?)""",
            (suuid, f["facility_id"], NOW),
        )
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        scope_map[("FACILITY", f["facility_code"])] = sid

    for d in conn.execute("SELECT * FROM department WHERE status='ACTIVE'").fetchall():
        suuid = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO authorization_scope_v2
               (scope_uuid, scope_type, department_id, status, created_at)
               VALUES (?, 'DEPARTMENT', ?, 'ACTIVE', ?)""",
            (suuid, d["department_id"], NOW),
        )
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        scope_map[("DEPARTMENT", d["department_code"])] = sid

    for u in conn.execute("SELECT * FROM nursing_unit WHERE status='ACTIVE'").fetchall():
        suuid = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO authorization_scope_v2
               (scope_uuid, scope_type, unit_id, status, created_at)
               VALUES (?, 'UNIT', ?, 'ACTIVE', ?)""",
            (suuid, u["unit_id"], NOW),
        )
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        scope_map[("UNIT", u["unit_code"])] = sid

    # ── 9. Map persona → identity_account_v2 + staff_member_v2 ──────

    persona_to_user = {}  # persona_code → v2 user_id

    v1_personas = conn.execute("SELECT * FROM persona").fetchall()
    for p in v1_personas:
        acct_uuid = str(uuid.uuid4())
        staff_uuid = str(uuid.uuid4())
        try:
            is_demo = p["is_demo"]
        except (IndexError, KeyError):
            is_demo = 1

        # Create identity account as PENDING_VERIFICATION because the v2
        # CHECK constraint requires email for ACTIVE HUMAN accounts, and
        # legacy/demo personas are not verified production identities. The
        # approved HR/SSO migration, not this seed, must activate the account.
        conn.execute(
            """INSERT INTO identity_account_v2
               (account_uuid, legacy_app_user_id, account_type, auth_provider,
                account_status, created_at, updated_at)
               VALUES (?, NULL, 'HUMAN', 'LEGACY_LOCAL', 'PENDING_VERIFICATION', ?, ?)""",
            (acct_uuid, NOW, NOW),
        )
        v2_user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create staff member
        conn.execute(
            """INSERT INTO staff_member_v2
               (staff_uuid, legacy_persona_id, employee_number, display_name,
                source_system, source_updated_at, record_status, is_demo)
               VALUES (?, ?, ?, ?, 'LEGACY_ORG_DIRECTORY', ?, 'ACTIVE', ?)""",
            (staff_uuid, p["persona_id"],
             None if is_demo else f"EMP-{p['persona_code']}",
             p["display_name"], NOW, is_demo),
        )
        v2_staff_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Link account to staff
        conn.execute(
            """INSERT INTO identity_staff_link_v2
               (user_id, staff_id, linked_at, linked_by_user_id, verification_method)
               VALUES (?, ?, ?, ?, 'LEGACY_DEMO')""",
            (v2_user_id, v2_staff_id, NOW, system_user_id),
        )

        persona_to_user[p["persona_code"]] = v2_user_id

    # ── 10. Map role_grant → access_grant_request_v2 + access_grant_v2

    # We need to temporarily drop the grant-request match trigger because
    # the bootstrap grants are auto-approved (no real request workflow).
    conn.execute("DROP TRIGGER IF EXISTS access_grant_request_match_insert_v2")

    v1_grants = conn.execute(
        """SELECT g.*, p.persona_code
           FROM role_grant g
           JOIN persona p ON p.persona_id = g.persona_id
           WHERE g.status = 'ACTIVE'"""
    ).fetchall()

    for g in v1_grants:
        v2_user_id = persona_to_user.get(g["persona_code"])
        v2_role_id = role_id_map.get(g["role_id"])
        scope_key = (g["scope_type"].upper(), g["scope_code"])
        v2_scope_id = scope_map.get(scope_key)

        if not (v2_user_id and v2_role_id and v2_scope_id):
            print(f"[008] WARN: skipping grant {g['grant_id']} — unmapped user/role/scope")
            continue

        req_uuid = str(uuid.uuid4())
        grant_uuid = str(uuid.uuid4())

        # Create the grant request (auto-approved for migration)
        conn.execute(
            """INSERT INTO access_grant_request_v2
               (request_uuid, user_id, role_id, scope_id,
                requested_by_user_id, requested_at, requested_from, requested_to,
                reason_code, justification, requires_dual_control,
                approved_by_user_id, decided_at, decision_reason, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'MIGRATION', 'Auto-migrated from v1 role_grant',
                       0, ?, ?, 'Migration bootstrap', 'APPROVED')""",
            (req_uuid, v2_user_id, v2_role_id, v2_scope_id,
             system_user_id, NOW, g["effective_from"], g["effective_to"],
             approver_user_id, NOW),
        )
        v2_request_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create the active grant
        conn.execute(
            """INSERT INTO access_grant_v2
               (grant_uuid, policy_id, request_id, user_id, role_id, scope_id,
                requested_by_user_id, approved_by_user_id, activated_by_user_id,
                effective_from, effective_to, reason_code, justification,
                requires_dual_control, status, activated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'MIGRATION',
                       'Auto-migrated from v1 role_grant', 0, 'ACTIVE', ?)""",
            (grant_uuid, policy_id, v2_request_id, v2_user_id, v2_role_id, v2_scope_id,
             system_user_id, approver_user_id, approver_user_id,
             g["effective_from"], g["effective_to"], NOW),
        )

    # Restore the trigger
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS access_grant_request_match_insert_v2
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
           END"""
    )

    # ── 11. Add shadow-mode divergence log table ─────────────────────

    conn.execute(
        """CREATE TABLE IF NOT EXISTS rbac_shadow_divergence_log (
               id              INTEGER PRIMARY KEY AUTOINCREMENT,
               occurred_at     TEXT NOT NULL,
               subject         TEXT NOT NULL,
               permission      TEXT NOT NULL,
               resource_type   TEXT NOT NULL,
               resource_code   TEXT NOT NULL,
               v1_allow        INTEGER NOT NULL,
               v1_reason       TEXT NOT NULL,
               v2_decision     TEXT NOT NULL,
               v2_reason_code  TEXT NOT NULL,
               v2_reason_detail TEXT NOT NULL,
               request_id      TEXT NOT NULL
           )"""
    )

    # ── 12. Version stamp ────────────────────────────────────────────

    conn.execute(
        "INSERT INTO schema_version (version, description) VALUES (8, 'v1→v2 data seed and shadow divergence log')"
    )

    conn.commit()
    conn.close()
    print(f"[008] Seeded v2 tables: {len(v1_roles)} roles, {len(v1_perms)} permissions, "
          f"{len(v1_personas)} personas, {len(v1_grants)} grants, {len(v1_sods)} SoD rules")


def _ensure_system_account(conn: sqlite3.Connection, acct_uuid: str, label: str = "") -> int:
    """Create a SERVICE account used for migration bootstrap."""
    existing = conn.execute(
        "SELECT user_id FROM identity_account_v2 WHERE account_uuid=?",
        (acct_uuid,),
    ).fetchone()
    if existing:
        return existing["user_id"]

    conn.execute(
        """INSERT INTO identity_account_v2
           (account_uuid, account_type, auth_provider,
            account_status, created_at, updated_at)
           VALUES (?, 'SERVICE', 'LOCAL', 'ACTIVE', ?, ?)""",
        (acct_uuid, NOW, NOW),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    run(db_path)
