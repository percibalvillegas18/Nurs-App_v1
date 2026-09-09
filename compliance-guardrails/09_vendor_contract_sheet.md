# HNWMS Compliance Engine — Vendor Integration Contract Sheet

**Purpose:** One-page summary of what a HIS/EMR/Payroll or Scheduling vendor must integrate to interoperate with the HNWMS Compliance Guardrail Layer. Full detail & full payloads: `08_api_wire_examples.md`. Generic/standalone from any single EMR; tailor specific v2 profiles/Z-segments once a platform is selected.

---

## 1. Contact & system identity
- **System:** HNWMS Compliance Guardrail Layer (hospital nursing workforce mgmt)
- **API base URL:** `/api/hnwms/compliance` (HTTPS only)
- **Auth:** OAuth2 bearer; caller scoped to facility/department/unit (RBAC)
- **Time:** ISO-8601 local facility timezone; send +offset

## 2. What the engine does
Automated **ALLOW / INFORM / WARN / BLOCK** of workforce actions (schedule, overtime, leave, deployment) against Saudi Labor Law (HRSD) + CBAHI + Hospital Policy. Verdict = **strictest** applicable rule. **Fail-closed default:** if the engine/feeds are unavailable, the system declares **degraded mode**, blocks newly attempted approvals, holds them in a pending queue, and alerts operators — never silently allows a non-compliant action. Time-limited **DON emergency override** available where a unit cannot be safely staffed (bounded, audited; policy in `05` §6).

## 3. REST contract (key endpoints)
| Method/Path | Payload/notes |
|---|---|
| `POST /compliance/evaluate` | One candidate: `SHIFT`/`OT`/`LEAVE`/`DEPLOYMENT`. Returns `verdict` + `rule_results[]` + `evaluation_id`. |
| `POST /compliance/evaluate/batch` | Monthly roster → per-row + aggregate verdict. |
| `POST /compliance/exceptions` | Submit time-limited exception (reason/risk/mitigation required). |
| `POST /compliance/exceptions/{id}/approve` | Multi-level approval/reject. |
| `GET /compliance/status/{staff_id}` | Employee compliance status. |
| `GET /compliance/status/shift/{shift_ref}` | Shift compliance status. |
| `GET /compliance/evaluations` · `GET /compliance/audit` | History + immutable audit (role-scoped). |

### Minimal evaluate body (SHIFT)
```json
{ "target": { "type": "SHIFT", "staff_id": "NUR-000125", "unit_code": "ICU-MAIN",
    "unit_name": "Intensive Care Unit (ICU) Main",
    "shift_type": "NIGHT", "shift_date": "2026-09-10", "start": "23:00", "end": "07:00" } }
```
### Response shape (verdict)
```json
{ "evaluation_id": "EV-88213", "verdict": "ALLOW|INFORM|WARN|BLOCK",
  "overall_status": "COMPLIANT|STAFFING_RISK|BLOCKED",
  "rule_results": [ { "rule_code": "LAB-RS-001", "severity": "…",
      "message": "…", "computed": 6, "threshold": 5 } ],
  "exception_required": true|false }
```

## 4. FHIR R4 (external/clinical boundary)
- **`Task`** = a guardrail exception/approval action. `status=requested`, `intent=proposal`; **time-limited** via `restriction.period`; reason/risk/mitigation carried as `input`.
- **`OperationOutcome`** = machine-readable decision reason: `issue[].details.coding` = rule code (`http://hnwms.local/rules`), `diagnostics` = human message.

## 5. HL7 v2 ADT (census → staffing demand)
| Trigger | Effect the engine consumes |
|---|---|
| `ADT A01` (Admit) | Increment unit census → derives `staffing_requirement` (RN/Senior/Charge/specialty by census+acuity+unit type) → used to gate rostering |
| `ADT A02` (Transfer) | Decrement source / increment target unit census |
| `ADT A03` (Discharge) | Decrement unit census; recompute occupancy & requirement |

**Standards note (vendor-specific):** segments above are standard v2.3–2.5 shape. Actual v2 profile & Z-segments (e.g., acuity, bed/room, service) are confirmed with the chosen EMR — this sheet is the generic baseline.

## 6. Domain codes (shared vocabulary — from the Org/Location registry)
| Code | Meaning | Example |
|---|---|---|
| `staff_id` | Staff Nurse Master id | `NUR-000125` |
| `unit_code` | **Location-registry** unit code (single source of truth) | `ICU-MAIN`, `W3A`, `ED-RESUS` |
| `shift_type` | `MORNING/EVENING/NIGHT/EXTENDED/ONCALL` | |
| `leave_type` | `ANNUAL/SICK/MATERNITY/EMERGENCY/UNPAID/…` | |
| `eval_target_type` | `SHIFT/ROSTER/OT/LEAVE/DEPLOYMENT/ASSIGNMENT/PUNCH` | |

> **Unit codes are NOT invented here.** `unit_code` must be a code from the **location registry** (`implementation-plan/artifacts/normalized_department_unit.csv`), which is the single source of truth. Example mappings: `ICU-MAIN` = Intensive Care Unit (ICU) Main, `W3A` = Ward 3A - General Acute, `ED-RESUS` = ED Resuscitation Area. Payloads always carry a registry-issued code, never a display alias.

## 7. Behavioural requirements
- **Do not mutate on evaluate** — `evaluate` is read-only; publish/approve only after ALLOW (or approved exception).
- **Honor BLOCK/WARN** — never write a schedule/OT/leave/deployment the engine returns non-compliant.
- **Audit** — log every evaluation/exception to `compliance_audit_log`.
- **No PII across boundary** — workforce screens carry census/occupancy aggregates only.

## 8. Acceptance (vendor proves)
- ALLOW / WARN / BLOCK each return a deterministic verdict for a known case (see `07_test_acceptance_criteria.md`).
- ADT A01/A02/A03 correctly shift unit census and trigger staffing-requirement re-evaluation.
- A BLOCK cannot be bypassed by a single override; exceptions are time-limited and audited.

---
**Source of truth:** `compliance-guardrails/08_api_wire_examples.md`. Tailor to EMR-specific v2 profile after platform selection.
