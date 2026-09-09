"""RBAC evaluator: permission ∩ scope ∩ SoD.

Status: v1 prototype contract applied 2026-09-09; not a production identity or clinical-transaction authorization system.
Copy this module into HIS consumers. It only needs a DB connection with
role, role_permission, permission, role_grant, persona, sod_rule,
nursing_unit, department, and facility.

The v1 contract is retained for compatibility, but evaluation is deliberately
fail-closed for unknown/inactive resources.  A facility grant is not a
wildcard: the requested resource must resolve through the same active facility
ancestry as the grant.
"""
from __future__ import annotations

import sqlite3
from datetime import date


VALID_RESOURCE_TYPES = {"FACILITY", "DEPARTMENT", "UNIT"}


class RbacEngine:
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def evaluate(self, subject: str, permission: str, resource_type: str, resource_code: str) -> dict:
        subject = (subject or "").strip()
        permission = (permission or "").strip().upper()
        resource_type = (resource_type or "").strip().upper()
        resource_code = (resource_code or "").strip()

        # Never allow a malformed or unknown resource to match a broad grant.
        # This is especially important for FACILITY grants, which used to
        # return True without resolving the requested resource at all.
        if resource_type not in VALID_RESOURCE_TYPES or not resource_code:
            return self._deny(
                subject, permission, resource_type, resource_code,
                "Unknown or malformed resource",
            )
        if not self._resource_exists(resource_type, resource_code):
            return self._deny(
                subject, permission, resource_type, resource_code,
                "Unknown or inactive resource",
            )

        grants = self._grants(subject)
        if not grants:
            return self._deny(subject, permission, resource_type, resource_code, "No active role grant for subject")

        held = self._held_permissions(grants)
        for sod in self._sod_hits(held):
            if permission in (sod["perm_a"], sod["perm_b"]):
                # A standing waiver is legacy prototype behavior; production
                # must replace it with event-scoped break-glass.
                if not self._waived(sod, grants):
                    return self._deny(
                        subject, permission, resource_type, resource_code,
                        f"SoD: {sod['message']}",
                    )

        matching = []
        for g in grants:
            if permission not in g["permissions"]:
                continue
            if self._scope_contains(g["scope_type"], g["scope_code"], resource_type, resource_code):
                matching.append(g)

        if not matching:
            has_perm = permission in held
            reason = (
                "Permission granted but resource is outside scope"
                if has_perm
                else f"Role does not include permission {permission}"
            )
            return self._deny(subject, permission, resource_type, resource_code, reason)

        g = matching[0]
        return {
            "allow": True,
            "subject": subject,
            "permission": permission,
            "resource": {"type": resource_type, "code": resource_code},
            "reason": f"{g['role_code']} @ {g['scope_type']}:{g['scope_code']}",
            "matched_grant": {
                "role": g["role_code"],
                "scope_type": g["scope_type"],
                "scope_code": g["scope_code"],
            },
        }

    def _resource_exists(self, resource_type: str, resource_code: str) -> bool:
        """Resolve a resource and its active facility ancestry.

        v1 grants contain free-text scope codes, so this check is the runtime
        guard until all consumers have moved to the strongly referenced v2
        scope tables.
        """
        if resource_type == "FACILITY":
            sql = "SELECT 1 FROM facility WHERE facility_code=? AND status='ACTIVE'"
        elif resource_type == "DEPARTMENT":
            sql = """SELECT 1
                     FROM department d JOIN facility f ON f.facility_id=d.facility_id
                     WHERE d.department_code=? AND d.status='ACTIVE' AND f.status='ACTIVE'"""
        elif resource_type == "UNIT":
            sql = """SELECT 1
                     FROM nursing_unit u
                     JOIN department d ON d.department_id=u.department_id
                     JOIN facility f ON f.facility_id=d.facility_id
                     WHERE u.unit_code=? AND u.status='ACTIVE'
                       AND d.status='ACTIVE' AND f.status='ACTIVE'"""
        else:
            return False
        return self.conn.execute(sql, (resource_code,)).fetchone() is not None

    def _grants(self, subject: str) -> list[dict]:
        today = date.today().isoformat()
        rows = self.conn.execute(
            """
            SELECT g.grant_id, g.scope_type, g.scope_code, r.role_code, r.role_id
            FROM role_grant g
            JOIN persona p ON p.persona_id = g.persona_id
            JOIN role r ON r.role_id = g.role_id
            WHERE p.persona_code = ?
              AND g.status = 'ACTIVE'
              AND g.effective_from <= ?
              AND (g.effective_to IS NULL OR g.effective_to >= ?)
            """,
            (subject, today, today),
        ).fetchall()
        if not rows:
            return []
        # Batch-fetch permissions for all role_ids at once (eliminates N+1)
        role_ids = list({r["role_id"] for r in rows})
        placeholders = ",".join("?" for _ in role_ids)
        perm_rows = self.conn.execute(
            f"""SELECT rp.role_id, perm.perm_code
                FROM role_permission rp
                JOIN permission perm ON perm.permission_id = rp.permission_id
                WHERE rp.role_id IN ({placeholders})""",
            role_ids,
        ).fetchall()
        perms_by_role: dict[int, list[str]] = {}
        for pr in perm_rows:
            perms_by_role.setdefault(pr["role_id"], []).append(pr["perm_code"])
        out = []
        for row in rows:
            d = dict(row)
            d["permissions"] = perms_by_role.get(d["role_id"], [])
            out.append(d)
        return out

    def _held_permissions(self, grants: list[dict]) -> set[str]:
        held: set[str] = set()
        for g in grants:
            held.update(g["permissions"])
        return held

    def _sod_hits(self, held: set[str]) -> list[dict]:
        rules = [dict(r) for r in self.conn.execute("SELECT * FROM sod_rule").fetchall()]
        return [
            rule for rule in rules
            if rule["perm_a"] in held and rule["perm_b"] in held
        ]

    def _sod_hit(self, held: set[str], grants: list[dict]):
        """Compatibility helper for consumers that used the old private method."""
        hits = self._sod_hits(held)
        return hits[0] if hits else None

    def _waived(self, rule: dict, grants: list[dict]) -> bool:
        waive = {x.strip() for x in (rule.get("waive_roles") or "").split(",") if x.strip()}
        return any(g["role_code"] in waive for g in grants)

    def _scope_contains(self, gtype: str, gcode: str, rtype: str, rcode: str) -> bool:
        gtype, rtype = (gtype or "").upper(), (rtype or "").upper()
        gcode, rcode = (gcode or "").strip(), (rcode or "").strip()
        if gtype == "FACILITY":
            if rtype == "FACILITY":
                return gcode == rcode and self._resource_exists("FACILITY", rcode)
            if rtype == "DEPARTMENT":
                row = self.conn.execute(
                    """SELECT f.facility_code
                       FROM department d
                       JOIN facility f ON f.facility_id=d.facility_id
                       WHERE d.department_code=? AND d.status='ACTIVE' AND f.status='ACTIVE'""",
                    (rcode,),
                ).fetchone()
                return bool(row) and row["facility_code"] == gcode
            if rtype == "UNIT":
                row = self.conn.execute(
                    """SELECT f.facility_code
                       FROM nursing_unit u
                       JOIN department d ON d.department_id=u.department_id
                       JOIN facility f ON f.facility_id=d.facility_id
                       WHERE u.unit_code=? AND u.status='ACTIVE'
                         AND d.status='ACTIVE' AND f.status='ACTIVE'""",
                    (rcode,),
                ).fetchone()
                return bool(row) and row["facility_code"] == gcode
            return False
        if gtype == "DEPARTMENT":
            if rtype == "DEPARTMENT":
                return gcode == rcode
            if rtype == "UNIT":
                row = self.conn.execute(
                    """SELECT d.department_code
                       FROM nursing_unit u
                       JOIN department d ON d.department_id = u.department_id
                       JOIN facility f ON f.facility_id=d.facility_id
                       WHERE u.unit_code = ? AND u.status='ACTIVE'
                         AND d.status='ACTIVE' AND f.status='ACTIVE'""",
                    (rcode,),
                ).fetchone()
                return bool(row) and row["department_code"] == gcode
            return False
        if gtype == "UNIT":
            return rtype == "UNIT" and gcode == rcode
        return False

    def _deny(self, subject, permission, resource_type, resource_code, reason):
        return {
            "allow": False,
            "subject": subject,
            "permission": permission,
            "resource": {"type": resource_type, "code": resource_code},
            "reason": reason,
            "matched_grant": None,
        }
