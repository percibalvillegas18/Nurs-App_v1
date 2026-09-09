#!/usr/bin/env python3
"""Wave P1 Org Directory API + static UI. Stdlib only."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from rbac.engine import RbacEngine  # noqa: E402
import um  # noqa: E402

DB = HERE / "data" / "org_directory.db"
STATIC = HERE / "static"
HOST = os.environ.get("BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))

RBAC_STATUS = "APPROVED"
RBAC_APPLIED = "2026-09-09"

# (subject, permission, resource_type, resource_code, label, expect_allow)
SCENARIOS = [
    ("demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "W3A", "Charge places patients on own unit", True),
    ("demo.slot.charge.w3a", "BED_CONTROL", "UNIT", "ICU-MAIN", "Charge cannot place on ICU", False),
    ("demo.slot.charge.w3a", "BED_READ", "UNIT", "ICU-MAIN", "Charge can view ICU census", True),
    ("demo.slot.charge.icu-main", "BED_CONTROL", "UNIT", "ICU-MAIN", "ICU charge places on ICU", True),
    ("demo.slot.charge.icu-main", "BED_CONTROL", "UNIT", "W3A", "ICU charge cannot place on W3A", False),
    ("demo.slot.sched.emrg", "BED_CONTROL", "UNIT", "ED-RESUS", "Scheduler cannot move beds", False),
    ("demo.slot.sched.emrg", "SCHED_WRITE", "UNIT", "ED-RESUS", "Scheduler publishes ED roster", True),
    ("demo.slot.sched.emrg", "BED_READ", "UNIT", "ED-RESUS", "Scheduler sees ED census for staffing", True),
    ("demo.slot.um.gens", "APPROVE", "UNIT", "W3A", "UM approves in GENS", True),
    ("demo.slot.um.gens", "BED_BLOCK", "UNIT", "W3A", "UM may block/OOS a GENS bed", True),
    ("demo.slot.um.gens", "BED_CONTROL", "UNIT", "W3A", "UM does not assign/place patients", False),
    ("demo.slot.bedcoord", "BED_CONTROL", "UNIT", "ICU-MAIN", "Bed coordinator places anywhere", True),
    ("demo.slot.clerk.emrg", "BED_REQUEST", "UNIT", "ED-RESUS", "Clerk requests a bed", True),
    ("demo.slot.clerk.emrg", "BED_CONTROL", "UNIT", "ED-RESUS", "Clerk cannot assign", False),
    ("demo.slot.hr", "ORG_READ", "UNIT", "W3A", "HR reads locations", True),
    ("demo.slot.hr", "BED_CONTROL", "UNIT", "W3A", "HR cannot move beds", False),
]


import contextlib


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextlib.contextmanager
def db_conn():
    """Context manager for database connections — ensures close on exit."""
    conn = db()
    try:
        yield conn
    finally:
        conn.close()


def rows(sql, args=()):
    conn = db()
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def one(sql, args=()):
    r = rows(sql, args)
    return r[0] if r else None


def tree(nodes, parent=None):
    out = []
    for n in nodes:
        if n["parent_org_node_id"] == parent:
            child = dict(n)
            child["children"] = tree(nodes, n["org_node_id"])
            out.append(child)
    return out


def summary():
    units = rows("SELECT * FROM nursing_unit")
    lic = sum(u["licensed_capacity"] for u in units)
    ed = sum(u["resource_capacity"] for u in units if u["capacity_class"] == "ED_STRETCHER")
    src = sum(u["source_bed_count"] or 0 for u in units)
    pending = [u["unit_code"] for u in units if u["dq_flag"] and "PENDING" in u["dq_flag"]]
    return {
        "facility": one("SELECT * FROM facility"),
        "signoff": "UNSIGNED",
        "walk_status": "NOT_WALKED",
        "units": len(units),
        "departments": 4,
        "source_bed_count": src,
        "licensed_inpatient": lic,
        "licensed_inpatient_if_merged": lic - 14,
        "ed_stretchers": ed,
        "patient_placeable": sum(u["resource_capacity"] for u in units if u["is_bedded"]),
        "pending_dq": pending,
        "rbac": RBAC_STATUS,
        "rbac_applied": RBAC_APPLIED,
        "warning": "P0 unsigned. Do not report 515/524 as licensed beds. Physical audit not walked. RBAC approved.",
    }


def _roles_with_perms():
    """Fetch all roles with their permissions in two queries (no N+1)."""
    conn = db()
    try:
        role_list = [dict(r) for r in conn.execute("SELECT * FROM role ORDER BY role_id")]
        perm_rows = conn.execute(
            """SELECT rp.role_id, perm.perm_code
               FROM role_permission rp
               JOIN permission perm ON perm.permission_id = rp.permission_id
               ORDER BY perm.perm_code"""
        ).fetchall()
        by_role = {}
        for rp in perm_rows:
            by_role.setdefault(rp["role_id"], []).append(rp["perm_code"])
        for r in role_list:
            r["permissions"] = by_role.get(r["role_id"], [])
        return role_list
    finally:
        conn.close()


ROUTES = {
    "/api/health": lambda q: {"ok": True, "service": "org-directory", "wave": "P1", "rbac": RBAC_STATUS},
    "/api/summary": lambda q: summary(),
    "/api/facilities": lambda q: rows("SELECT * FROM facility"),
    "/api/departments": lambda q: rows(
        """SELECT d.*, f.facility_code,
                  (SELECT COUNT(*) FROM nursing_unit u WHERE u.department_id=d.department_id) AS unit_count,
                  (SELECT COALESCE(SUM(licensed_capacity),0) FROM nursing_unit u WHERE u.department_id=d.department_id) AS licensed_capacity
           FROM department d JOIN facility f ON f.facility_id=d.facility_id ORDER BY d.department_code"""
    ),
    "/api/unit-groups": lambda q: rows(
        """SELECT g.*, d.department_code, d.name AS department_name
           FROM unit_group g JOIN department d ON d.department_id=g.department_id ORDER BY d.department_code, g.name"""
    ),
    "/api/units": lambda q: rows(
        """SELECT u.*, d.department_code, d.name AS department_name, g.name AS unit_group_name,
                  a.walk_status, a.desk_recommendation, a.notes AS audit_notes
           FROM nursing_unit u
           JOIN department d ON d.department_id=u.department_id
           JOIN unit_group g ON g.unit_group_id=u.unit_group_id
           LEFT JOIN desk_audit a ON a.unit_code=u.unit_code
           ORDER BY d.department_code, u.unit_code"""
    ),
    "/api/org-nodes": lambda q: rows("SELECT * FROM org_node ORDER BY org_node_id"),
    "/api/org-tree": lambda q: tree(rows("SELECT * FROM org_node ORDER BY org_node_id")),
    "/api/positions": lambda q: rows(
        """SELECT p.*, n.org_code, n.name AS org_name
           FROM workforce_position p LEFT JOIN org_node n ON n.org_node_id=p.org_node_id
           ORDER BY p.position_level, p.position_code"""
    ),
    "/api/coverage": lambda q: rows(
        """SELECT c.*, u.unit_name, u.capacity_class, d.name AS department_name
           FROM coverage_template c
           LEFT JOIN nursing_unit u ON u.unit_code=c.unit_code
           LEFT JOIN department d ON d.department_id=u.department_id
           ORDER BY c.clinical_line, c.unit_code"""
    ),
    "/api/roles": lambda q: _roles_with_perms(),
    "/api/vocabulary": lambda q: rows("SELECT * FROM vocabulary ORDER BY domain, code"),
    "/api/audit": lambda q: rows("SELECT * FROM desk_audit ORDER BY unit_code"),
    "/api/events": lambda q: rows("SELECT * FROM registry_event ORDER BY id DESC"),
    "/api/rbac/personas": lambda q: rows(
        """SELECT p.*, r.role_code, g.scope_type, g.scope_code
           FROM persona p
           JOIN role_grant g ON g.persona_id = p.persona_id
           JOIN role r ON r.role_id = g.role_id
           ORDER BY p.persona_id"""
    ),
    "/api/rbac/people": lambda q: list_people(),
    "/api/rbac/grants": lambda q: rows(
        """SELECT g.*, p.persona_code, p.display_name, r.role_code, r.title
           FROM role_grant g
           JOIN persona p ON p.persona_id = g.persona_id
           JOIN role r ON r.role_id = g.role_id
           ORDER BY p.persona_code"""
    ),
    "/api/rbac/sod": lambda q: rows("SELECT * FROM sod_rule"),
    "/api/rbac/matrix": lambda q: rbac_matrix(),
    "/api/rbac/scenarios": lambda q: run_scenarios(),
    "/api/rollup": lambda q: rows(
        """SELECT capacity_class,
                  COUNT(*) AS unit_count,
                  COALESCE(SUM(resource_capacity),0) AS resource_capacity,
                  COALESCE(SUM(licensed_capacity),0) AS licensed_capacity,
                  COALESCE(SUM(source_bed_count),0) AS source_bed_count
           FROM nursing_unit GROUP BY capacity_class ORDER BY licensed_capacity DESC, resource_capacity DESC"""
    ),
}


def list_people():
    people = rows(
        """SELECT persona_id, persona_code, display_name, job_title, category, is_demo, notes
           FROM persona ORDER BY category, job_title, display_name"""
    )
    grants = rows(
        """SELECT g.persona_id, r.role_code, r.title, g.scope_type, g.scope_code, g.status
           FROM role_grant g JOIN role r ON r.role_id = g.role_id
           ORDER BY r.role_code"""
    )
    by_id = {}
    for p in people:
        p["grants"] = []
        by_id[p["persona_id"]] = p
    for g in grants:
        if g["persona_id"] in by_id:
            by_id[g["persona_id"]]["grants"].append(
                {
                    "role": g["role_code"],
                    "title": g["title"],
                    "scope_type": g["scope_type"],
                    "scope_code": g["scope_code"],
                    "status": g["status"],
                }
            )
    return people


def rename_person(payload: dict) -> dict:
    code = (payload.get("persona_code") or "").strip()
    name = (payload.get("display_name") or "").strip()
    if not code or not name:
        return {"error": "persona_code and display_name are required"}
    conn = db()
    try:
        row = conn.execute("SELECT persona_id, display_name FROM persona WHERE persona_code=?", (code,)).fetchone()
        if not row:
            return {"error": "not found"}
        old = row["display_name"]
        conn.execute("UPDATE persona SET display_name=? WHERE persona_code=?", (name, code))
        conn.execute(
            "INSERT INTO registry_event (event_time, event_type, actor, detail) VALUES (?,?,?,?)",
            (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "PERSON_RENAME",
                "org-directory",
                f"{code}: {old} → {name}",
            ),
        )
        conn.commit()
        return {"ok": True, "persona_code": code, "display_name": name, "previous": old}
    finally:
        conn.close()


def rbac_matrix():
    roles = rows("SELECT role_code, title FROM role ORDER BY role_id")
    perms = rows("SELECT perm_code, module FROM permission ORDER BY permission_id")
    links = {
        (r["role_code"], r["perm_code"])
        for r in rows(
            """SELECT role.role_code, perm.perm_code
               FROM role_permission rp
               JOIN role ON role.role_id = rp.role_id
               JOIN permission perm ON perm.permission_id = rp.permission_id"""
        )
    }
    return {
        "roles": roles,
        "permissions": perms,
        "cells": [
            {"role": role["role_code"], "permission": perm["perm_code"], "granted": (role["role_code"], perm["perm_code"]) in links}
            for role in roles
            for perm in perms
        ],
    }


def run_scenarios():
    conn = db()
    eng = RbacEngine(conn)
    out = []
    for subject, perm, rtype, rcode, label, expect_allow in SCENARIOS:
        res = eng.evaluate(subject, perm, rtype, rcode)
        res["label"] = label
        res["expected"] = expect_allow
        res["pass"] = res["allow"] == expect_allow
        out.append(res)
    conn.close()
    return out


def log_decision(conn, res: dict, mode: str = "ENFORCED"):
    """Persist an RBAC decision to the audit log.

    mode: 'ENFORCED' for real access decisions, 'SIMULATED' for dry-run / evaluate-via-GET.
    """
    conn.execute(
        """INSERT INTO rbac_decision_log (decided_at, subject, permission, resource_type, resource_code, allow, reason, mode)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            res.get("subject", ""),
            res.get("permission", ""),
            (res.get("resource") or {}).get("type", ""),
            (res.get("resource") or {}).get("code", ""),
            1 if res.get("allow") else 0,
            res.get("reason", ""),
            mode,
        ),
    )


