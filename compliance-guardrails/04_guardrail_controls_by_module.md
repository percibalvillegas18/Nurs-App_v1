# Guardrail Controls by HNWMS Module

Maps every control domain to the module(s) where the guardrail is enforced, aligned to the existing package (M1–M13). "Engine call" = point of enforcement; engine reads module data and never duplicates it.

## Staff Nurse Master Data (SSOT) — foundation
Serves as the **single source of truth** for: Employee ID, Job Number, Position, Department, Unit, Grade, Nationality, Employment Status, plus references to Professional Registration, License, Credential, and Training/Competency. Every guardrail resolves identity through Staff ID; **no guardrail bypasses the master** (a nurse cannot be scheduled/assigned from a stale or inactive master record).
| Control | Code(s) |
|---|---|
| Employment status / authorization gate | LAB-CT-007, HOS-POL-004 |
| Position/title/salary integrity | LAB-CT-004/005/006 |
| Staff-file completeness | CBA-DOC-001 |

## M1 Workforce Planning — demand input
Provides required staffing & skill-mix baselines consumed by staffing/skill-mix guardrails.
| Control | Code(s) |
|---|---|
| Staffing requirement targets (per unit/shift) | CBA-STAFF-001, CBA-STAFF-002 |
| Skill-mix profile (RN/Senior/Charge/specialty) | CBA-SKILL-001 |

## M3 Credentialing & Onboarding — eligibility source
Owns license/credential/certification data (SCFHS-verified). Engine reads it **before any schedule/deploy/assign**.
| Control | Code(s) |
|---|---|
| License validity & expiry | CBA-LIC-001/002 |
| Credential validity for position/unit | CBA-CRED-001 |
| Medication-safety / infection / emergency competency authorization | CBA-MED-001, CBA-IP-001, CBA-EM-001 |
| Patient-identification training | CBA-TRAIN-002 |

## M4 Nursing Deployment — assignment gate
**Pre-write eligibility** before deploying or reassigning a nurse.
| Control | Code(s) |
|---|---|
| Deployment eligibility (employment+license+credentials+competency+dept) | CBA-LIC-001, CBA-CRED-001, CBA-COMP-001, HOS-POL-004 |
| Unsafe-assignment detection | CBA-SAFE-001 |
| Transfer / redeployment authorization | LAB-CT-009 |
| Skill mix & staffing when re-deploying | CBA-SKILL-001, CBA-STAFF-001 |

## M5 Scheduling & Rostering — the core scheduling guardrail point
**Every candidate shift is evaluated before publish.**
| Control | Code(s) |
|---|---|
| Max daily/weekly & Ramadan hours | LAB-WH-001..004 |
| Rest between shifts / weekly rest / consecutive & double shifts | LAB-RS-001..004, LAB-WH-006 |
| Holiday work → OT | LAB-WH-005 |
| OT exposure | LAB-OT-003 |
| Night-shift frequency / weekend / shift-pattern policy | HOS-POL-001/002/003 |
| License/credential/competency valid for the shift | CBA-LIC/CRED/COMP, CBA-TRAIN-001 |
| Minimum staffing & skill mix for the unit-shift | CBA-STAFF-001/002, CBA-SKILL-001 |

## M6 Attendance & Time Management — OT + hours enforcement
**Punch validation and OT approval are guardrailed; compliant OT only reaches payroll.**
| Control | Code(s) |
|---|---|
| Daily/weekly actual-hour limits & holiday OT | LAB-WH-*, LAB-WH-005 |
| OT eligibility / approval / caps / rate / authorization | LAB-OT-001..006 |
| OT payroll interface + audit | LAB-OT-007 |

## M7 Leave Management — balance AND coverage
**Approval must not create unsafe staffing — balance alone is insufficient.**
| Control | Code(s) |
|---|---|
| Entitlement / balance / accrual / carry-forward / expiry / pro-rata / 5-yr step | LAB-LV-001..005 |
| **Staffing-coverage gate on approval** | LAB-LV-006 |
| Maternity / extended leave coordination | LAB-LV-007 |

## M8 Performance & Competency + M11/LMS — competency/training source
Engine reads competency validity (M8) and training completion (M11/LMS) for assignment gating.
| Control | Code(s) |
|---|---|
| Competency validity/expiry | CBA-COMP-001 |
| Mandatory & patient-safety training | CBA-TRAIN-001/002, CBA-MED-001, CBA-IP-001, CBA-EM-001 |
| Incident → automated escalation | CBA-INCID-001 |

## M9 Analytics & Control Tower — visibility
Consumes compliance results/status for dashboards & KPIs (see `06`). Does not enforce; it reports.
| Control | Code(s) |
|---|---|
| Compliance KPIs, staffing gaps, license/credential/competency expiry | CBA-LIC-002, CBA-QUAL-001, LAB-CT-001/002/003, CBA-STAFF-*, CBA-SKILL-* |

## M10 Contract & Retention — contract guardrails
| Control | Code(s) |
|---|---|
| Expiry / probation / renewal | LAB-CT-001/002/003 |
| Mismatch / status / transfer-agreement guards | LAB-CT-004..009 |

## M12 Separation / Exit — termination & end-of-service guardrails
| Control | Code(s) |
|---|---|
| Termination approval workflow | LAB-CT-010 |
| End-of-service calculation HR validation | LAB-CT-011 |

## Payroll (external) — final validation
| Control | Code(s) |
|---|---|
| Only approved, compliant OT/hours/leave exported | LAB-OT-007, LAB-LV-* |

---

### Engine → module decision summary
| Decision | System behaviour |
|---|---|
| ALLOW | Transaction proceeds |
| INFORM (ADVISORY) | Proceeds; notification only |
| WARN (WARNING) | Proceeds only with approval/escalation (configurable) |
| BLOCK | Transaction prevented; exception path required (see `05`) |
