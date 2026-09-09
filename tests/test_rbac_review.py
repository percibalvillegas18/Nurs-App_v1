#!/usr/bin/env python3
"""Regression tests for the security/RBAC review fixes.

Run with: python3 -m unittest tests.test_rbac_review
"""
from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "org-directory"))

from rbac.engine import RbacEngine  # noqa: E402
import um  # noqa: E402


class TestV1ResourceContainment(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE facility (
                facility_id INTEGER PRIMARY KEY, facility_code TEXT UNIQUE,
                name TEXT, status TEXT
            );
            CREATE TABLE department (
                department_id INTEGER PRIMARY KEY, department_code TEXT UNIQUE,
                facility_id INTEGER, name TEXT, status TEXT
            );
            CREATE TABLE nursing_unit (
                unit_id INTEGER PRIMARY KEY, unit_code TEXT UNIQUE,
                department_id INTEGER, unit_name TEXT, status TEXT
            );
            CREATE TABLE persona (
                persona_id INTEGER PRIMARY KEY, persona_code TEXT UNIQUE,
                display_name TEXT, job_title TEXT, category TEXT,
                is_demo INTEGER, notes TEXT
            );
            CREATE TABLE role (
                role_id INTEGER PRIMARY KEY, role_code TEXT UNIQUE,
                title TEXT, level TEXT, data_scope TEXT
            );
            CREATE TABLE permission (
                permission_id INTEGER PRIMARY KEY, perm_code TEXT UNIQUE,
                module TEXT, description TEXT
            );
            CREATE TABLE role_permission (role_id INTEGER, permission_id INTEGER,
                                          PRIMARY KEY(role_id, permission_id));
            CREATE TABLE role_grant (
                grant_id INTEGER PRIMARY KEY, persona_id INTEGER, role_id INTEGER,
                scope_type TEXT, scope_code TEXT, effective_from TEXT,
                effective_to TEXT, status TEXT
            );
            CREATE TABLE sod_rule (
                sod_id INTEGER PRIMARY KEY, perm_a TEXT, perm_b TEXT,
                message TEXT, waive_roles TEXT
            );
            INSERT INTO facility VALUES (1, 'AIGH', 'AIGH', 'ACTIVE');
            INSERT INTO facility VALUES (2, 'OTHER', 'Other', 'ACTIVE');
            INSERT INTO department VALUES (1, 'GENS', 1, 'General', 'ACTIVE');
            INSERT INTO department VALUES (2, 'OTHER', 2, 'Other', 'ACTIVE');
            INSERT INTO nursing_unit VALUES (1, 'W3A', 1, 'Ward 3A', 'ACTIVE');
            INSERT INTO nursing_unit VALUES (2, 'O1', 2, 'Other ward', 'ACTIVE');
            INSERT INTO persona VALUES (1, 'demo.slot.bedcoord', 'Bed Coordinator', 'Bed Coordinator', 'Ops', 1, NULL);
            INSERT INTO role VALUES (1, 'BED_COORD', 'Bed Coordinator', 'P3', 'FACILITY');
            INSERT INTO permission VALUES (1, 'BED_CONTROL', 'Bed', 'Control beds');
            INSERT INTO role_permission VALUES (1, 1);
            INSERT INTO role_grant VALUES (1, 1, 1, 'FACILITY', 'AIGH', '2026-01-01', NULL, 'ACTIVE');
            """
        )

    def tearDown(self):
        self.conn.close()

    def test_facility_scope_is_not_a_wildcard(self):
        engine = RbacEngine(self.conn)
        self.assertTrue(engine.evaluate("demo.slot.bedcoord", "BED_CONTROL", "UNIT", "W3A")["allow"])
        self.assertFalse(engine.evaluate("demo.slot.bedcoord", "BED_CONTROL", "UNIT", "O1")["allow"])
        self.assertFalse(engine.evaluate("demo.slot.bedcoord", "BED_CONTROL", "UNIT", "NO_SUCH_UNIT")["allow"])
        self.assertFalse(engine.evaluate("demo.slot.bedcoord", "BED_CONTROL", "FACILITY", "OTHER")["allow"])
        self.assertFalse(engine.evaluate("demo.slot.bedcoord", "BED_CONTROL", "UNKNOWN", "anything")["allow"])

    def test_expired_grant_is_not_authoritative(self):
        self.conn.execute("UPDATE role_grant SET effective_to='2020-01-01' WHERE grant_id=1")
        self.conn.commit()
        result = RbacEngine(self.conn).evaluate(
            "demo.slot.bedcoord", "BED_CONTROL", "UNIT", "W3A"
        )
        self.assertFalse(result["allow"])
        self.assertIn("No active role grant", result["reason"])


class TestIdentityAdminDateAlignment(unittest.TestCase):
    def test_expired_admin_grant_does_not_set_admin_flag(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        now = datetime.now(timezone.utc)
        future = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.executescript(
            """
            CREATE TABLE persona (persona_id INTEGER PRIMARY KEY, persona_code TEXT,
                display_name TEXT, job_title TEXT, category TEXT);
            CREATE TABLE app_user (user_id INTEGER PRIMARY KEY, persona_id INTEGER,
                username TEXT, status TEXT, must_change INTEGER, last_login TEXT,
                password_salt TEXT, password_hash TEXT);
            CREATE TABLE app_session (token TEXT PRIMARY KEY, user_id INTEGER,
                created_at TEXT, expires_at TEXT);
            CREATE TABLE role (role_id INTEGER PRIMARY KEY, role_code TEXT);
            CREATE TABLE role_grant (persona_id INTEGER, role_id INTEGER, status TEXT,
                effective_from TEXT, effective_to TEXT);
            INSERT INTO persona VALUES (1, 'demo.admin', 'Admin', 'Admin', 'System');
            INSERT INTO app_user VALUES (1, 1, 'admin', 'ACTIVE', 0, NULL, 'salt', 'hash');
            INSERT INTO app_session VALUES ('token', 1, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z');
            INSERT INTO role VALUES (1, 'ORG_ADMIN');
            INSERT INTO role_grant VALUES (1, 1, 'ACTIVE', '2020-01-01', '2020-12-31');
            """
        )
        user = um.user_from_conn(conn, {"Authorization": "Bearer token"})
        self.assertIsNotNone(user)
        self.assertEqual(user["roles"], [])
        self.assertFalse(user["can_admin_users"])
        conn.close()


if __name__ == "__main__":
    unittest.main()
