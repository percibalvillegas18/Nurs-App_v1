"""RBAC evaluator: permission ∩ scope ∩ SoD.

Status: APPROVED and applied 2026-09-09 (Org Directory + HNWMS contract).
Copy this module into HIS consumers. It only needs a DB connection with
role, role_permission, permission, role_grant, persona, sod_rule,
nursing_unit, department.
"""
from __future__ import annotations

import sqlite3
from datetime import date


class RbacEngine:
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def evaluate(self, subject: str, permission: str, resource_type: str, resource_code: str) -> dict:
        grants = self._grants(subject)
        if not grants:
            return self._deny(subject, permission, resource_type, resource_code, "No active role grant for subject")

        held = self._held_permissions(grants)
        sod = self._sod_hit(held, grants)
        if sod and permission in (sod["perm_a"], sod["perm_b"]):
            # SYS_ADMIN waive
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

    def _sod_hit(self, held: set[str], grants: list[dict]):
        rules = [dict(r) for r in self.conn.execute("SELECT * FROM sod_rule").fetchall()]
        for rule in rules:
            if rule["perm_a"] in held and rule["perm_b"] in held:
                return rule
        return None

    def _waived(self, rule: dict, grants: list[dict]) -> bool:
        waive = {x.strip() for x in (rule.get("waive_roles") or "").split(",") if x.strip()}
        return any(g["role_code"] in waive for g in grants)

    def _scope_contains(self, gtype: str, gcode: str, rtype: str, rcode: str) -> bool:
        gtype, rtype = gtype.upper(), rtype.upper()
        if gtype == "FACILITY":
            return True
        if rtype == "FACILITY":
            return False
        if gtype == "DEPARTMENT":
            if rtype == "DEPARTMENT":
                return gcode == rcode
            if rtype == "UNIT":
                row = self.conn.execute(
                    """SELECT d.department_code
                       FROM nursing_unit u
                       JOIN department d ON d.department_id = u.department_id
                       WHERE u.unit_code = ?""",
                    (rcode,),
                ).fetchone()
                return bool(row) and dict(row)["department_code"] == gcode
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
