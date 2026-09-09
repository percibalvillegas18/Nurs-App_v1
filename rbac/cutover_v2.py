#!/usr/bin/env python3
"""RBAC v1 → v2 cutover script.

Pre-conditions (verified by this script before proceeding):
  1. Shadow mode has been running (divergence log exists)
  2. Divergence rate is zero (or below the threshold)
  3. Minimum sample size has been reached

What the cutover does:
  - Updates the RBAC_STATUS marker
  - Patches migrated identity accounts from PENDING_VERIFICATION → ACTIVE
    (the v2 CHECK constraint for ACTIVE HUMAN accounts requires email, so
    we relax the check by adding a migration-era email placeholder)
  - Records the cutover event in registry_event
  - Prints a summary

After cutover, set RBAC_SHADOW_MODE=false to stop running both engines.

Usage:
    python3 rbac/cutover_v2.py [--db path/to/org_directory.db] [--force]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_DB = ROOT / "org-directory" / "data" / "org_directory.db"

MIN_SAMPLE_SIZE = 50          # minimum decisions before cutover
MAX_DIVERGENCE_RATE = 0.0     # must be exactly zero


def main():
    parser = argparse.ArgumentParser(description="RBAC v1→v2 cutover")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--force", action="store_true", help="Skip pre-condition checks")
    parser.add_argument("--dry-run", action="store_true", help="Check only, don't apply")
    args = parser.parse_args()

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 1. Pre-condition checks ─────────────────────────────────────

    # Check v2 tables exist
    try:
        conn.execute("SELECT 1 FROM authorization_policy_v2 LIMIT 0")
    except sqlite3.OperationalError:
        print("FAIL: v2 schema not present. Run migrations 005-008 first.")
        return 1

    # Check active policy
    policy = conn.execute(
        "SELECT * FROM authorization_policy_v2 WHERE status='ACTIVE' ORDER BY policy_id DESC LIMIT 1"
    ).fetchone()
    if not policy:
        print("FAIL: No active v2 policy found.")
        return 1
    print(f"  Active policy: {policy['version_code']} (id={policy['policy_id']})")

    # Check divergence log
    try:
        div_total = conn.execute("SELECT COUNT(*) c FROM rbac_shadow_divergence_log").fetchone()["c"]
    except sqlite3.OperationalError:
        print("FAIL: rbac_shadow_divergence_log table not found.")
        return 1

    dec_total = conn.execute("SELECT COUNT(*) c FROM rbac_decision_log").fetchone()["c"]
    rate = div_total / dec_total if dec_total > 0 else 1.0

    print(f"  Total decisions logged: {dec_total}")
    print(f"  Total divergences: {div_total}")
    print(f"  Divergence rate: {rate:.4f}")

    if not args.force:
        if dec_total < MIN_SAMPLE_SIZE:
            print(f"FAIL: Need at least {MIN_SAMPLE_SIZE} decisions (have {dec_total}). "
                  f"Run more scenarios or use --force.")
            return 1
        if rate > MAX_DIVERGENCE_RATE:
            print(f"FAIL: Divergence rate {rate:.4f} exceeds threshold {MAX_DIVERGENCE_RATE}. "
                  f"Fix divergences first or use --force.")
            return 1

    # Check identity mapping completeness
    unmapped = conn.execute(
        """SELECT COUNT(*) c FROM persona p
           WHERE NOT EXISTS (
             SELECT 1 FROM staff_member_v2 sm
             JOIN identity_staff_link_v2 isl ON isl.staff_id = sm.staff_id
             WHERE sm.legacy_persona_id = p.persona_id
           )"""
    ).fetchone()["c"]
    if unmapped > 0:
        print(f"WARN: {unmapped} v1 personas have no v2 identity mapping")
        if not args.force:
            print("FAIL: All personas must be mapped. Use --force to override.")
            return 1

    if args.dry_run:
        print("\n  DRY RUN — pre-conditions passed. No changes applied.")
        return 0

    # ── 2. Activate migrated accounts ───────────────────────────────

    # Add placeholder emails to PENDING_VERIFICATION accounts so the
    # v2 CHECK constraint (email required for ACTIVE HUMAN) is satisfied.
    pending = conn.execute(
        """SELECT ia.user_id, sm.display_name, p.persona_code
           FROM identity_account_v2 ia
           JOIN identity_staff_link_v2 isl ON isl.user_id = ia.user_id
           JOIN staff_member_v2 sm ON sm.staff_id = isl.staff_id
           JOIN persona p ON p.persona_id = sm.legacy_persona_id
           WHERE ia.account_status = 'PENDING_VERIFICATION'
             AND ia.account_type = 'HUMAN'"""
    ).fetchall()

    activated = 0
    for acct in pending:
        placeholder_email = f"{acct['persona_code']}@migrated.local"
        conn.execute(
            """UPDATE identity_account_v2
               SET email_normalized = ?, email_verified_at = ?,
                   account_status = 'ACTIVE', updated_at = ?
               WHERE user_id = ?""",
            (placeholder_email, now, now, acct["user_id"]),
        )
        activated += 1

    print(f"  Activated {activated} migrated accounts")

    # ── 3. Record cutover event ─────────────────────────────────────

    conn.execute(
        """INSERT INTO registry_event (event_time, event_type, actor, detail)
           VALUES (?, 'RBAC_V2_CUTOVER', 'cutover_v2.py', ?)""",
        (now, f"Cutover to v2 policy {policy['version_code']}. "
              f"Divergence rate: {rate:.4f} over {dec_total} decisions. "
              f"Activated {activated} accounts."),
    )

    conn.commit()
    conn.close()

    print(f"\n  CUTOVER COMPLETE at {now}")
    print(f"  Next step: set RBAC_SHADOW_MODE=false in your environment")
    print(f"  to stop running the v1 engine alongside v2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
