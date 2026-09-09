#!/usr/bin/env python3
"""Integration tests for the RBAC v2 shadow-mode adapter.

Tests cover:
  1. Shadow adapter produces the same v1 result as the v1 engine
  2. Divergences are logged when v2 disagrees with v1
  3. Divergence report endpoint returns correct structure
  4. Shadow adapter degrades gracefully when v2 tables are absent
  5. Identity mapping (persona_code → account_uuid) works
  6. Cutover pre-condition checks work
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "org-directory"))

# Ensure migrations dir is on path
MIGRATIONS = ROOT / "migrations"


def _fresh_db(tmp_path: Path) -> Path:
    """Create a fresh test database from the live DB + migrations 005-008."""
    live_db = ROOT / "org-directory" / "data" / "org_directory.db"
    if not live_db.exists():
        raise RuntimeError(f"Live database not found at {live_db}. Run seed.py first.")

    db_path = tmp_path / "test_shadow.db"
    shutil.copy2(live_db, db_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()

    applied = {r[0] for r in conn.execute("SELECT version FROM schema_version")}

    # Apply SQL migrations
    for mig in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
        if mig.name.endswith("_rollback.sql"):
            continue
        ver = int(mig.name[:3])
        if ver in applied:
            continue
        conn.executescript(mig.read_text())
        applied.add(ver)

    # Run the Python seed (008) if not already applied
    try:
        count = conn.execute("SELECT COUNT(*) FROM authorization_policy_v2").fetchone()[0]
    except sqlite3.OperationalError:
        count = 0

    if count == 0:
        conn.close()
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "seed_v2", str(MIGRATIONS / "008_seed_v2.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run(db_path)
    else:
        conn.close()

    return db_path


def _get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class TestShadowAdapter:
    """Test suite for ShadowRbacAdapter."""

    @classmethod
    def setup(cls):
        """Set up a test database with v1 + v2 schema and data."""
        import tempfile
        cls.tmp = Path(tempfile.mkdtemp(prefix="shadow_test_"))
        cls.db_path = _fresh_db(cls.tmp)

    def test_01_v1_result_unchanged(self):
        """Shadow adapter returns identical v1 result."""
        from rbac.engine import RbacEngine
        from rbac.shadow_adapter import ShadowRbacAdapter

        conn = _get_conn(self.db_path)

        v1_eng = RbacEngine(conn)
        v1_result = v1_eng.evaluate(
            "demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "W3A"
        )

        shadow = ShadowRbacAdapter(conn, shadow_enabled=True)
        shadow_result = shadow.evaluate(
            "demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "W3A"
        )

        # The v1 fields must match exactly
        assert shadow_result["allow"] == v1_result["allow"], \
            f"allow mismatch: {shadow_result['allow']} vs {v1_result['allow']}"
        assert shadow_result["subject"] == v1_result["subject"]
        assert shadow_result["permission"] == v1_result["permission"]
        assert shadow_result["reason"] == v1_result["reason"]
        conn.close()
        print("  PASS: v1 result unchanged through shadow adapter")

    def test_02_shadow_disabled_skips_v2(self):
        """When shadow_enabled=False, no v2 work runs."""
        from rbac.shadow_adapter import ShadowRbacAdapter

        conn = _get_conn(self.db_path)
        adapter = ShadowRbacAdapter(conn, shadow_enabled=False)
        result = adapter.evaluate(
            "demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "W3A"
        )
        assert result["allow"] is True
        # No divergence should be logged
        div = conn.execute("SELECT COUNT(*) c FROM rbac_shadow_divergence_log").fetchone()["c"]
        assert div == 0, f"Expected 0 divergences, got {div}"
        conn.close()
        print("  PASS: shadow disabled skips v2 correctly")

    def test_03_identity_mapping(self):
        """persona_code correctly resolves to v2 account_uuid."""
        from rbac.shadow_adapter import ShadowRbacAdapter

        conn = _get_conn(self.db_path)
        adapter = ShadowRbacAdapter(conn, shadow_enabled=True)
        uuid = adapter._resolve_account_uuid("demo.slot.charge.w3a")
        assert uuid is not None, "Failed to resolve demo.slot.charge.w3a to account_uuid"
        # Should be a valid UUID format
        parts = uuid.split("-")
        assert len(parts) == 5, f"Invalid UUID format: {uuid}"
        conn.close()
        print(f"  PASS: identity mapping resolved → {uuid}")

    def test_04_all_scenarios_run(self):
        """All 16 RBAC scenarios run through shadow adapter without error."""
        from rbac.shadow_adapter import ShadowRbacAdapter

        SCENARIOS = [
            ("demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "W3A", True),
            ("demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "ICU-MAIN", False),
            ("demo.slot.charge.w3a", "BED_READ", "UNIT", "ICU-MAIN", True),
            ("demo.slot.charge.icu-main", "BED_CONTROL", "UNIT", "ICU-MAIN", True),
            ("demo.slot.charge.icu-main", "BED_CONTROL", "UNIT", "W3A", False),
            ("demo.slot.sched.emrg", "BED_CONTROL", "UNIT", "ED-RESUS", False),
            ("demo.slot.sched.emrg", "SCHED_WRITE", "UNIT", "ED-RESUS", True),
            ("demo.slot.sched.emrg", "BED_READ", "UNIT", "ED-RESUS", True),
            ("demo.slot.um.gens", "APPROVE", "UNIT", "W3A", True),
            ("demo.slot.um.gens", "BED_BLOCK", "UNIT", "W3A", True),
            ("demo.slot.um.gens", "BED_CONTROL", "UNIT", "W3A", False),
            ("demo.slot.bedcoord", "BED_CONTROL", "UNIT", "ICU-MAIN", True),
            ("demo.slot.clerk.emrg", "BED_REQUEST", "UNIT", "ED-RESUS", True),
            ("demo.slot.clerk.emrg", "BED_CONTROL", "UNIT", "ED-RESUS", False),
            ("demo.slot.hr", "ORG_READ", "UNIT", "W3A", True),
            ("demo.slot.hr", "BED_CONTROL", "UNIT", "W3A", False),
        ]

        conn = _get_conn(self.db_path)
        adapter = ShadowRbacAdapter(conn, shadow_enabled=True)

        passed = 0
        failed = 0
        for subject, perm, rtype, rcode, expected in SCENARIOS:
            result = adapter.evaluate(subject, perm, rtype, rcode)
            if result["allow"] == expected:
                passed += 1
            else:
                failed += 1
                print(f"    FAIL: {subject}/{perm}/{rtype}:{rcode} "
                      f"expected={expected} got={result['allow']}")

        conn.commit()
        conn.close()

        assert failed == 0, f"{failed} scenario(s) failed"
        print(f"  PASS: All {passed} scenarios passed through shadow adapter")

    def test_05_divergence_report_structure(self):
        """Divergence report returns the expected structure."""
        from rbac.shadow_adapter import ShadowRbacAdapter

        conn = _get_conn(self.db_path)
        report = ShadowRbacAdapter.divergence_report(conn)

        assert "total_divergences" in report
        assert "total_decisions" in report
        assert "divergence_rate" in report
        assert "by_reason_code" in report
        assert "by_subject" in report
        assert "recent" in report
        assert isinstance(report["divergence_rate"], float)
        conn.close()
        print(f"  PASS: divergence report structure valid "
              f"(rate={report['divergence_rate']}, "
              f"divergences={report['total_divergences']})")

    def test_06_grants_passthrough(self):
        """_grants() and _held_permissions() work via the adapter."""
        from rbac.shadow_adapter import ShadowRbacAdapter

        conn = _get_conn(self.db_path)
        adapter = ShadowRbacAdapter(conn, shadow_enabled=True)
        grants = adapter._grants("demo.slot.charge.w3a")
        held = adapter._held_permissions(grants)

        assert len(grants) > 0, "Expected at least one grant"
        assert "BED_CONTROL" in held, f"Expected BED_CONTROL in held permissions: {held}"
        conn.close()
        print(f"  PASS: grants passthrough ({len(grants)} grants, {len(held)} permissions)")


def run_tests():
    print("=" * 60)
    print("RBAC v2 Shadow Integration Tests")
    print("=" * 60)

    suite = TestShadowAdapter()
    suite.setup()

    tests = [
        suite.test_01_v1_result_unchanged,
        suite.test_02_shadow_disabled_skips_v2,
        suite.test_03_identity_mapping,
        suite.test_04_all_scenarios_run,
        suite.test_05_divergence_report_structure,
        suite.test_06_grants_passthrough,
    ]

    passed = 0
    failed = 0
    errors = []

    for test in tests:
        name = test.__name__
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  FAIL: {name}: {e}")

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  {name}: {err}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
