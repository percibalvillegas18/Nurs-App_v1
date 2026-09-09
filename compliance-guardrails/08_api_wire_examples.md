# Compliance Guardrail Layer — API & FHIR/HL7 Wire Examples

**Version:** 1.0 · **Date:** 2026-09-09
**Purpose:** Concrete request/response contracts ("wire format") for the **Compliance Rules Engine** and its integration with Scheduling/Attendance/Leave/Deployment and with the HIS/EMR (via the bed/org location registry and census). These make the architecture in `01_architecture_integration.md` directly implementable and give vendors/build teams exact field names, payloads, and outcomes.

> **Vendor-facing:** A one-page distilled version for hand-off to an HIS/EMR/Payroll/Scheduling vendor is in **`09_vendor_contract_sheet.md`** (source of truth remains this document).

Companions: `01_architecture_integration.md` (architecture/evaluation points), `04_guardrail_controls_by_module.md` (which rule fires where), `05_severity_exceptions_approvals.md` (severity/exceptions). REST uses a consistent `ComplianceEvaluation` envelope; clinical interchange uses **FHIR R4** (`Task`, `OperationOutcome`) and **HL7 v2** (`ADT A01/A02/A03`) so the layer interoperates with standard HIS/EMR/Payroll rather than a private format.

---

## 1. Conventions

- **Base URL:** `/api/hnwms/compliance`
- **AuthN/AuthZ:** OAuth2 / bearer with role+scope; a caller may evaluate only within its facility/department/unit scope (§ RBAC). Engine never returns patient-identifiable data.
- **Consistent envelope fields:** `evaluation_id`, `target`, `verdict` (`ALLOW`/`INFORM`/`WARN`/`BLOCK`), `overall_status`, `rule_results[]`, `effective_exceptions[]`.
- **Verdict = strictest applicable rule.** Any BLOCK → `BLOCK`; else any WARN → `WARN`; else `ALLOW`/`INFORM`.
- Endpoint `POST /compliance/evaluate` is **synchronous and non-mutating** (pure evaluation). Publishing/approving is a separate action the calling module performs only after a non-blocking verdict (or an approved exception).

### Shared domain codes (drawn from the Org/Location registry + HNWMS)
| Code | Meaning |
|---|---|
| `staff_id` | HNWMS Staff Nurse Master id (e.g. `NUR-000125`) |
| `unit_code` | **Location-registry** unit code (single source of truth — see note below) |
| `shift_type` | `MORNING` / `EVENING` / `NIGHT` / `EXTENDED` / `ONCALL` |
| `shift_date`, `start`/`end` | ISO-8601 date / `HH:MM` (local facility timezone) |
| `leave_type` | `ANNUAL` / `SICK` / `MATERNITY` / `EMERGENCY` / `UNPAID` / … |
| `eval_target_type` | `SHIFT` / `ROSTER` / `OT` / `LEAVE` / `DEPLOYMENT` / `ASSIGNMENT` / `PUNCH` |

> **Canonical unit identity.** Every `unit_code` in a payload MUST be a code from the **location registry** (`implementation-plan/artifacts/normalized_department_unit.csv`). That registry is the single source of truth for unit codes — HNWMS does not invent or accept ad-hoc unit identifiers. The examples in this document map to real registry rows as follows:
>
> | Scenario in this doc | Registry `unit_code` | Registry `unit_name` |
> |---|---|---|
> | ICU Main | `ICU-MAIN` | Intensive Care Unit (ICU) Main |
> | Ward 3A - General Acute | `W3A` | Ward 3A - General Acute |
> | ED Resuscitation Area | `ED-RESUS` | ED Resuscitation Area |
>
> **Two honest caveats:**
> 1. `NICU`, `WARD3A`, `ICU-MAIN`, and bare `ICU` are **not** registry codes. The ICU scenario uses `ICU-MAIN`; there is **no NICU** in the current registry (nearest pediatric row is `PEDS`).
> 2. The registry's `unit_code` values are **placeholders to be finalized in Wave P0** (`implementation-plan/06`). Payloads must always carry a registry-issued code — never a display alias — but the authoritative code set is confirmed during that sign-off.

---