def authorize(user: dict, permission: str, resource_type: str, resource_code: str) -> dict:
    """Evaluate an RBAC check for the currently logged-in user."""
    conn = db()
    try:
        eng = RbacEngine(conn)
        res = eng.evaluate(user["persona_code"], permission, resource_type, resource_code)
        log_decision(conn, res)
        conn.commit()
        return res
    finally:
        conn.close()


def my_rbac(user: dict) -> dict:
    """Return the current user's RBAC grants and held permissions."""
    conn = db()
    try:
        eng = RbacEngine(conn)
        grants = eng._grants(user["persona_code"])
        held = sorted(eng._held_permissions(grants))
        return {
            "ok": True,
            "persona_code": user["persona_code"],
            "display_name": user.get("display_name", ""),
            "grants": [
                {
                    "role": g["role_code"],
                    "scope_type": g["scope_type"],
                    "scope_code": g["scope_code"],
                    "permissions": sorted(g["permissions"]),
                }
                for g in grants
            ],
            "held_permissions": held,
        }
    finally:
        conn.close()


def evaluate_request(payload: dict, mode: str = "ENFORCED") -> dict:
    conn = db()
    try:
        eng = RbacEngine(conn)
        res = eng.evaluate(
            payload.get("subject", ""),
            payload.get("permission", ""),
            payload.get("resource_type", "UNIT"),
            payload.get("resource_code", ""),
        )
        log_decision(conn, res, mode=mode)
        conn.commit()
        res["mode"] = mode
        return res
    finally:
        conn.close()


