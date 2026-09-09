# Test & Acceptance Criteria — Compliance Guardrail Layer

Tests each control domain and the engine/exception mechanics. Each row implies: rule configured in `compliance_rule` (with parameter thresholds), invoked at its evaluation point, result audited.

## A. Rules-engine mechanics
| ID | Scenario | Expected |
|---|---|---|
| RG-01 | Configure a new rule + parameters, set effective window | Rule active at evaluation; effective-dated; change audited. |
| RG-02 | Evaluate a transaction against a rule with computed < warn_value | PASS/COMPLIANT (ALLOW). |
| RG-03 | computed between warn and block threshold | WARNING + routing to approval/escalation. |
| RG-04 | computed exceeds block threshold | BLOCK; transaction prevented; reason stored. |
| RG-05 | Multiple rules run on one candidate | Verdict = strictest (any BLOCK → BLOCK; else WARN; else ALLOW). |
| RG-06 | Rule expiry passes / toggle inactive | Rule no longer evaluated; log records the change. |
| RG-07 | Ramadan calendar window active | Hour limits auto-recalculated (6/36 h) for applicable scope. |

## B. Working hours / rest
| ID | Scenario | Expected |
|---|---|---|
| WH-01 | 12 h shift on a **registered Art. 100 shift-system** unit (e.g. ICU-MAIN 19:00–07:00) | **ALLOW** on LAB-WH-001 (duration alone is not a violation). Evaluate 3-week average. |
| WH-01a | 10 h shift on a **standard day-pattern** (Art. 98) employee | BLOCK or route to OT (LAB-WH-001 / LAB-OT-*) — 8h wall applies. |
| WH-02 | Weekly total approaches the **applicable** cap (48 h standard or Art. 100 average) | WARNING/escalation (LAB-WH-002). |
| WH-03 | Six consecutive hours with no ≥30 min rest/prayer/meal break | BLOCK (LAB-RS-001, Art. 101). Rest-between-shifts is HOS-POL-001, not LAB-RS-001. |
| WH-04 | Same-day double shift | BLOCK/approval-required (LAB-WH-006). |
| WH-05 | Consecutive-shift cap reached | WARNING (LAB-RS-003/004). |
| WH-06 | Official-holiday shift assigned | Routes to OT calculation + approval (LAB-WH-005). |

## C. Overtime
| ID | Scenario | Expected |
|---|---|---|
| OT-01 | Actual > contracted/scheduled hours | OT detected (LAB-OT-001). |
| OT-02 | OT submitted without supervisor approval | BLOCK (LAB-OT-002) — not passed to payroll. |
| OT-03 | OT rate computed | hourly + 50% base (LAB-OT-004) — confirm against policy. |
| OT-04 | OT cap exceeded (rolling / weekly incl legal max) | WARNING/escalation (LAB-OT-003). |
| OT-05 | Emergency/holiday OT | Higher approval chain + premium (LAB-OT-005). |
| OT-06 | Payroll export | Only approved, compliant OT exported; audit intact (LAB-OT-007). |

## D. Leave
| ID | Scenario | Expected |
|---|---|---|
| LV-01 | Request exceeds available annual balance | BLOCK (LAB-LV-001). |
| LV-02 | Balance present BUT approval would breach staffing coverage | BLOCK/coverage-review — balance alone insufficient (LAB-LV-006). |
| LV-03 | New hire entitlement | Pro-rata computed (LAB-LV-004). |
| LV-04 | Service passes 5 years | Entitlement recalcs to 30 d (LAB-LV-005). |
| LV-05 | Carry-forward cap / expiry | Warn + use-by alert (LAB-LV-002/003). |

## E. Contract & employment
| ID | Scenario | Expected |
|---|---|---|
| CT-01 | Contract/probation expiring | Alert pipeline + renewal escalation (LAB-CT-001/002/003). |
| CT-02 | Job title vs approved position mismatch | BLOCK (LAB-CT-004). |
| CT-03 | Wage-category transfer without written agreement | BLOCK (LAB-CT-008). |
| CT-04 | Unauthorized transfer/redeployment | BLOCK (LAB-CT-009). |
| CT-05 | Salary vs grade mismatch | WARNING (LAB-CT-006). |
| CT-06 | Termination without workflow / end-of-service | Approval + HR validation (LAB-CT-010/011). |