## 2. REST endpoints (summary)

| Method/Path | Purpose | Invoked by |
|---|---|---|
| `POST /compliance/evaluate` | Evaluate one candidate transaction (shift/roster/OT/leave/deployment) | M5, M6, M7, M4 |
| `POST /compliance/evaluate/batch` | Evaluate a monthly roster (returns per-row + aggregate) | M5 roster publish |
| `POST /compliance/exceptions` | Submit a guardrail exception request | Any blocked requester |
| `POST /compliance/exceptions/{id}/approve` | Approve/reject an exception (multi-level) | Approver role |
| `GET /compliance/status/{staff_id}` | Employee compliance status | M9 / self-view |
| `GET /compliance/status/shift/{shift_ref}` | Shift compliance status | M9 |
| `GET /compliance/evaluations?unit=&from=&to=` | Evaluation history | M9 / audit |
| `GET /compliance/audit` | Immutable audit log (role-scoped) | Compliance/audit |

Full wire bodies for the key ones follow.

---

## 3. REST — evaluate a single shift

### Request
```http
POST /api/hnwms/compliance/evaluate
Authorization: Bearer <token>
Content-Type: application/json

{
  "target": {
    "type": "SHIFT",
    "staff_id": "NUR-000125",
    "unit_code": "ICU-MAIN",          // location-registry code = Intensive Care Unit (ICU) Main
    "unit_name": "Intensive Care Unit (ICU) Main",
    "shift_type": "NIGHT",
    "shift_date": "2026-09-10",
    "start": "23:00",
    "end": "07:00",
    "is_overtime": false
  },
  "include_rule_results": true
}
```

### Case A — COMPLIANT → `ALLOW`
```json
{
  "evaluation_id": "EV-88100",
  "verdict": "ALLOW",
  "overall_status": "COMPLIANT",
  "target": { "type": "SHIFT", "staff_id": "NUR-000125", "shift_date": "2026-09-10" },
  "rule_results": [
    { "rule_code": "CBA-LIC-001", "severity": "ALLOW", "result": "PASS", "message": "License valid to 2027-01-15" },
    { "rule_code": "LAB-WH-001", "severity": "ALLOW", "result": "PASS", "message": "Daily hours within limit" },
    { "rule_code": "CBA-STAFF-001", "severity": "ALLOW", "result": "PASS", "message": "ICU Main night staffing met after assignment" }
  ]
}
```

### Case B — staffing risk → `WARN`
```json
{
  "evaluation_id": "EV-88101",
  "verdict": "WARN",
  "overall_status": "STAFFING_RISK",
  "target": { "type": "SHIFT", "staff_id": "NUR-000125", "unit_code": "W3A", "unit_name": "Ward 3A - General Acute", "shift_date": "2026-09-10" },
  "rule_results": [
    { "rule_code": "CBA-STAFF-001", "severity": "WARNING", "result": "WARN",
      "message": "Ward 3A - General Acute morning requires 10 RN; scheduled 9", "computed": 9, "threshold": 10 },
    { "rule_code": "CBA-SKILL-001", "severity": "ALLOW", "result": "PASS", "message": "Skill mix present" }
  ],
  "required_action": "APPROVAL_OR_REMEDIATION"
}
```

### Case C — blocked → `BLOCK`
```json
{
  "evaluation_id": "EV-88213",
  "verdict": "BLOCK",
  "overall_status": "BLOCKED",
  "target": { "type": "SHIFT", "staff_id": "NUR-000125", "unit_code": "ICU-MAIN", "unit_name": "Intensive Care Unit (ICU) Main", "shift_date": "2026-09-10" },
  "rule_results": [
    { "rule_code": "LAB-RS-001", "severity": "BLOCK", "result": "FAIL",
      "message": "Six consecutive hours without a rest break; Art. 101 requires a break after 5h" },
    { "rule_code": "CBA-LIC-001", "severity": "ALLOW", "result": "PASS", "message": "License valid" }
  ],
  "exception_required": true,
  "exception_policy": { "exception_allowed": true, "approval_level": "NURSING_ADMINISTRATION", "time_limited": true }
}
```

---

## 4. REST — batch roster evaluation

