# Guardrail Severity, Exceptions & Approval Authority

## 1. Severity model (4 levels, not just pass/fail)
| Level | Meaning | System action |
|---|---|---|
| 🟢 **COMPLIANT** (ALLOW) | All controls satisfied | Allow transaction |
| 🔵 **ADVISORY** (INFORM) | No immediate violation | Inform / monitor |
| 🟠 **WARNING** | Risk approaching threshold | Require approval / escalate to route |
| 🔴 **BLOCKED** | Compliance or safety failure | **Prevent** the transaction |

Verdict of an evaluation = the **strictest** applicable rule result (any BLOCK → BLOCK; else any WARN → WARN; else ALLOW/INFORM). Each rule result stores severity, computed vs threshold, and message (`evaluation_rule_result`).

## 2. Compliance status indicators
Per the spec, every employee and every shift carries an automated status:
- **Employee compliance:** Labor Law 🟢 · Contract 🟢 · License 🟢 · Credential 🟢 · Competency 🟠 · Leave 🟢 · Training 🔴 → **OVERALL 🔴 NOT COMPLIANT**. Stored in `employee_compliance_status` (overall_score 0–100).
- **Shift compliance:** Working Hours · Rest · Overtime · License · Competency · Skill Mix · Staffing Level → **SHIFT BLOCKED** if any RED/BLOCK. Stored in `shift_compliance_status`.

## 3. Exception management ("no bypass by clicking override")
A hospital must **not** bypass a guardrail by a single override click. Required path:

```text
Guardrail Violation
   → Exception Request          (mandatory reason)
   → Risk Assessment            (documented risk)
   → Mitigation                 (how risk is reduced)
   → Authorized Approval        (level depends on severity/rule)
   → Time-Limited Exception     (explicit start/end)
   → Audit Trail                (immutable log)
   → Compliance Dashboard       (visibility)
```

**Example:** *"Emergency staffing shortage — ICU night shift"* → an exception record captures: who requested, why, which rule violated, risk level, mitigation, approver, start/end time, actual staffing, and corrective action.

**Design rules:**
- `reason_required`, `risk_assessment`, `mitigation` are mandatory (not optional free text).
- Exceptions are **time-limited** (`start_time`/`end_time`); they do not persist silently.
- Non-time-critical production blocks cannot be overridden by the requesting role (separation of duties).
- Exception is fully audited in `compliance_audit_log` and surfaced on the compliance dashboard.

## 4. Approval authority matrix (approval level per severity)
Approval level is driven by rule `severity_default` + category; escalate up the nursing/HR reporting line (Charge → Unit Manager → Nursing Administration/Deputy DON → DON → Hospital Director; HR for contract/employment).

| Transaction / severity | Approval level | Exception allowed |
|---|---|---|
| ADVISORY | none (inform) | n/a |
| WARNING (schedule/rest/OT exposure) | Unit Manager (+ charge context) | Yes, time-limited |
| WARNING (leave coverage risk) | Unit Manager + Nursing Admin review | Yes, with coverage mitigation |
| WARNING (contract/employment) | HR / Department head | Yes, with legal/HR review |
| BLOCK (working-hours/rest safety) | Nursing Administration / Deputy DON | Yes, exceptional |
| BLOCK (license/credential/competency invalid) | Usually none — resolve the record (M3/M8); override only via DON + HR with documented risk & mitigation | Conditional |
| BLOCK (minimum staffing / skill mix / unsafe assignment) | DON / Hospital Director | Exceptional, must include staffing corrective action |
| BLOCK (unauthorized transfer / wage-category) | HR + legal sign-off | Yes, with written agreement evidence |
| Contract/termination / end-of-service | HR (+ finance) | Standard workflow |

**Rule:** higher severity ⇒ higher & fewer approvers; license/credential/competency blocks are **resolve-first** (fix the underlying record) rather than override-by-default.

## 5. Escalation & SLA
- Auto-escalation up the ladder by step (Charge → Unit Manager → Deputy DON → DON) when an approval exceeds its SLA.
- WARN events not actioned within the configured SLA auto-escalate.
- Every escalation/decision is logged with actor, role, timestamp, decision, and reason.

## 6. Degraded-mode & emergency-override policy (engine / feed unavailability)

**Default = fail-closed.** If the Compliance Engine or its data feeds (Staff Master, M3 license, M8 competency, LMS, EMR census) are unavailable, newly attempted schedule/OT/leave/deployment approvals are **blocked** and flagged — the system never silently allows a non-compliant action. This protects against approving transactions that cannot be checked.

**But fail-closed is not an unbounded block.** In a genuine emergency the hospital must still be able to staff a unit. The escalation path already exists for BLOCKs, and it must extend to *engine-down* states:

1. **Degraded-mode is declared automatically** the moment the engine or a required feed fails health checks, and is **surfaced** on the compliance dashboard + operator alert. Reverts automatically when health is restored.
2. **Action queue:** legitimate approvals attempted during degraded mode are held in a **pending queue** (not dropped), so they can be released for re-evaluation when the engine returns.
3. **Emergency override (time-limited):** if a unit cannot be safely staffed while waiting, the **DON (or designated on-call director)** may issue a **time-limited override** — recorded with reason, affected rule/unit/action, start & end time, and post-event re-evaluation. Override duration is bounded by hospital policy (e.g., a shift or ≤ N hours); it **cannot** exceed the declared window or be issued by the requesting/unit role (separation of duties).
4. **Risk register:** every override is logged to `compliance_audit_log` and appears on the exception register & DON dashboard, feeding the CBAHI workforce-compliance report.
5. **No silent bypass:** overriding is always visible, attributable, and finite — identical to the guardrail-exception controls in §3, just applied to an availability/health failure rather than a rule violation.

> **Policy parameters to set before go-live:** fail-closed default (recommended ON), degraded-mode auto-declaration thresholds, emergency-override max duration, and who may approve an override (recommend DON or on-call director only).