## F. License / credential / competency / training (CBAHI)
| ID | Scenario | Expected |
|---|---|---|
| LC-01 | License expired/invalid nurse scheduled | BLOCK — cannot be scheduled/deployed (CBA-LIC-001). |
| LC-02 | License expiry approaching | Alert pipeline triggers (CBA-LIC-002). |
| LC-03 | Credential invalid for target unit/role | BLOCK (CBA-CRED-001). |
| LC-04 | Competency expired for assignment skill | BLOCK (CBA-COMP-001). |
| LC-05 | Mandatory training outstanding | BLOCK schedule (CBA-TRAIN-001); escalation. |
| LC-06 | Medication/IP/emergency competency missing | BLOCK / validate per rule (CBA-MED-001, CBA-IP-001, CBA-EM-001). |

## G. Minimum staffing / skill mix / safety

> **Scenario note:** The unit labels in G (ICU, Medical Ward, ED, NICU) are **illustrative by unit-type**. Bind each scenario to a real registry code (ICU Main = `ICU-MAIN`, Medical Ward = `W3A`, ED = `ED-RESUS`). `NICU` does not exist — use `ICU-MAIN` or `PEDS`.
| ID | Scenario | Expected |
|---|---|---|
| ST-01 | ICU required 12 / scheduled 12 | 🟢 COMPLIANT (CBA-STAFF-001). |
| ST-02 | Medical ward required 10 / scheduled 9 | 🟠 AMBER staffing-risk (CBA-STAFF-001/002). |
| ST-03 | ED required 15 / scheduled 11 | 🔴 CRITICAL → BLOCK/escalate (CBA-STAFF-001). |
| ST-04 | NICU required 8 / scheduled 7 | 🔴 CRITICAL → BLOCK/escalate. |
| ST-05 | Required Charge Nurse missing from roster | BLOCK/ESCALATE, not just "10 scheduled" (CBA-SKILL-001). |
| ST-06 | All staff individually eligible but staffing below min | Schedule NOT auto-approved — patient-safety gate (CBA-SAFE-001). |

## H. Exceptions & audit
| ID | Scenario | Expected |
|---|---|---|
| EX-01 | Attempt to override a BLOCK with no reason | Rejected — mandatory reason/risk/mitigation. |
| EX-02 | Exception requested + approved | Time-limited window enforced; approver+decision logged; expires automatically. |
| EX-03 | Requesting role also approves own override | Prevented (separation of duties). |
| EX-04 | Any eval/override/parameter change | Immutable `compliance_audit_log` entry (who/what/when/before/after/source). |
| EX-05 | Non-time-critical production block overridden | Not allowed by requesting role; only authorized higher level with risk & corrective action. |

## I. Dashboards / status
| ID | Scenario | Expected |
|---|---|---|
| DS-01 | Employee compliance status aggregates | Correct per-domain + overall status & score (spec §11). |
| DS-02 | Shift compliance status aggregates | Correct per-domain + SHIFT BLOCKED when any RED. |
| DS-03 | Nursing Director KPIs | Values computed per `06`; targets displayed. |
| DS-04 | Exception register & blocked log | Complete, filterable by rule/unit/date. |

## J. Security & compliance of the layer
- [ ] Rule parameters restricted to authorized compliance/HR roles; every change audited.
- [ ] Exception/approval data viewable only by authorized approvers & auditors (RBAC scoping).
- [ ] No patient-identifiable data on workforce/compliance screens beyond aggregates.
- [ ] Regulatory mapping (Saudi Labor Law articles + CBAHI edition) documented and evidenced for each rule's `legal_reference`.

## K. Go-live acceptance gate
- [ ] All RG-*, WH-*, OT-*, LV-*, CT-*, LC-*, ST-*, EX-*, DS-* cases pass.
- [ ] Default rule parameters reviewed & signed by HR/Legal and Nursing Director against current law & CBAHI.
- [ ] Exceptions logged >0 cases demonstrate a real, time-limited, multi-approval path end-to-end.
- [ ] UAT by super-users (schedulers, charge/managers, DON, HR, payroll) with zero open critical/high defects.
- [ ] Rollback / rule-disable rehearsal successful; audit intact.
