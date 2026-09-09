"""Shadow clinical-safety composer for HNWMS RBAC v2 Part 4."""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any


ENGINE_VERSION = "part4-reference-1"
PASS_STATES = {
    "employment_state", "license_state", "credential_state", "competency_state",
    "training_state", "unit_authorization_state", "occupational_state",
    "shift_context_state",
}
VERDICT_WEIGHT = {"ALLOW": 0, "INFORM": 1, "WARN": 2, "BLOCK": 3, "ERROR": 4}


class ClinicalSafetyEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def evaluate(
        self, *, account_uuid: str, staff_uuid: str, permission_code: str,
        unit_code: str, candidate_hash: str, safety_policy_version: str,
        request_id: str, at: str, authorization_decision_id: str | None = None,
        break_glass_event_uuid: str | None = None,
    ) -> dict[str, Any]:
        prior = self.conn.execute(
            "SELECT * FROM clinical_safety_decision_v2 WHERE request_id=?", (request_id,)
        ).fetchone()
        if prior:
            return self._decision_dict(prior)

        policy = self.conn.execute(
            """SELECT * FROM clinical_safety_policy_v2
               WHERE version_code=? AND status='ACTIVE' AND effective_from<=?
                 AND (effective_to IS NULL OR effective_to>?)""",
            (safety_policy_version, at, at),
        ).fetchone()
        account = self.conn.execute(
            "SELECT * FROM identity_account_v2 WHERE account_uuid=?", (account_uuid,)
        ).fetchone()
        staff = self.conn.execute(
            "SELECT * FROM staff_member_v2 WHERE staff_uuid=?", (staff_uuid,)
        ).fetchone()
        unit = self.conn.execute(
            """SELECT u.* FROM nursing_unit u JOIN department d ON d.department_id=u.department_id
               JOIN facility f ON f.facility_id=d.facility_id
               WHERE u.unit_code=? AND u.status='ACTIVE' AND d.status='ACTIVE' AND f.status='ACTIVE'""",
            (unit_code,),
        ).fetchone()
        if policy is None:
            return self._record(request_id, at, None, None, staff, permission_code,
                                unit, candidate_hash, None, None, "ERROR", "SAFETY_POLICY_NOT_ACTIVE",
                                "Safety policy is unknown or inactive", None, safety_policy_version, [])
        if account is None or account["account_status"] != "ACTIVE" or staff is None or staff["record_status"] != "ACTIVE" or unit is None:
            return self._record(request_id, at, None, None, staff, permission_code, unit,
                                candidate_hash, None, None, "BLOCK", "SUBJECT_OR_UNIT_NOT_ACTIVE",
                                "Account, staff, or unit is unknown/inactive", policy["safety_policy_id"],
                                safety_policy_version, [])
        linked = self.conn.execute(
            "SELECT 1 FROM identity_staff_link_v2 WHERE user_id=? AND staff_id=?",
            (account["user_id"], staff["staff_id"]),
        ).fetchone()
        if not linked:
            return self._record(request_id, at, None, None, staff, permission_code, unit,
                                candidate_hash, None, None, "BLOCK", "IDENTITY_STAFF_MISMATCH",
                                "Account is not linked to the requested staff identity",
                                policy["safety_policy_id"], safety_policy_version, [])

        profile = self.conn.execute(
            """SELECT pp.*, p.perm_code FROM safety_permission_profile_v2 pp
               JOIN authorization_permission_v2 p ON p.permission_id=pp.permission_id
               WHERE pp.safety_policy_id=? AND pp.authorization_policy_id=?
                 AND p.perm_code=? AND pp.status='ACTIVE'""",
            (policy["safety_policy_id"], policy["authorization_policy_id"], permission_code),
        ).fetchone()
        if profile is None:
            return self._record(request_id, at, None, None, staff, permission_code, unit,
                                candidate_hash, None, None, "ERROR", "PERMISSION_SAFETY_PROFILE_MISSING",
                                "Permission has no active Part 4 profile", policy["safety_policy_id"],
                                safety_policy_version, [])

        auth = self._valid_authorization(
            authorization_decision_id, account["user_id"], permission_code, unit_code,
            policy["authorization_policy_id"], at,
            policy["authorization_decision_ttl_seconds"],
        )
        break_glass = self._valid_break_glass(
            break_glass_event_uuid, account["user_id"], staff["staff_id"],
            profile["permission_id"], unit, policy["safety_policy_id"], at,
        )
        if auth is None and break_glass is None:
            return self._record(request_id, at, None, None, staff, permission_code, unit,
                                candidate_hash, None, None, "BLOCK", "AUTHORIZATION_REQUIRED",
                                "Neither a matching Part 3 allow nor active break-glass permission exists",
                                policy["safety_policy_id"], safety_policy_version, [])

        eligibility = None
        if profile["requires_eligibility"]:
            eligibility = self._latest_eligibility(staff["staff_id"], unit["unit_id"], at)
            if eligibility is None or eligibility["source_state"] != "AVAILABLE" or any(eligibility[name] == "UNKNOWN" for name in PASS_STATES):
                return self._record(request_id, at, auth, break_glass, staff, permission_code,
                                    unit, candidate_hash, eligibility, None, "ERROR",
                                    "ELIGIBILITY_SOURCE_UNAVAILABLE_OR_STALE",
                                    "Fresh authoritative eligibility evidence is unavailable",
                                    policy["safety_policy_id"], safety_policy_version, [])
            failed = sorted(name for name in PASS_STATES if eligibility[name] == "FAIL")
            if failed:
                return self._record(request_id, at, auth, break_glass, staff, permission_code,
                                    unit, candidate_hash, eligibility, None, "BLOCK",
                                    "ELIGIBILITY_BLOCK", "Failed eligibility factors: " + ",".join(failed),
                                    policy["safety_policy_id"], safety_policy_version, [])

        evaluation = None
        exceptions: list[int] = []
        final_result = "ALLOW"
        final_reason = "SAFETY_CONTROLS_PASS"
        detail = "Authorization, eligibility, and guardrail requirements pass"
        if profile["requires_guardrails"]:
            evaluation = self.conn.execute(
                """SELECT * FROM guardrail_evaluation_v2
                   WHERE safety_policy_id=? AND candidate_hash=? AND staff_id=? AND unit_id=?
                     AND status='COMPLETE' AND source_state='AVAILABLE'
                     AND evaluated_at<=? AND valid_until>?
                   ORDER BY evaluated_at DESC LIMIT 1""",
                (policy["safety_policy_id"], candidate_hash, staff["staff_id"], unit["unit_id"], at, at),
            ).fetchone()
            if evaluation is None:
                return self._record(request_id, at, auth, break_glass, staff, permission_code,
                                    unit, candidate_hash, eligibility, None, "ERROR",
                                    "GUARDRAIL_SOURCE_UNAVAILABLE_OR_STALE",
                                    "Fresh transaction-bound guardrail evaluation is unavailable",
                                    policy["safety_policy_id"], safety_policy_version, [])
            results = self.conn.execute(
                """SELECT rr.*, ra.exception_allowed FROM guardrail_rule_result_v2 rr
                   JOIN guardrail_rule_adapter_v2 ra ON ra.rule_adapter_id=rr.rule_adapter_id
                   WHERE rr.guardrail_evaluation_id=? ORDER BY rr.external_rule_code""",
                (evaluation["guardrail_evaluation_id"],),
            ).fetchall()
            if not results:
                return self._record(request_id, at, auth, break_glass, staff, permission_code,
                                    unit, candidate_hash, eligibility, evaluation, "ERROR",
                                    "GUARDRAIL_RESULTS_MISSING", "Guardrail evaluation contains no rule results",
                                    policy["safety_policy_id"], safety_policy_version, [])

            remaining = []
            for result in results:
                if result["effective_verdict"] == "BLOCK":
                    exception_id = self._effective_exception(
                        result, candidate_hash, staff["staff_id"], unit["unit_id"],
                        policy["authorization_policy_id"], at,
                    )
                    if exception_id is not None:
                        exceptions.append(exception_id)
                        continue
                remaining.append(result["effective_verdict"])
            strictest = max(remaining or ["ALLOW"], key=lambda value: VERDICT_WEIGHT[value])
            declared = max((row["effective_verdict"] for row in results), key=lambda value: VERDICT_WEIGHT[value])
            if declared != evaluation["declared_verdict"]:
                return self._record(request_id, at, auth, break_glass, staff, permission_code,
                                    unit, candidate_hash, eligibility, evaluation, "ERROR",
                                    "GUARDRAIL_VERDICT_MISMATCH",
                                    "Declared evaluation verdict does not match immutable rule results",
                                    policy["safety_policy_id"], safety_policy_version, exceptions)
            if strictest in ("BLOCK", "ERROR"):
                final_result = strictest
                final_reason = "GUARDRAIL_BLOCK" if strictest == "BLOCK" else "GUARDRAIL_ERROR"
                detail = "One or more unexcepted guardrail results prevent the transaction"
            elif strictest == "WARN":
                final_result = "WARN"
                final_reason = "GUARDRAIL_WARNING"
                detail = "Guardrail warning requires the approved escalation workflow"

        return self._record(request_id, at, auth, break_glass, staff, permission_code, unit,
                            candidate_hash, eligibility, evaluation, final_result, final_reason,
                            detail, policy["safety_policy_id"], safety_policy_version, exceptions)

    def validate_break_glass_activation(self, *, event_uuid: str, unit_code: str, at: str) -> dict[str, Any]:
        event = self.conn.execute(
            """SELECT e.*, b.clinical_bundle, b.status AS bundle_status,
                      b.max_duration_seconds, sp.status AS policy_status,
                      sp.max_break_glass_seconds
               FROM break_glass_event_v2 e JOIN break_glass_bundle_v2 b ON b.bundle_id=e.bundle_id
               JOIN clinical_safety_policy_v2 sp ON sp.safety_policy_id=e.safety_policy_id
               WHERE e.event_uuid=?""",
            (event_uuid,),
        ).fetchone()
        unit = self.conn.execute("SELECT * FROM nursing_unit WHERE unit_code=? AND status='ACTIVE'", (unit_code,)).fetchone()
        if event is None or unit is None or event["status"] != "REQUESTED":
            return {"allow": False, "reason_code": "EVENT_NOT_ACTIVATABLE"}
        if event["target_unit_id"] != unit["unit_id"]:
            return {"allow": False, "reason_code": "BREAK_GLASS_TARGET_MISMATCH"}
        if event["authentication_assurance"] != "STEP_UP" or event["policy_status"] != "ACTIVE" or event["bundle_status"] != "APPROVED":
            return {"allow": False, "reason_code": "ACTIVATION_CONTROL_FAILED"}
        if not self._scope_contains_unit(event["scope_id"], unit):
            return {"allow": False, "reason_code": "BREAK_GLASS_SCOPE_MISMATCH"}
        if event["clinical_bundle"]:
            eligibility = self._latest_eligibility(event["staff_id"], unit["unit_id"], at)
            if eligibility is None or eligibility["source_state"] != "AVAILABLE" or any(eligibility[name] != "PASS" for name in PASS_STATES):
                return {"allow": False, "reason_code": "BREAK_GLASS_ELIGIBILITY_BLOCK"}
        return {"allow": True, "reason_code": "BREAK_GLASS_ACTIVATION_VALID"}

    def _valid_authorization(self, decision_id: str | None, user_id: int,
                             permission: str, unit_code: str, policy_id: int,
                             at: str, ttl_seconds: int) -> str | None:
        if decision_id is None:
            return None
        row = self.conn.execute(
            """SELECT * FROM authorization_decision_v2
               WHERE decision_id=? AND user_id=? AND permission_code=?
                 AND resource_type='UNIT' AND resource_code=?
                 AND policy_id=? AND decision='ALLOW' AND decided_at<=?
                 AND (julianday(?)-julianday(decided_at))*86400.0 <= ?+0.5""",
            (decision_id, user_id, permission, unit_code, policy_id, at, at, ttl_seconds),
        ).fetchone()
        return row["decision_id"] if row else None

    def _valid_break_glass(self, event_uuid: str | None, user_id: int, staff_id: int, permission_id: int, unit: sqlite3.Row, policy_id: int, at: str) -> sqlite3.Row | None:
        if event_uuid is None:
            return None
        row = self.conn.execute(
            """SELECT e.* FROM break_glass_event_v2 e
               JOIN break_glass_bundle_permission_v2 bp ON bp.bundle_id=e.bundle_id
               WHERE e.event_uuid=? AND e.user_id=? AND e.staff_id=?
                 AND e.safety_policy_id=? AND bp.permission_id=?
                 AND e.status='ACTIVE' AND e.activated_at<=? AND e.expires_at>?""",
            (event_uuid, user_id, staff_id, policy_id, permission_id, at, at),
        ).fetchone()
        return row if row and row["target_unit_id"] == unit["unit_id"] and self._scope_contains_unit(row["scope_id"], unit) else None

    def _latest_eligibility(self, staff_id: int, unit_id: int, at: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """SELECT * FROM clinical_eligibility_snapshot_v2
               WHERE staff_id=? AND unit_id=? AND captured_at<=? AND valid_until>?
               ORDER BY captured_at DESC LIMIT 1""",
            (staff_id, unit_id, at, at),
        ).fetchone()

    def _effective_exception(self, result: sqlite3.Row, candidate_hash: str,
                             staff_id: int, unit_id: int, auth_policy_id: int,
                             at: str) -> int | None:
        if not result["exception_allowed"]:
            return None
        rows = self.conn.execute(
            """SELECT x.* FROM guardrail_exception_request_v2 x
               WHERE x.rule_result_id=? AND x.candidate_hash=? AND x.staff_id=? AND x.unit_id=?
                 AND x.status='APPROVED' AND x.starts_at<=? AND x.expires_at>?
               ORDER BY x.exception_id""",
            (result["rule_result_id"], candidate_hash, staff_id, unit_id, at, at),
        ).fetchall()
        for row in rows:
            valid_approvals = self.conn.execute(
                """SELECT COUNT(*) FROM guardrail_exception_approval_v2 a
                   JOIN authorization_decision_v2 d ON d.decision_id=a.authorization_decision_id
                   WHERE a.exception_id=? AND a.decision='APPROVE'
                     AND d.decision='ALLOW' AND d.user_id=a.approver_user_id
                     AND d.permission_code='GUARDRAIL_EXCEPTION_APPROVE'
                     AND d.resource_type='UNIT' AND d.policy_id=?
                     AND d.resource_code=(SELECT unit_code FROM nursing_unit WHERE unit_id=?)""",
                (row["exception_id"], auth_policy_id, unit_id),
            ).fetchone()[0]
            rejected = self.conn.execute(
                "SELECT 1 FROM guardrail_exception_approval_v2 WHERE exception_id=? AND decision='REJECT' LIMIT 1",
                (row["exception_id"],),
            ).fetchone()
            if valid_approvals >= row["required_approvals"] and not rejected:
                return row["exception_id"]
        return None

    def _scope_contains_unit(self, scope_id: int, unit: sqlite3.Row) -> bool:
        scope = self.conn.execute("SELECT * FROM authorization_scope_v2 WHERE scope_id=? AND status='ACTIVE'", (scope_id,)).fetchone()
        if scope is None:
            return False
        if scope["scope_type"] == "UNIT":
            return scope["unit_id"] == unit["unit_id"]
        if scope["scope_type"] == "DEPARTMENT":
            return scope["department_id"] == unit["department_id"]
        facility_id = self.conn.execute("SELECT facility_id FROM department WHERE department_id=?", (unit["department_id"],)).fetchone()[0]
        return scope["facility_id"] == facility_id

    def _record(self, request_id: str, at: str, auth_id: str | None,
                break_glass: sqlite3.Row | None, staff: sqlite3.Row | None,
                permission: str, unit: sqlite3.Row | None, candidate_hash: str,
                eligibility: sqlite3.Row | None, evaluation: sqlite3.Row | None,
                result: str, reason_code: str, detail: str,
                safety_policy_id: int | None, policy_version: str,
                exceptions: list[int]) -> dict[str, Any]:
        decision_id = str(uuid.uuid4())
        break_glass_id = break_glass["break_glass_event_id"] if break_glass else None
        self.conn.execute(
            """INSERT INTO clinical_safety_decision_v2
               (safety_decision_id,request_id,decided_at,authorization_decision_id,
                break_glass_event_id,staff_id,permission_code,unit_id,candidate_hash,
                eligibility_snapshot_id,guardrail_evaluation_id,result,reason_code,
                reason_detail,safety_policy_id,safety_policy_version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (decision_id, request_id, at, auth_id, break_glass_id,
             staff["staff_id"] if staff else None, permission,
             unit["unit_id"] if unit else None, candidate_hash,
             eligibility["eligibility_snapshot_id"] if eligibility else None,
             evaluation["guardrail_evaluation_id"] if evaluation else None,
             result, reason_code, detail, safety_policy_id, policy_version),
        )
        for exception_id in exceptions:
            self.conn.execute(
                "INSERT INTO clinical_safety_decision_exception_v2 (safety_decision_id,exception_id) VALUES (?,?)",
                (decision_id, exception_id),
            )
        if break_glass:
            self.conn.execute(
                """INSERT INTO break_glass_use_v2
                   (break_glass_event_id,safety_decision_id,used_at,permission_code,
                    resource_type,resource_code,outcome)
                   VALUES (?,?,?,?,'UNIT',?,?)""",
                (break_glass_id, decision_id, at, permission,
                 unit["unit_code"] if unit else "UNKNOWN", result),
            )
        row = self.conn.execute("SELECT * FROM clinical_safety_decision_v2 WHERE safety_decision_id=?", (decision_id,)).fetchone()
        return self._decision_dict(row)

    def _decision_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        exceptions = [r[0] for r in self.conn.execute(
            "SELECT exception_id FROM clinical_safety_decision_exception_v2 WHERE safety_decision_id=? ORDER BY exception_id",
            (row["safety_decision_id"],),
        )]
        return {
            "safety_decision_id": row["safety_decision_id"],
            "request_id": row["request_id"],
            "result": row["result"],
            "allow": row["result"] == "ALLOW",
            "reason_code": row["reason_code"],
            "authorization_decision_id": row["authorization_decision_id"],
            "break_glass_event_id": row["break_glass_event_id"],
            "eligibility_snapshot_id": row["eligibility_snapshot_id"],
            "guardrail_evaluation_id": row["guardrail_evaluation_id"],
            "exception_ids": exceptions,
            "safety_policy_version": row["safety_policy_version"],
        }