PUBLIC_API = {"/api/health", "/api/auth/login", "/api/auth/accounts"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, fmt, *args):
        print("[org-directory]", self.address_string(), fmt % args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'none'; object-src 'none'; "
            "frame-ancestors 'none'; script-src 'self'; connect-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
            "form-action 'self'",
        )
        if self._secure():
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        super().end_headers()

    def _secure(self) -> bool:
        proto = (self.headers.get("X-Forwarded-Proto") or "").lower()
        return proto == "https"

    def _auth_user(self):
        conn = db()
        try:
            return um.user_from_conn(conn, self.headers)
        finally:
            conn.close()

    def _auth_user_post(self):
        """Authenticate for state-changing requests. Requires Bearer/header token (CSRF protection)."""
        token = um.request_token(self.headers, require_header=True)
        if not token:
            return None
        conn = db()
        try:
            return um.user_from_conn(conn, self.headers)
        finally:
            conn.close()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path.startswith("/api/"):
            user = None if path in PUBLIC_API else self._auth_user()
            if path not in PUBLIC_API and not user:
                return self._json({"error": "login required"}, 401)
            if path == "/api/auth/me":
                resp = {"ok": True, "user": um.public_me(user), "rbac": RBAC_STATUS}
                if um.DEMO_MODE:
                    resp["demo_password"] = um.DEMO_PASSWORD
                return self._json(resp)
            if path == "/api/rbac/me":
                return self._json(my_rbac(user))
            if path == "/api/auth/accounts":
                conn = db()
                try:
                    acc = [
                        {
                            "username": r["username"],
                            "display_name": r["display_name"],
                            "job_title": r["job_title"],
                            "category": r["category"],
                        }
                        for r in conn.execute(
                            """SELECT u.username, p.display_name, p.job_title, p.category
                               FROM app_user u JOIN persona p ON p.persona_id=u.persona_id
                               WHERE u.status='ACTIVE' ORDER BY p.category, p.display_name"""
                        )
                    ]
                    resp = {"accounts": acc}
                    if um.DEMO_MODE:
                        resp["demo_password"] = um.DEMO_PASSWORD
                    return self._json(resp)
                finally:
                    conn.close()
            if path == "/api/um/profile":
                q = parse_qs(parsed.query)
                code = (q.get("persona") or [None])[0]
                conn = db()
                try:
                    persona = um.resolve_persona(conn, user, code)
                    if not persona:
                        return self._json({"error": "not found or not allowed"}, 404)
                    return self._json(um.profile_payload(conn, persona))
                finally:
                    conn.close()
            if path == "/api/um/accounts":
                conn = db()
                try:
                    return self._json(um.list_accounts(conn, user))
                finally:
                    conn.close()
            if path.startswith("/api/um/documents/") and path != "/api/um/documents":
                try:
                    doc_id = int(path.rsplit("/", 1)[-1])
                except ValueError:
                    return self._json({"error": "bad id"}, 400)
                conn = db()
                try:
                    rec, path_or_err = um.open_document(conn, user, doc_id)
                    if rec is None:
                        return self._json({"error": path_or_err}, 404 if path_or_err == "not found" else 403)
                    data = Path(path_or_err).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", rec.get("mime") or "application/octet-stream")
                    from urllib.parse import quote
                    ascii_name = re.sub(r'[^\x20-\x7E]', '_', rec["original_name"])
                    ascii_name = re.sub(r'[\r\n"\\]', '_', ascii_name)
                    utf8_name = quote(rec["original_name"], safe='')
                    self.send_header(
                        "Content-Disposition",
                        f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{utf8_name}'
                    )
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                finally:
                    conn.close()
            if path == "/api/rbac/evaluate":
                q = parse_qs(parsed.query)
                payload = {
                    "subject": (q.get("subject") or [user["persona_code"]])[0],
                    "permission": (q.get("permission") or [""])[0],
                    "resource_type": (q.get("resource_type") or ["UNIT"])[0],
                    "resource_code": (q.get("resource_code") or [""])[0],
                }
                if not user["can_admin_users"]:
                    payload["subject"] = user["persona_code"]
                try:
                    return self._json(evaluate_request(payload, mode="SIMULATED"))
                except Exception as e:
                    return self._json({"error": "RBAC evaluation failed"}, 500)
            if path.startswith("/api/units/") and path != "/api/units":
                code = unquote(path.split("/")[-1])
                rec = one(
                    """SELECT u.*, d.department_code, d.name AS department_name, g.name AS unit_group_name,
                              a.walk_status, a.desk_recommendation, a.notes AS audit_notes
                       FROM nursing_unit u
                       JOIN department d ON d.department_id=u.department_id
                       JOIN unit_group g ON g.unit_group_id=u.unit_group_id
                       LEFT JOIN desk_audit a ON a.unit_code=u.unit_code
                       WHERE u.unit_code=?""",
                    (code,),
                )
                return self._json(rec if rec else {"error": "not found"}, 200 if rec else 404)
            fn = ROUTES.get(path)
            if not fn:
                return self._json({"error": "not found", "path": path}, 404)
            try:
                return self._json(fn(parse_qs(parsed.query)))
            except Exception as e:
                traceback.print_exc()
                return self._json({"error": "Internal server error"}, 500)
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length") or 0)
        if length > um.MAX_UPLOAD + 64_000:
            return self._json({"error": "payload too large"}, 413)
        raw = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type") or ""

        if path == "/api/auth/login":
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return self._json({"error": "invalid json"}, 400)
            conn = db()
            try:
                res = um.login(conn, payload.get("username", ""), payload.get("password", ""), client_ip=self.client_address[0])
                if not res.get("ok"):
                    return self._json(res, 401)
                return self._json(res, 200, extra=[("Set-Cookie", um.set_cookie(res["token"], secure=self._secure()))])
            finally:
                conn.close()

        user = self._auth_user_post()
        if not user:
            return self._json({"error": "login required — Authorization header is required for POST requests"}, 401)

        if path == "/api/auth/logout":
            conn = db()
            try:
                um.logout(conn, um.request_token(self.headers))
                return self._json({"ok": True}, 200, extra=[("Set-Cookie", um.clear_cookie(secure=self._secure()))])
            finally:
                conn.close()

        if path == "/api/um/documents":
            parts = um.parse_multipart(ctype, raw)
            filepart = parts.get("file")
            if not isinstance(filepart, dict):
                return self._json({"error": "file is required"}, 400)
            conn = db()
            try:
                res = um.save_document(
                    conn,
                    user,
                    parts.get("persona") if isinstance(parts.get("persona"), str) else None,
                    parts.get("doc_code") if isinstance(parts.get("doc_code"), str) else "",
                    filepart.get("filename") or "upload.bin",
                    filepart.get("mime") or "application/octet-stream",
                    filepart.get("data") or b"",
                )
                return self._json(res, 200 if res.get("ok") else 400)
            finally:
                conn.close()

        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._json({"error": "invalid json"}, 400)

        if path == "/api/um/profile":
            conn = db()
            try:
                payload["_headers"] = self.headers
                res = um.save_profile(conn, user, payload.get("persona"), payload)
                return self._json(res, 200 if res.get("ok") else 400)
            finally:
                conn.close()

        if path == "/api/rbac/people/rename":
            decision = authorize(user, "ORG_WRITE", "FACILITY", "AIGH")
            if not decision["allow"]:
                return self._json({"error": "not allowed", "reason": decision["reason"], "rbac": decision}, 403)
            res = rename_person(payload)
            return self._json(res, 200 if res.get("ok") else (404 if res.get("error") == "not found" else 400))
        return self._json({"error": "not found", "path": path}, 404)

    def _json(self, payload, status=200, extra=None):
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra or []:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


def _session_cleanup_loop():
    """Background thread: clean expired sessions every 15 minutes."""
    import time
    while True:
        time.sleep(900)
        try:
            with db_conn() as conn:
                um.cleanup_sessions(conn)
        except Exception:
            pass  # best-effort


def main():
    if not DB.exists():
        raise SystemExit("Database missing. Run: python3 seed.py")
    import threading
    t = threading.Thread(target=_session_cleanup_loop, daemon=True)
    t.start()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Org Directory P1 http://{HOST}:{PORT}")
    if um.DEMO_MODE:
        print("  DEMO_MODE=true  (shared password active)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
