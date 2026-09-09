"""Shadow-mode RBAC adapter: runs v1 (authoritative) and v2 (shadow) side-by-side.

While in shadow mode, every RBAC evaluation:
  1. Runs the v1 engine (result is authoritative — returned to the caller)
  2. Resolves the v1 subject (persona_code) → v2 account_uuid
  3. Runs the v2 engine (result is logged but never enforced)
  4. Compares the two decisions
  5. Logs any divergence to rbac_shadow_divergence_log

When divergence rate reaches zero over a meaningful sample, the cutover
script (`cutover_v2.py`) can flip to v2-only mode.

Status: Phase 6 integration — shadow mode.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


class ShadowRbacAdapter:
    """Drop-in replacement for RbacEngine that shadows v2 alongside v1."""

    # Import engines lazily to keep the module self-contained
    _RbacEngine = None
    _RbacV2Engine = None

    def __init__(self, conn: sqlite3.Connection, *, shadow_enabled: bool = True):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.shadow_enabled = shadow_enabled

        # Lazy-import the two engines
        if ShadowRbacAdapter._RbacEngine is None:
            from rbac.engine import RbacEngine
            ShadowRbacAdapter._RbacEngine = RbacEngine
        if ShadowRbacAdapter._RbacV2Engine is None:
            from rbac.engine_v2 import RbacV2Engine
            ShadowRbacAdapter._RbacV2Engine = RbacV2Engine

        self.v1 = ShadowRbacAdapter._RbacEngine(conn)
        self.v2 = ShadowRbacAdapter._RbacV2Engine(conn) if shadow_enabled else None

        # Cache the active policy version for v2 calls
        self._policy_version: str | None = None

    @property
    def policy_version(self) -> str | None:
        """Resolve the active v2 policy version (cached per adapter instance)."""
        if self._policy_version is not None:
            return self._policy_version
        row = self.conn.execute(
            "SELECT version_code FROM authorization_policy_v2 WHERE status='ACTIVE' ORDER BY policy_id DESC LIMIT 1"
        ).fetchone()
        self._policy_version = row["version_code"] if row else None
        return self._policy_version

    def evaluate(self, subject: str, permission: str,
                 resource_type: str, resource_code: str) -> dict[str, Any]:
        """Evaluate RBAC — v1 is authoritative, v2 runs in shadow mode.

        Returns the v1 result dict (unchanged API contract).
        """
        # ── v1 (authoritative) ──────────────────────────────────────
        v1_result = self.v1.evaluate(subject, permission, resource_type, resource_code)

        if not self.shadow_enabled or self.v2 is None:
            return v1_result

        # ── v2 (shadow) ─────────────────────────────────────────────
        request_id = f"shadow-{uuid.uuid4()}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        account_uuid = self._resolve_account_uuid(subject)
        policy_version = self.policy_version

        v2_result: dict[str, Any] | None = None
        v2_error: str | None = None

        if account_uuid is None:
            v2_error = f"No v2 account found for persona_code={subject}"
        elif policy_version is None:
            v2_error = "No active v2 policy found"
        else:
            try:
                v2_result = self.v2.evaluate(
                    account_uuid=account_uuid,
                    permission_code=permission.upper().strip(),
                    resource_type=resource_type.upper().strip(),
                    resource_code=resource_code,
                    policy_version=policy_version,
                    request_id=request_id,
                    at=now,
                    context={"shadow_mode": True, "v1_subject": subject},
                )
            except Exception as exc:
                v2_error = f"v2 engine error: {exc}"

        # ── Compare and log divergence ──────────────────────────────
        v1_allow = v1_result.get("allow", False)
        if v2_result is not None:
            v2_decision = v2_result.get("decision", "ERROR")
            v2_allow = v2_result.get("allow", False)
            v2_reason_code = v2_result.get("reason_code", "UNKNOWN")
        elif v2_error:
            v2_decision = "ERROR"
            v2_allow = None
            v2_reason_code = "SHADOW_ERROR"
        else:
            v2_decision = "SKIPPED"
            v2_allow = None
            v2_reason_code = "SHADOW_SKIPPED"

        # A divergence is any case where the outcomes differ,
        # or where v2 couldn't produce a result at all.
        diverged = (v2_allow is None) or (v1_allow != v2_allow)

        if diverged:
            self._log_divergence(
                subject=subject,
                permission=permission,
                resource_type=resource_type,
                resource_code=resource_code,
                v1_allow=v1_allow,
                v1_reason=v1_result.get("reason", ""),
                v2_decision=v2_decision,
                v2_reason_code=v2_reason_code,
                v2_reason_detail=v2_error or (v2_result or {}).get("reason_detail", ""),
                request_id=request_id,
                now=now,
            )

        # Always return the v1 result — v2 is purely observational
        return v1_result

    # ── Delegation: pass-through to v1 for non-evaluate methods ─────

    def _grants(self, subject: str) -> list[dict]:
        """Expose v1 grants for my_rbac()."""
        return self.v1._grants(subject)

    def _held_permissions(self, grants: list[dict]) -> set[str]:
        """Expose v1 held_permissions for my_rbac()."""
        return self.v1._held_permissions(grants)

    # ── Internal helpers ────────────────────────────────────────────

    def _resolve_account_uuid(self, persona_code: str) -> str | None:
        """Map v1 persona_code → v2 account_uuid via the identity bridge.

        Path: persona.persona_code → persona.persona_id
              → staff_member_v2.legacy_persona_id → identity_staff_link_v2.staff_id
              → identity_account_v2.account_uuid
        """
        row = self.conn.execute(
            """SELECT ia.account_uuid
               FROM persona p
               JOIN staff_member_v2 sm ON sm.legacy_persona_id = p.persona_id
               JOIN identity_staff_link_v2 isl ON isl.staff_id = sm.staff_id
               JOIN identity_account_v2 ia ON ia.user_id = isl.user_id
               WHERE p.persona_code = ?
               LIMIT 1""",
            (persona_code,),
        ).fetchone()
        return row["account_uuid"] if row else None

    def _log_divergence(
        self, *, subject: str, permission: str,
        resource_type: str, resource_code: str,
        v1_allow: bool, v1_reason: str,
        v2_decision: str, v2_reason_code: str, v2_reason_detail: str,
        request_id: str, now: str,
    ) -> None:
        """Insert a row into the shadow divergence log."""
        try:
            self.conn.execute(
                """INSERT INTO rbac_shadow_divergence_log
                   (occurred_at, subject, permission, resource_type, resource_code,
                    v1_allow, v1_reason, v2_decision, v2_reason_code,
                    v2_reason_detail, request_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, subject, permission, resource_type, resource_code,
                 1 if v1_allow else 0, v1_reason, v2_decision,
                 v2_reason_code, v2_reason_detail, request_id),
            )
        except Exception:
            # Shadow logging is best-effort — never block the real decision
            pass

    # ── Divergence reporting ────────────────────────────────────────

    @staticmethod
    def divergence_report(conn: sqlite3.Connection, *, limit: int = 100) -> dict[str, Any]:
        """Generate a divergence summary from the shadow log."""
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT COUNT(*) c FROM rbac_shadow_divergence_log").fetchone()["c"]
        by_reason = [
            dict(r) for r in conn.execute(
                """SELECT v2_reason_code, COUNT(*) AS count
                   FROM rbac_shadow_divergence_log
                   GROUP BY v2_reason_code ORDER BY count DESC"""
            )
        ]
        by_subject = [
            dict(r) for r in conn.execute(
                """SELECT subject, COUNT(*) AS count
                   FROM rbac_shadow_divergence_log
                   GROUP BY subject ORDER BY count DESC LIMIT 10"""
            )
        ]
        recent = [
            dict(r) for r in conn.execute(
                """SELECT * FROM rbac_shadow_divergence_log
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            )
        ]

        # Calculate divergence rate (needs total decision count)
        total_decisions = conn.execute(
            "SELECT COUNT(*) c FROM rbac_decision_log"
        ).fetchone()["c"]

        return {
            "total_divergences": total,
            "total_decisions": total_decisions,
            "divergence_rate": round(total / total_decisions, 4) if total_decisions > 0 else 0.0,
            "by_reason_code": by_reason,
            "by_subject": by_subject,
            "recent": recent,
        }