```http
POST /api/hnwms/compliance/evaluate/batch
```
```json
{
  "target": { "type": "ROSTER", "unit_code": "ICU-MAIN", "unit_name": "Intensive Care Unit (ICU) Main", "month": "2026-09" },
  "rows": [
    { "row_ref": "ICU-MAIN-20260910-M-01", "staff_id": "NUR-000125", "shift_type": "MORNING", "shift_date": "2026-09-10", "start": "07:00", "end": "15:00" },
    { "row_ref": "ICU-MAIN-20260910-N-04", "staff_id": "NUR-000210", "shift_type": "NIGHT",  "shift_date": "2026-09-10", "start": "23:00", "end": "07:00" }
  ]
}
```
```json
{
  "roster_verdict": "BLOCK",               // strictest across rows
  "evaluations": [
    { "row_ref": "ICU-MAIN-20260910-M-01", "evaluation_id": "EV-88110", "verdict": "ALLOW" },
    { "row_ref": "ICU-MAIN-20260910-N-04", "evaluation_id": "EV-88111", "verdict": "WARN",
      "rule_results": [{ "rule_code": "CBA-SKILL-001", "severity": "WARNING", "message": "Charge nurse required on ICU Main night shift" }] }
  ],
  "blocked_count": 0,
  "warn_count": 1,
  "summary": "1 warning; correct or approve before publish"
}
```

---

## 5. REST — OT approval and leave approval hooks

### OT eligibility/approval (guarded in M6)
```http
POST /api/hnwms/compliance/evaluate
```
```json
{
  "target": { "type": "OT", "staff_id": "NUR-000125", "ot_date": "2026-09-11",
    "actual_hours": 11.5, "scheduled_hours": 8.0, "reason": "ICU staff shortage" }
}
```
```json
{
  "evaluation_id": "EV-88300", "verdict": "WARN", "overall_status": "OT_APPROVAL_REQUIRED",
  "rule_results": [
    { "rule_code": "LAB-OT-001", "severity": "ALLOW", "result": "PASS", "message": "Contracted hours met; OT eligible" },
    { "rule_code": "LAB-OT-003", "severity": "WARNING", "result": "WARN", "message": "Weekly incl. OT = 50h > 48h cap", "computed": 50, "threshold": 48 },
    { "rule_code": "LAB-OT-006", "severity": "BLOCK", "result": "PENDING", "message": "Requires Department then Nursing Director approval" }
  ],
  "required_action": "APPROVAL_CHAIN"
}
```

### Leave approval — balance is NOT the only gate (M7)
```http
POST /api/hnwms/compliance/evaluate
```
```json
{
  "target": { "type": "LEAVE", "staff_id": "NUR-000210", "unit_code": "ICU-MAIN", "unit_name": "Intensive Care Unit (ICU) Main",
    "leave_type": "ANNUAL", "start_date": "2026-09-20", "end_date": "2026-10-05" }
}
```
```json
{
  "evaluation_id": "EV-88400", "verdict": "BLOCK", "overall_status": "BLOCKED",
  "rule_results": [
    { "rule_code": "LAB-LV-001", "severity": "ALLOW", "result": "PASS", "message": "Balance sufficient (12 days)" },
    { "rule_code": "LAB-LV-006", "severity": "BLOCK", "result": "FAIL",
      "message": "Approving leave drops ICU Main night shift to 5 RN vs required 8 RN for 3 nights",
      "computed": 5, "threshold": 8 }
  ],
  "exception_required": true,
  "exception_policy": { "approval_level": "NURSING_ADMINISTRATION", "requires_replacement": true }
}
```

---

## 6. FHIR R4 — standards-based interchange

FHIR is used at the HIS/EMR and external-vendor boundary. The compliance engine exposes evaluation/exception actions as **FHIR `Task`** resources and returns reasons as **FHIR `OperationOutcome`**.

