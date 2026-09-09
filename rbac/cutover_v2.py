#!/usr/bin/env python3
"""RBAC v1 → v2 cutover script.

Pre-conditions (verified by this script before proceeding):
  1. Shadow mode has been running (divergence log exists)
  2. Divergence rate is zero (or below the threshold)
  3. Minimum sample size has been reached

What the cutover does:
  - Verifies that policy, shadow evidence, mappings, and real verified
    identities meet the cutover gate
  - Does not activate pending/demo/legacy-local accounts and does not create
    placeholder email addresses
  - Records the cutover event in registry_event
  - Prints a summary

This script does not switch runtime enforcement. After an approved cutover,
use the deployment's explicit v2-enforced mode and verify transaction-bound
PDP middleware; `RBAC_SHADOW_MODE=false` currently selects the v1 prototype.

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
    parser.add_argument("--force", action="store_true", help="Skip sample/divergence checks only; identity gates remain mandatory")
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

    # Check identity mapping completeness. This is never bypassed by
    # --force: a cutover must not turn demo slots into active human accounts.
    unmapped = conn.execute(
        """SELECT COUNT(*) c FROM persona p
           WHERE NOT EXISTS (
             SELECT 1 FROM staff_member_v2 sm
             JOIN identity_staff_link_v2 isl ON isl.staff_id = sm.staff_id
             WHERE sm.legacy_persona_id = p.persona_id
           )"""
    ).fetchone()["c"]
    if unmapped > 0:
        print(f"FAIL: {unmapped} v1 personas have no v2 identity mapping")
        return 1

    identity_debt = conn.execute(
        """SELECT COUNT(*) c FROM identity_account_v2
           WHERE account_type='HUMAN'
             AND (account_status <> 'ACTIVE'
                  OR auth_provider IN ('LEGACY_LOCAL','LOCAL')
                  OR email_verified_at IS NULL)"""
    ).fetchone()["c"]
    if identity_debt > 0:
        print(f"FAIL: {identity_debt} human identity accounts are not real, verified production identities")
        print("      Complete HR/SSO/MFA migration and verification before cutover.")
        return 1

    if args.dry_run:
        print("\n  DRY RUN — pre-conditions passed. No changes applied.")
        return 0

    # ── 2. No identity activation is performed here ─────────────────
    # Account lifecycle belongs to the approved HR/SSO migration. In
    # particular, do not manufacture @migrated.local addresses or mark them
    # as verified merely to satisfy a database CHECK constraint.
    activated = 0

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

    print(f"\n  CUTOVER GATE COMPLETE at {now}")
    print("  No runtime mode was changed. Deploy the separately approved")
    print("  v2-enforced mode only after transaction-bound PDP checks are live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
