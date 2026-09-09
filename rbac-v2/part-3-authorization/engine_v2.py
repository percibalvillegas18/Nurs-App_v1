"""Shadow RBAC v2 evaluator for Part 3.

This module is deliberately not imported by the current Org Directory API.
It evaluates versioned direct grants and constrained delegations, resolves
authoritative location ancestry, evaluates every applicable SoD rule, and
records immutable decision evidence.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


ENGINE_VERSION = "part3-reference-1"
VALID_RESOURCE_TYPES = {"FACILITY", "DEPARTMENT", "UNIT"}


class RbacV2Engine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def evaluate(
        self,
        *,
        account_uuid: str,
        permission_code: str,
        resource_type: str,
        resource_code: str,
        policy_version: str,
        request_id: str,
        at: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate and append one reproducible shadow decision.

        ``request_id`` is an idempotency key, not a bearer capability. A
        caller reusing it with a different subject, permission, resource,
        policy, or context must not receive the original decision.
        """
        request_id = str(request_id or "").strip()
        account_uuid = str(account_uuid or "").strip()
        at = at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        resource_type = (resource_type or "").upper().strip()
        permission_code = (permission_code or "").upper().strip()
        resource_code = (resource_code or "").strip()
        policy_version = (policy_version or "").strip()
        context_json = json.dumps(context or {}, sort_keys=True, separators=(",", ":"))

        if not request_id:
            return self._request_id_error("", "REQUEST_ID_REQUIRED", policy_version)

        account = self.conn.execute(
            "SELECT * FROM identity_account_v2 WHERE account_uuid=?",
            (account_uuid,),
        ).fetchone()
        policy = self.conn.execute(
            """SELECT * FROM authorization_policy_v2
               WHERE version_code=? AND status='ACTIVE'
                 AND effective_from <= ?
                 AND (effective_to IS NULL OR effective_to > ?)""",
            (policy_version, at, at),
        ).fetchone()

        prior = self._prior(request_id)
        if prior is not None:
            if self._prior_matches(
                prior, account, policy, permission_code, resource_type,
                resource_code, policy_version, context_json,
            ):
                return prior
            return self._request_id_error(request_id, "REQUEST_ID_REUSE", policy_version)

        if policy is None:
            return self._record(
                request_id, at, None, permission_code, resource_type, resource_code,
                None, "DENY", "POLICY_NOT_ACTIVE", "Policy is unknown or not active",
                None, None, None, policy_version, 0, context_json, [],
            )

        if account is None or account["account_status"] != "ACTIVE":
            return self._record(
                request_id, at, account["user_id"] if account else None,
                permission_code, resource_type, resource_code, None, "DENY",
                "ACCOUNT_NOT_ACTIVE", "Account is unknown or not active", None, None,
                policy["policy_id"], policy_version, 0, context_json, [],
            )

        permission = self.conn.execute(
            """SELECT * FROM authorization_permission_v2
               WHERE policy_id=? AND perm_code=? AND status='ACTIVE'""",
            (policy["policy_id"], permission_code),
        ).fetchone()
        if permission is None:
            return self._record(
                request_id, at, account["user_id"], permission_code, resource_type,
                resource_code, None, "DENY", "PERMISSION_UNKNOWN",
                "Permission is not active in the requested policy", None, None,
                policy["policy_id"], policy_version, 0, context_json, [],
            )

        resource = self._resource(resource_type, resource_code)
        if resource is None:
            return self._record(
                request_id, at, account["user_id"], permission_code,
                resource_type if resource_type in VALID_RESOURCE_TYPES else "UNKNOWN",
                resource_code, None, "DENY", "RESOURCE_NOT_ACTIVE",
                "Resource type/code is unknown, inactive, or has inactive ancestry",
                None, None, policy["policy_id"], policy_version,
                permission["requires_part4"], context_json, [],
            )

        target_scope = self._exact_scope(resource)
        if target_scope is None:
            return self._record(
                request_id, at, account["user_id"], permission_code, resource_type,
                resource_code, None, "DENY", "RESOURCE_SCOPE_NOT_REGISTERED",
                "Resource has no active validated authorization scope", None, None,
                policy["policy_id"], policy_version, permission["requires_part4"],
                context_json, [],
            )

        direct = self._direct_entitlements(account["user_id"], policy["policy_id"], at)
        delegated = self._delegated_entitlements(account["user_id"], policy["policy_id"], at)
        covering = [e for e in direct + delegated if self._scope_contains(e, resource)]
        matches = [e for e in covering if e["permission_id"] == permission["permission_id"]]

        sod = self._action_sod(
            policy["policy_id"], permission["permission_id"], covering, direct + delegated
        )
        blocking = [rule for rule in sod if rule["outcome"] == "BLOCK"]
        if blocking:
            return self._record(
                request_id, at, account["user_id"], permission_code, resource_type,
                resource_code, target_scope["scope_id"], "DENY", "SOD_CONFLICT",
                "One or more applicable separation-of-duties rules block the action",
                None, None, policy["policy_id"], policy_version,
                permission["requires_part4"], context_json, sod,
            )

        if not matches:
            return self._record(
                request_id, at, account["user_id"], permission_code, resource_type,
                resource_code, target_scope["scope_id"], "DENY", "NO_EFFECTIVE_ENTITLEMENT",
                "No effective direct grant or delegation contains the permission and resource",
                None, None, policy["policy_id"], policy_version,
                permission["requires_part4"], context_json, sod,
            )

        match = sorted(matches, key=lambda e: (e["delegation_id"] is not None, e["grant_id"]))[0]
        return self._record(
            request_id, at, account["user_id"], permission_code, resource_type,
            resource_code, target_scope["scope_id"], "ALLOW", "ENTITLEMENT_MATCH",
            "Effective entitlement and validated scope matched; Part 4 may still be required",
            match["grant_id"], match["delegation_id"], policy["policy_id"], policy_version,
            permission["requires_part4"], context_json, sod,
        )

    def validate_grant_activation(
        self, *, request_uuid: str, activated_by_account_uuid: str, at: str
    ) -> dict[str, Any]:
        """Validate an approved request before a controlled service creates its grant."""
        request = self.conn.execute(
            """SELECT q.*, r.policy_id, p.version_code, p.status AS policy_status,
                      s.status AS scope_status
               FROM access_grant_request_v2 q
               JOIN authorization_role_v2 r ON r.role_id=q.role_id AND r.status='ACTIVE'
               JOIN authorization_policy_v2 p ON p.policy_id=r.policy_id
               JOIN authorization_scope_v2 s ON s.scope_id=q.scope_id
               WHERE q.request_uuid=?""",
            (request_uuid,),
        ).fetchone()
        actor = self.conn.execute(
            "SELECT * FROM identity_account_v2 WHERE account_uuid=? AND account_status='ACTIVE'",
            (activated_by_account_uuid,),
        ).fetchone()
        if request is None or actor is None:
            return {"allow": False, "reason_code": "REQUEST_OR_ACTOR_NOT_ACTIVE", "sod_rule_ids": []}
        if request["status"] != "APPROVED" or request["policy_status"] != "ACTIVE" or request["scope_status"] != "ACTIVE":
            return {"allow": False, "reason_code": "REQUEST_NOT_ACTIVATABLE", "sod_rule_ids": []}
        if request["requested_from"] > at or (request["requested_to"] and request["requested_to"] <= at):
            return {"allow": False, "reason_code": "REQUEST_OUTSIDE_EFFECTIVE_WINDOW", "sod_rule_ids": []}
        if request["requires_dual_control"] and actor["user_id"] == request["approved_by_user_id"]:
            return {"allow": False, "reason_code": "DUAL_CONTROL_REQUIRED", "sod_rule_ids": []}

        proposed_permissions = {
            row[0] for row in self.conn.execute(
                "SELECT permission_id FROM authorization_role_permission_v2 WHERE role_id=?",
                (request["role_id"],),
            )
        }
        current = self._direct_entitlements(request["user_id"], request["policy_id"], at)
        current += self._delegated_entitlements(request["user_id"], request["policy_id"], at)
        proposed_scope = dict(self.conn.execute(
            "SELECT * FROM authorization_scope_v2 WHERE scope_id=?", (request["scope_id"],)
        ).fetchone())

        conflicts = []
        rules = self.conn.execute(
            "SELECT * FROM sod_rule_v2 WHERE policy_id=? AND status='ACTIVE'",
            (request["policy_id"],),
        ).fetchall()
        for rule in rules:
            pair = {rule["permission_a_id"], rule["permission_b_id"]}
            internal = pair <= proposed_permissions
            cross = False
            if pair & proposed_permissions:
                needed = pair - proposed_permissions
                cross = any(
                    e["permission_id"] in needed
                    and (rule["overlap_mode"] == "ANY_SCOPE" or self._scopes_overlap(proposed_scope, e))
                    for e in current
                )
            if internal or cross:
                conflicts.append(rule["rule_code"])
        has_block = any(
                self.conn.execute("SELECT enforcement FROM sod_rule_v2 WHERE rule_code=? AND policy_id=?", (code, request["policy_id"])).fetchone()[0] == "BLOCK"
                for code in conflicts
            )
        return {
            "allow": not has_block,
            "reason_code": "SOD_CONFLICT" if has_block else ("ACTIVATION_VALID_WITH_ALERT" if conflicts else "ACTIVATION_VALID"),
            "sod_rule_ids": sorted(conflicts),
        }

    def _direct_entitlements(self, user_id: int, policy_id: int, at: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT g.grant_id, NULL AS delegation_id, rp.permission_id,
                      s.scope_id, s.scope_type, s.facility_id, s.department_id, s.unit_id
               FROM access_grant_v2 g
               JOIN authorization_role_v2 ar
                 ON ar.role_id=g.role_id AND ar.policy_id=g.policy_id AND ar.status='ACTIVE'
               JOIN authorization_role_permission_v2 rp
                 ON rp.role_id=g.role_id AND rp.policy_id=g.policy_id
               JOIN authorization_permission_v2 ap
                 ON ap.permission_id=rp.permission_id AND ap.policy_id=rp.policy_id AND ap.status='ACTIVE'
               JOIN authorization_scope_v2 s ON s.scope_id=g.scope_id AND s.status='ACTIVE'
               WHERE g.user_id=? AND g.policy_id=? AND g.status='ACTIVE'
                 AND g.effective_from <= ?
                 AND (g.effective_to IS NULL OR g.effective_to > ?)""",
            (user_id, policy_id, at, at),
        ).fetchall()
        return [dict(row) for row in rows]

    def _delegated_entitlements(self, user_id: int, policy_id: int, at: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT g.grant_id, d.delegation_id, dp.permission_id,
                      s.scope_id, s.scope_type, s.facility_id, s.department_id, s.unit_id
               FROM delegation_v2 d
               JOIN delegation_permission_v2 dp ON dp.delegation_id=d.delegation_id
               JOIN access_grant_v2 g ON g.grant_id=d.source_grant_id
               JOIN authorization_role_v2 ar
                 ON ar.role_id=g.role_id AND ar.policy_id=g.policy_id AND ar.status='ACTIVE'
               JOIN authorization_permission_v2 ap
                 ON ap.permission_id=dp.permission_id AND ap.policy_id=d.policy_id AND ap.status='ACTIVE'
               JOIN authorization_scope_v2 s ON s.scope_id=d.scope_id AND s.status='ACTIVE'
               WHERE d.delegate_user_id=? AND d.policy_id=? AND d.status='ACTIVE'
                 AND d.starts_at <= ? AND d.expires_at > ?
                 AND g.status='ACTIVE' AND g.effective_from <= ?
                 AND (g.effective_to IS NULL OR g.effective_to > ?)""",
            (user_id, policy_id, at, at, at, at),
        ).fetchall()
        return [dict(row) for row in rows]

    def _action_sod(
        self, policy_id: int, requested_permission_id: int,
        covering: list[dict[str, Any]], all_entitlements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        covering_held = {e["permission_id"] for e in covering}
        all_held = {e["permission_id"] for e in all_entitlements}
        out = []
        for rule in self.conn.execute(
            "SELECT * FROM sod_rule_v2 WHERE policy_id=? AND status='ACTIVE' ORDER BY rule_code",
            (policy_id,),
        ):
            pair = {rule["permission_a_id"], rule["permission_b_id"]}
            held = all_held if rule["overlap_mode"] == "ANY_SCOPE" else covering_held
            if requested_permission_id in pair and pair <= held:
                out.append({
                    "sod_rule_id": rule["sod_rule_id"],
                    "rule_code": rule["rule_code"],
                    "outcome": rule["enforcement"],
                })
        return out

    def _resource(self, resource_type: str, code: str) -> dict[str, Any] | None:
        if resource_type == "FACILITY":
            row = self.conn.execute(
                "SELECT facility_id, facility_code FROM facility WHERE facility_code=? AND status='ACTIVE'",
                (code,),
            ).fetchone()
            return dict(row) | {"type": "FACILITY", "department_id": None, "unit_id": None} if row else None
        if resource_type == "DEPARTMENT":
            row = self.conn.execute(
                """SELECT d.department_id, d.department_code, d.facility_id, f.facility_code
                   FROM department d JOIN facility f ON f.facility_id=d.facility_id
                   WHERE d.department_code=? AND d.status='ACTIVE' AND f.status='ACTIVE'""",
                (code,),
            ).fetchone()
            return dict(row) | {"type": "DEPARTMENT", "unit_id": None} if row else None
        if resource_type == "UNIT":
            row = self.conn.execute(
                """SELECT u.unit_id, u.unit_code, u.department_id, d.department_code,
                          d.facility_id, f.facility_code
                   FROM nursing_unit u JOIN department d ON d.department_id=u.department_id
                   JOIN facility f ON f.facility_id=d.facility_id
                   WHERE u.unit_code=? AND u.status='ACTIVE' AND d.status='ACTIVE' AND f.status='ACTIVE'""",
                (code,),
            ).fetchone()
            return dict(row) | {"type": "UNIT"} if row else None
        return None

    def _exact_scope(self, resource: dict[str, Any]) -> sqlite3.Row | None:
        column = {"FACILITY": "facility_id", "DEPARTMENT": "department_id", "UNIT": "unit_id"}[resource["type"]]
        return self.conn.execute(
            f"SELECT * FROM authorization_scope_v2 WHERE scope_type=? AND {column}=? AND status='ACTIVE'",
            (resource["type"], resource[column]),
        ).fetchone()

    @staticmethod
    def _scope_contains(scope: dict[str, Any], resource: dict[str, Any]) -> bool:
        if scope["scope_type"] == "FACILITY":
            return scope["facility_id"] == resource.get("facility_id")
        if scope["scope_type"] == "DEPARTMENT":
            return resource["type"] != "FACILITY" and scope["department_id"] == resource.get("department_id")
        return resource["type"] == "UNIT" and scope["unit_id"] == resource.get("unit_id")

    def _scopes_overlap(self, first: dict[str, Any], second: dict[str, Any]) -> bool:
        first_resource = self._scope_anchor(first)
        second_resource = self._scope_anchor(second)
        return self._scope_contains(first, second_resource) or self._scope_contains(second, first_resource)

    def _scope_anchor(self, scope: dict[str, Any]) -> dict[str, Any]:
        if scope["scope_type"] == "FACILITY":
            return {"type": "FACILITY", "facility_id": scope["facility_id"], "department_id": None, "unit_id": None}
        if scope["scope_type"] == "DEPARTMENT":
            facility_id = self.conn.execute("SELECT facility_id FROM department WHERE department_id=?", (scope["department_id"],)).fetchone()[0]
            return {"type": "DEPARTMENT", "facility_id": facility_id, "department_id": scope["department_id"], "unit_id": None}
        row = self.conn.execute(
            "SELECT u.department_id, d.facility_id FROM nursing_unit u JOIN department d ON d.department_id=u.department_id WHERE u.unit_id=?",
            (scope["unit_id"],),
        ).fetchone()
        return {"type": "UNIT", "facility_id": row["facility_id"], "department_id": row["department_id"], "unit_id": scope["unit_id"]}

    @staticmethod
    def _prior_matches(
        prior: dict[str, Any], account: sqlite3.Row | None, policy: sqlite3.Row | None,
        permission_code: str, resource_type: str, resource_code: str,
        policy_version: str, context_json: str,
    ) -> bool:
        if account is None or account["account_status"] != "ACTIVE" or policy is None:
            return False
        resource = prior.get("resource") or {}
        return (
            prior.get("user_id") == account["user_id"]
            and prior.get("permission_code") == permission_code
            and resource.get("type") == resource_type
            and resource.get("code") == resource_code
            and prior.get("policy_version") == policy_version
            and prior.get("context_json") == context_json
        )

    @staticmethod
    def _request_id_error(request_id: str, reason_code: str, policy_version: str) -> dict[str, Any]:
        return {
            "decision_id": None,
            "request_id": request_id,
            "decision": "ERROR",
            "allow": False,
            "reason_code": reason_code,
            "policy_version": policy_version,
            "matched_grant_id": None,
            "delegation_id": None,
            "sod_rule_ids": [],
            "requires_part4": False,
        }

    def _prior(self, request_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM authorization_decision_v2 WHERE request_id=?", (request_id,)
        ).fetchone()
        return self._decision_dict(row) if row else None

    def _record(
        self, request_id: str, at: str, user_id: int | None, permission_code: str,
        resource_type: str, resource_code: str, resolved_scope_id: int | None,
        decision: str, reason_code: str, reason_detail: str,
        matched_grant_id: int | None, delegation_id: int | None,
        policy_id: int | None, policy_version: str, requires_part4: int,
        context_json: str, sod: list[dict[str, Any]],
    ) -> dict[str, Any]:
        decision_id = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO authorization_decision_v2
               (decision_id,request_id,decided_at,user_id,permission_code,resource_type,
                resource_code,resolved_scope_id,decision,reason_code,reason_detail,
                matched_grant_id,delegation_id,policy_id,policy_version,requires_part4,
                context_json,engine_version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (decision_id, request_id, at, user_id, permission_code, resource_type,
             resource_code, resolved_scope_id, decision, reason_code, reason_detail,
             matched_grant_id, delegation_id, policy_id, policy_version,
             requires_part4, context_json, ENGINE_VERSION),
        )
        for rule in sod:
            self.conn.execute(
                "INSERT INTO authorization_decision_sod_v2 (decision_id,sod_rule_id,outcome) VALUES (?,?,?)",
                (decision_id, rule["sod_rule_id"], rule["outcome"]),
            )
        row = self.conn.execute(
            "SELECT * FROM authorization_decision_v2 WHERE decision_id=?", (decision_id,)
        ).fetchone()
        return self._decision_dict(row)

    def _decision_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        sod = [
            r[0] for r in self.conn.execute(
                """SELECT s.rule_code FROM authorization_decision_sod_v2 ds
                   JOIN sod_rule_v2 s ON s.sod_rule_id=ds.sod_rule_id
                   WHERE ds.decision_id=? ORDER BY s.rule_code""",
                (row["decision_id"],),
            )
        ]
        return {
            "decision_id": row["decision_id"],
            "request_id": row["request_id"],
            "decision": row["decision"],
            "allow": row["decision"] == "ALLOW",
            "reason_code": row["reason_code"],
            "permission_code": row["permission_code"],
            "user_id": row["user_id"],
            "context_json": row["context_json"],
            "policy_version": row["policy_version"],
            "matched_grant_id": row["matched_grant_id"],
            "delegation_id": row["delegation_id"],
            "sod_rule_ids": sod,
            "requires_part4": bool(row["requires_part4"]),
            "resource": {"type": row["resource_type"], "code": row["resource_code"]},
        }
