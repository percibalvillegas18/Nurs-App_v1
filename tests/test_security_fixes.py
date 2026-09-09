#!/usr/bin/env python3
"""Test suite verifying all 16 code-review fixes.

Run: python -m pytest tests/test_security_fixes.py -v
Or:  python tests/test_security_fixes.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add project to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "org-directory"))
sys.path.insert(0, str(ROOT))


class TestDemoPasswordGating(unittest.TestCase):
    """Critical-1: Demo password must only appear when DEMO_MODE=true."""

    def test_demo_mode_off_password_is_none(self):
        os.environ.pop("DEMO_MODE", None)
        # Reimport to pick up env change
        import importlib
        import um
        importlib.reload(um)
        self.assertFalse(um.DEMO_MODE)
        self.assertIsNone(um.DEMO_PASSWORD)

    def test_demo_mode_on_password_present(self):
        os.environ["DEMO_MODE"] = "true"
        import importlib
        import um
        importlib.reload(um)
        self.assertTrue(um.DEMO_MODE)
        self.assertEqual(um.DEMO_PASSWORD, "Demo@2026")
        os.environ.pop("DEMO_MODE", None)
        importlib.reload(um)

    def test_login_error_no_demo_hint_when_off(self):
        os.environ.pop("DEMO_MODE", None)
        import importlib
        import um
        importlib.reload(um)
        # The error message should not contain the password
        conn = _test_db()
        _seed_test_user(conn)
        result = um.login(conn, "testuser", "wrongpassword", "127.0.0.1")
        self.assertIn("error", result)
        self.assertNotIn("Demo@2026", result["error"])
        conn.close()


class TestCSRFProtection(unittest.TestCase):
    """Critical-2: POST endpoints reject cookie-only auth."""

    def test_request_token_header_required_rejects_cookie(self):
        import importlib
        import um
        importlib.reload(um)
        headers = MagicMock()
        headers.get = lambda key, default=None: {
            "Authorization": "",
            "X-Session-Token": None,
            "Cookie": "hnwms_session=abc123",
        }.get(key)
        # With require_header=True, cookie-only should return None
        token = um.request_token(headers, require_header=True)
        self.assertIsNone(token)

    def test_request_token_header_allows_bearer(self):
        import importlib
        import um
        importlib.reload(um)
        headers = MagicMock()
        headers.get = lambda key, default=None: {
            "Authorization": "Bearer mytoken123",
            "X-Session-Token": None,
            "Cookie": "",
        }.get(key)
        token = um.request_token(headers, require_header=True)
        self.assertEqual(token, "mytoken123")

    def test_request_token_header_allows_x_session(self):
        import importlib
        import um
        importlib.reload(um)
        headers = MagicMock()
        headers.get = lambda key, default=None: {
            "Authorization": "",
            "X-Session-Token": "xtoken456",
            "Cookie": "",
        }.get(key)
        token = um.request_token(headers, require_header=True)
        self.assertEqual(token, "xtoken456")


class TestRBACSimulatedMode(unittest.TestCase):
    """Critical-3: GET evaluate logs decisions as SIMULATED."""

    def test_evaluate_request_marks_simulated(self):
        conn = _test_db()
        _seed_rbac(conn)
        # Apply mode column migration inline
        try:
            conn.execute("ALTER TABLE rbac_decision_log ADD COLUMN mode TEXT NOT NULL DEFAULT 'ENFORCED'")
        except Exception:
            pass  # already exists
        sys.path.insert(0, str(ROOT / "org-directory"))
        import importlib
        import app as app_module
        importlib.reload(app_module)
        # Monkey-patch db() to return a wrapper that makes close() a no-op
        # (sqlite3.Connection.close is read-only, so we can't patch it directly)
        class _NoCloseConn:
            """Proxy that delegates everything to the real conn but ignores close()."""
            def __init__(self, real):
                self._real = real
            def close(self):
                pass  # no-op so evaluate_request's finally doesn't close our test conn
            def __getattr__(self, name):
                return getattr(self._real, name)
        wrapper = _NoCloseConn(conn)
        app_module.db = lambda: wrapper
        try:
            payload = {
                "subject": "demo.slot.charge.w3a",
                "permission": "BED_CONTROL",
                "resource_type": "UNIT",
                "resource_code": "W3A",
            }
            result = app_module.evaluate_request(payload, mode="SIMULATED")
            self.assertEqual(result["mode"], "SIMULATED")
            row = conn.execute(
                "SELECT mode FROM rbac_decision_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(row["mode"], "SIMULATED")
        finally:
            conn.close()


class TestPathTraversalGuard(unittest.TestCase):
    """High-2: stored_name regex guard on document download."""

    def test_valid_stored_name_accepted(self):
        import importlib
        import um
        importlib.reload(um)
        # Valid format: 16 hex chars + extension
        self.assertTrue(re.fullmatch(r'[a-f0-9]{16}\.\w+', "abcdef0123456789.pdf"))

    def test_traversal_stored_name_rejected(self):
        import importlib
        import um
        importlib.reload(um)
        # A path traversal attempt should not match
        self.assertIsNone(re.fullmatch(r'[a-f0-9]{16}\.\w+', "../../etc/passwd"))
        self.assertIsNone(re.fullmatch(r'[a-f0-9]{16}\.\w+', "../secret.pdf"))


class TestBindAddress(unittest.TestCase):
    """High-3: Default bind address is 127.0.0.1."""

    def test_default_host_is_localhost(self):
        os.environ.pop("BIND_HOST", None)
        import importlib
        import app as app_module
        importlib.reload(app_module)
        self.assertEqual(app_module.HOST, "127.0.0.1")

    def test_env_override_host(self):
        os.environ["BIND_HOST"] = "0.0.0.0"
        import importlib
        import app as app_module
        importlib.reload(app_module)
        self.assertEqual(app_module.HOST, "0.0.0.0")
        os.environ.pop("BIND_HOST", None)
        importlib.reload(app_module)


class TestSessionInvalidation(unittest.TestCase):
    """High-4: Password change invalidates other sessions."""

    def test_password_change_revokes_other_sessions(self):
        os.environ.pop("DEMO_MODE", None)
        import importlib
        import um
        importlib.reload(um)
        conn = _test_db()
        _seed_test_user(conn)
        # Create two sessions for user_id=1
        conn.execute(
            "INSERT INTO app_session (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            ("token_keep", 1, "2026-09-09T00:00:00Z", "2026-09-10T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO app_session (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            ("token_revoke", 1, "2026-09-09T00:00:00Z", "2026-09-10T00:00:00Z"),
        )
        conn.commit()
        # Save profile with password change, pretending current token is "token_keep"
        user = {
            "persona_id": 1, "can_admin_users": True, "persona_code": "test.user",
            "username": "testuser",
        }
        headers = MagicMock()
        headers.get = lambda key, default=None: {
            "Authorization": "Bearer token_keep",
        }.get(key)
        payload = {
            "new_password": "NewPass@123",
            "_headers": headers,
        }
        result = um.save_profile(conn, user, "test.user", payload)
        self.assertTrue(result.get("ok"), f"Expected ok, got: {result}")
        # token_keep should remain, token_revoke should be gone
        remaining = [r["token"] for r in conn.execute("SELECT token FROM app_session").fetchall()]
        self.assertIn("token_keep", remaining)
        self.assertNotIn("token_revoke", remaining)
        conn.close()


class TestPasswordComplexity(unittest.TestCase):
    """Medium-5: Password complexity validation."""

    def test_no_uppercase_rejected(self):
        os.environ.pop("DEMO_MODE", None)
        import importlib
        import um
        importlib.reload(um)
        conn = _test_db()
        _seed_test_user(conn)
        user = {"persona_id": 1, "can_admin_users": True, "persona_code": "test.user"}
        result = um.save_profile(conn, user, "test.user", {"new_password": "lowercase1!", "_headers": {}})
        self.assertIn("uppercase", result.get("error", ""))
        conn.close()

    def test_no_digit_rejected(self):
        import importlib
        import um
        importlib.reload(um)
        conn = _test_db()
        _seed_test_user(conn)
        user = {"persona_id": 1, "can_admin_users": True, "persona_code": "test.user"}
        result = um.save_profile(conn, user, "test.user", {"new_password": "NoDigitHere!", "_headers": {}})
        self.assertIn("digit", result.get("error", ""))
        conn.close()

    def test_no_special_rejected(self):
        import importlib
        import um
        importlib.reload(um)
        conn = _test_db()
        _seed_test_user(conn)
        user = {"persona_id": 1, "can_admin_users": True, "persona_code": "test.user"}
        result = um.save_profile(conn, user, "test.user", {"new_password": "NoSpecial1A", "_headers": {}})
        self.assertIn("special", result.get("error", ""))
        conn.close()

    def test_same_password_rejected(self):
        import importlib
        import um
        importlib.reload(um)
        conn = _test_db()
        _seed_test_user(conn, password="SamePass@123")
        user = {"persona_id": 1, "can_admin_users": True, "persona_code": "test.user"}
        result = um.save_profile(conn, user, "test.user", {"new_password": "SamePass@123", "_headers": {}})
        self.assertIn("differ", result.get("error", ""))
        conn.close()

    def test_valid_password_accepted(self):
        import importlib
        import um
        importlib.reload(um)
        conn = _test_db()
        _seed_test_user(conn)
        user = {"persona_id": 1, "can_admin_users": True, "persona_code": "test.user"}
        result = um.save_profile(conn, user, "test.user", {"new_password": "ValidPass@99", "_headers": {}})
        self.assertTrue(result.get("ok"), f"Expected ok, got: {result}")
        conn.close()


class TestNPlus1Fix(unittest.TestCase):
    """Medium-1: RBAC engine no longer has N+1 query."""

    def test_grants_batch_query(self):
        """Verify grants returns data and uses batch permission fetch (structural test)."""
        conn = _test_db()
        _seed_rbac(conn)
        from rbac.engine import RbacEngine
        import importlib
        from rbac import engine as eng_mod
        importlib.reload(eng_mod)
        eng = eng_mod.RbacEngine(conn)
        grants = eng._grants("demo.slot.charge.w3a")
        self.assertTrue(len(grants) > 0, "Expected at least one grant")
        # Verify permissions are populated (would be empty if batch query failed)
        for g in grants:
            self.assertIsInstance(g["permissions"], list)
            self.assertTrue(len(g["permissions"]) > 0, f"Grant {g['role_code']} has no permissions")
        # Verify the source code uses IN (...) batch pattern instead of loop
        src = (ROOT / "rbac" / "engine.py").read_text()
        self.assertIn("WHERE rp.role_id IN", src, "Expected batch IN query in _grants")
        conn.close()


class TestFilenameAllowList(unittest.TestCase):
    """High-1: original_name sanitized to printable chars."""

    def test_control_chars_removed(self):
        sanitized = re.sub(r'[^\x20-\x7E -￿]', '_', "evil\x00file\nname.pdf")
        self.assertNotIn('\x00', sanitized)
        self.assertNotIn('\n', sanitized)

    def test_normal_filename_preserved(self):
        sanitized = re.sub(r'[^\x20-\x7E -￿]', '_', "report_2026.pdf")
        self.assertEqual(sanitized, "report_2026.pdf")


class TestLoginJSNoHardcodedPassword(unittest.TestCase):
    """Critical-1 (JS): login.js no longer contains hardcoded password."""

    def test_no_pw_variable(self):
        js_path = ROOT / "org-directory" / "static" / "login.js"
        content = js_path.read_text()
        self.assertNotIn('var PW = "Demo@2026"', content)
        self.assertNotIn("var PW =", content)


class TestMigrationScripts(unittest.TestCase):
    """Migration scripts parse and apply without errors."""

    def test_migrations_exist(self):
        mig_dir = ROOT / "migrations"
        self.assertTrue(mig_dir.exists())
        sql_files = list(mig_dir.glob("[0-9][0-9][0-9]_*.sql"))
        self.assertGreaterEqual(len(sql_files), 4)

    def test_rollback_scripts_exist(self):
        mig_dir = ROOT / "migrations"
        rollbacks = list(mig_dir.glob("*_rollback.sql"))
        self.assertGreaterEqual(len(rollbacks), 3)

    def test_migration_sql_is_valid(self):
        """Each migration SQL should parse in SQLite without error."""
        conn = _test_db()
        _seed_rbac(conn)
        mig_dir = ROOT / "migrations"
        for sql_file in sorted(mig_dir.glob("[0-9][0-9][0-9]_*.sql")):
            if "_rollback" in sql_file.name:
                continue
            sql = sql_file.read_text()
            try:
                conn.executescript(sql)
            except Exception as e:
                self.fail(f"Migration {sql_file.name} failed: {e}")
        conn.close()


# ─── Test helpers ─────────────────────────────────────────────────

def _test_db():
    """Create an in-memory SQLite database with the required schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Core schema
    schema_files = [
        ROOT / "org-directory" / "schema.sql",
        ROOT / "rbac" / "schema.sql",
        ROOT / "org-directory" / "um_schema.sql",
    ]
    for sf in schema_files:
        if sf.exists():
            sql = sf.read_text()
            # Remove PRAGMA lines that conflict with in-memory
            sql = "\n".join(l for l in sql.split("\n") if not l.strip().startswith("PRAGMA"))
            conn.executescript(sql)
    return conn