### 6.1 Exception request as a FHIR `Task`
A blocked scheduling decision creates a `Task` (status `requested`) routed to the required approver:
```json
{
  "resourceType": "Task",
  "id": "task-exc-88213",
  "status": "requested",
  "intent": "proposal",
  "priority": "urgent",
  "code": { "coding": [{ "system": "http://hnwms.local/codes", "code": "GUARDRAIL_EXCEPTION", "display": "Guardrail exception request" }] },
  "focus": {
    "identifier": { "system": "http://hnwms.local/evaluation", "value": "EV-88213" },
    "reference": "Task/ev-88213"
  },
  "for": { "identifier": { "system": "http://hnwms.local/staff", "value": "NUR-000125" } },
  "authoredOn": "2026-09-09T09:12:00+03:00",
  "requester": { "identifier": { "system": "http://hnwms.local/user", "value": "u-charge-04" } },
  "owner": { "identifier": { "system": "http://hnwms.local/role", "value": "NURSING_ADMINISTRATION" } },
  "restriction": { "period": { "start": "2026-09-09T21:00:00+03:00", "end": "2026-09-11T21:00:00+03:00" } },
  "input": [
    { "type": { "text": "rule_code" }, "valueCode": "LAB-RS-001" },
    { "type": { "text": "reason" }, "valueString": "Emergency staffing shortage - ICU night shift" },
    { "type": { "text": "risk_assessment" }, "valueString": "Moderate fatigue risk; mitigated by charge oversight" },
    { "type": { "text": "mitigation" }, "valueString": "Charge nurse + reduced assignment load" }
  ]
}
```
The `restriction.period` encodes the **time-limited** exception window; `input` carries the mandatory reason/risk/mitigation.

### 6.2 Decision / reason as FHIR `OperationOutcome`
```json
{
  "resourceType": "OperationOutcome",
  "id": "oo-eval-88213",
  "issue": [
    {
      "severity": "error",
      "code": "business-rule",
      "details": { "coding": [{ "system": "http://hnwms.local/rules", "code": "LAB-RS-001", "display": "Intra-shift rest and daily presence cap" }] },
      "diagnostics": "Six consecutive hours without a rest break; Art. 101 requires a break after 5h",
      "expression": ["Shift.end_time", "Shift.start_time"]
    },
    {
      "severity": "warning",
      "code": "business-rule",
      "details": { "coding": [{ "system": "http://hnwms.local/rules", "code": "LAB-OT-003", "display": "Overtime hour cap" }] },
      "diagnostics": "Weekly total 50h approaching cap"
    }
  ]
}
```

---

## 7. HL7 v2 — ADT → census → staffing → BLOCK (end-to-end)

This is the bridge to the **bed/org implementation plan** (`implementation-plan/`): EMR `ADT` events drive census, census drives the minimum-staffing `staffing_requirement`, and the engine evaluates rostering against it. Unit/location codes come from the Org Directory location registry.

### 7.1 ADT A01 (Admit) — an inpatient occupancy event
```hl7
MSH|^~\&|EMR|AIGH|HNWMS|AIGH|20260909100100||ADT^A01|MSGCENS0001|P|2.5
EVN|A01|20260909100100
PID|1||MRN-0099331^^^AIGH^MR||Patient^Sample||19850412|M
PV1|1|I|ICU-MAIN^Intensive Care Unit (ICU) Main^AIGH-ICU-MAIN^^B||||1234^Attending^Physician||||||||||||||||||||ICU-MAIN|||ADM
```
The engine/HNWMS consumes the `PV1.3` patient location (unit `ICU-MAIN` = ICU Main) to **increment census** for ICU Main. This feeds `staffing_requirement` (required RN for the ICU Main census/acuity).

### 7.2 Census → staffing requirement → engine check
After A01, the derived staffing requirement for the ICU Main night shift is evaluated before a roster can be published:
```json
// GET /api/hnwms/compliance/staffing-requirement?unit=ICU-MAIN&shift=NIGHT&date=2026-09-10
{
  "unit_code": "ICU-MAIN", "unit_name": "Intensive Care Unit (ICU) Main", "shift": "NIGHT", "date": "2026-09-10",
  "census": 12, "acuity": 3.5,
  "required": { "rn": 6, "senior_rn": 2, "charge": 1, "specialty": 1, "total": 10 },
  "scheduled": { "rn": 5, "senior_rn": 2, "charge": 1, "specialty": 1, "total": 9 },
  "verdict": "BLOCK", "rule": "CBA-STAFF-001",
  "message": "ICU Main night requires 10 total / 6 RN; scheduled 9 / 5 RN"
}
```