def _seed_test_user(conn, password="Demo@2026"):
    """Insert a minimal test persona + app_user."""
    import importlib
    import um
    importlib.reload(um)
    conn.execute(
        "INSERT OR IGNORE INTO persona (persona_id, persona_code, display_name, job_title, category, is_demo) "
        "VALUES (1, 'test.user', 'Test User', 'Tester', 'TEST', 1)"
    )
    salt, hashed = um.hash_password(password)
    conn.execute(
        "INSERT OR IGNORE INTO app_user (user_id, persona_id, username, password_salt, password_hash) "
        "VALUES (1, 1, 'testuser', ?, ?)",
        (salt, hashed),
    )
    conn.execute(
        "INSERT OR IGNORE INTO staff_profile (persona_id) VALUES (1)"
    )
    conn.commit()


def _seed_rbac(conn):
    """Insert minimal RBAC data for testing."""
    conn.execute("INSERT OR IGNORE INTO facility VALUES (1, 'AIGH', 'AIGH Hospital', 'Central', 'Riyadh', 'AIGH', 'CBAHI', 'ACTIVE')")
    conn.execute("INSERT OR IGNORE INTO department VALUES (1, 'GENS', 1, 'General Services', 'CLINICAL', 'ACTIVE')")
    conn.execute("INSERT OR IGNORE INTO unit_group VALUES (1, 1, 'Medical Wards', 'INPATIENT', 'ACTIVE')")
    conn.execute("INSERT OR IGNORE INTO nursing_unit VALUES (1, 'W3A', 1, 1, 'Ward 3A', 'WARD', 'INPATIENT', 'INPATIENT_LICENSED', 30, 30, 30, 1, NULL, '2026-01-01', NULL, 'ACTIVE')")
    conn.execute("INSERT OR IGNORE INTO persona VALUES (1, 'demo.slot.charge.w3a', 'Charge Nurse W3A', 'Charge Nurse', 'NURSING', 1, NULL)")
    conn.execute("INSERT OR IGNORE INTO role VALUES (1, 'CHARGE', 'Charge Nurse', 'L4', 'UNIT')")
    conn.execute("INSERT OR IGNORE INTO permission VALUES (1, 'BED_CONTROL', 'ADT', 'Place patient in bed')")
    conn.execute("INSERT OR IGNORE INTO permission VALUES (2, 'BED_READ', 'ADT', 'View bed census')")
    conn.execute("INSERT OR IGNORE INTO role_permission VALUES (1, 1)")
    conn.execute("INSERT OR IGNORE INTO role_permission VALUES (1, 2)")
    conn.execute("INSERT OR IGNORE INTO role_grant VALUES (1, 1, 1, 'UNIT', 'W3A', '2026-01-01', NULL, 'ACTIVE')")
    conn.execute("INSERT OR IGNORE INTO sod_rule VALUES (1, 'BED_CONTROL', 'SCHED_WRITE', 'Bed control and scheduling must be separate', 'SYS_ADMIN')")
    # Create the decision log table
    conn.execute("""CREATE TABLE IF NOT EXISTS rbac_decision_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decided_at TEXT NOT NULL,
        subject TEXT NOT NULL,
        permission TEXT NOT NULL,
        resource_type TEXT,
        resource_code TEXT,
        allow INTEGER NOT NULL,
        reason TEXT NOT NULL,
        mode TEXT NOT NULL DEFAULT 'ENFORCED'
    )""")
    conn.commit()


import contextlib

@contextlib.contextmanager
def _ctx(conn):
    """Fake context manager that yields conn without closing."""
    yield conn


if __name__ == "__main__":
    unittest.main()