### 7.3 ADT A03 (Discharge) — decrement census
```hl7
MSH|^~\&|EMR|AIGH|HNWMS|AIGH|20260910203000||ADT^A03|MSGCENS0002|P|2.5
EVN|A03|20260910203000
PID|1||MRN-0099331^^^AIGH^MR||Patient^Sample||19850412|M
PV1|1|I|W3A^Ward 3A - General Acute^AIGH-W3A^^B||||||||||||||||||||||W3A|||DIS
```
Census for `W3A` (Ward 3A - General Acute) decrements; occupancy and staffing-requirement recompute. If a discharge reduces the required RN count enough to close a staffing gap, previously BLOCKed shifts may re-evaluate to ALLOW (the engine re-runs on occupancy/roster change).

### 7.4 Transfer A02 (bed/unit change)
```hl7
MSH|^~\&|EMR|AIGH|HNWMS|AIGH|20260910141500||ADT^A02|MSGCENS0003|P|2.5
EVN|A02|20260910141500
PID|1||MRN-0099311^^^AIGH^MR||Patient^Transfer||19770301|F
PV1|1|I|ICU-MAIN^Intensive Care Unit (ICU) Main^AIGH-ICU-MAIN^^B|W3A^Ward 3A - General Acute^AIGH-W3A^^B
```
Source unit census decrements, target unit census increments — matching the ADT/bed workflow in `implementation-plan/`.

> **HL7 note:** segment identifiers (`PID`, `PV1`) are illustrative of standard v2.3–2.5 structure. Exact field use depends on the EMR's v2 profile / Z-segments; the integration contract should confirm the admitted set of trigger events (`A01/A02/A03`) and any local acuity segments the hospital uses to derive `staffing_requirement`.

---

## 8. Error handling & status codes

| HTTP | Meaning | Engine-level |
|---|---|---|
| `200` | Evaluation completed (verdict in body — even when BLOCK) | `verdict` decides outcome; publishing module enforces it |
| `200` with `verdict=BLOCK` | Transaction must not proceed without exception | `exception_required`, `exception_policy` |
| `400` | Malformed payload / unknown staff or unit code | validation message |
| `401` / `403` | Unauthenticated / out-of-scope caller | RBAC scope denied |
| `409` | Idempotency conflict (duplicate evaluation) | reuse existing `evaluation_id` |
| `503` | Engine/feeds temporarily unavailable | **fail-closed** (degraded mode declared; default BLOCK) — see below and `05` §6 |

**Fail-safe (degraded mode):** if the engine or a required data feed is unavailable, the system **declares degraded mode, blocks newly attempted schedule/OT/leave/deployment approvals, and alerts operators** — it never silently allows a non-compliant action. Actions are held in a **pending queue** for re-evaluation on recovery. If a unit cannot be safely staffed while waiting, a **time-limited DON (or on-call director) emergency override** may be issued — bounded, attributable, fully audited, and surfaced on the exception register (full policy in `05` §6). Fail-closed default is configurable but **ON by default**.

---

## 9. Contract ↔ module traceability
| Endpoint / message | Enforces | Documented in |
|---|---|---|
| `evaluate` SHIFT/ROSTER | LAB-WH/RS/OT, CBA-LIC/CRED/COMP/TRAIN/STAFF/SKILL, HOS-POL | `04` M5 |
| `evaluate` OT | LAB-OT-* | `04` M6 |
| `evaluate` LEAVE | LAB-LV-* (incl. coverage) | `04` M7 |
| `evaluate` DEPLOYMENT/ASSIGNMENT | CBA-LIC/CRED/COMP, HOS-POL-004, LAB-CT-009 | `04` M4 |
| FHIR `Task` + `OperationOutcome` | exception mgmt, decisions | `05` |
| HL7 `ADT A01/A02/A03` | census → staffing demand → CBA-STAFF-* | `implementation-plan/` |

Test cases in `07_test_acceptance_criteria.md` apply to these contracts (e.g., every guardrail domain returns a deterministic verdict and audits the evaluation).
