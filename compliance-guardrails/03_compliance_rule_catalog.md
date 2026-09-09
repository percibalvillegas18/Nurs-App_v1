# Compliance Rule Catalogue (55 rules)

Human-readable grouping of the machine-readable catalogue in `artifacts/compliance_rule_catalog.csv`. Codes follow the spec convention (`LAB-*` / `CBA-*`, plus `HOS-POL-*` for hospital policy). Severities shown are the **defaults**; all are parameterised and editable in `compliance_rule_parameter` and must be confirmed against current law/policy before go-live (see `01` §6).

## A. Working hours (LAB-WH-*)
| Code | Rule | Default | Action |
|---|---|---|---|
| LAB-WH-001 | Max daily hours — **pattern-aware** (Art. 98 8h standard; Art. 100 shift-system 3-week average; do not hard-block 12h nursing) | BLOCK | BLOCK (against the *applicable* pattern) |
| LAB-WH-002 | Max weekly hours — pattern-aware (Art. 98 48h; Art. 100 3-week average) | WARNING | WARN/ESCALATE |
| LAB-WH-003 | Ramadan daily hours (≤ 6 h, applicable workers) | WARNING | AUTO RECALC |
| LAB-WH-004 | Ramadan weekly hours (≤ 36 h) | WARNING | AUTO RECALC |
| LAB-WH-005 | Official-holiday work | WARNING | OT_CALC + APPROVAL |
| LAB-WH-006 | Double / multiple shift same day | BLOCK | BLOCK |

## B. Rest & shift patterns (LAB-RS-*)
| Code | Rule | Default | Action |
|---|---|---|---|
| LAB-RS-001 | Intra-shift rest + daily presence cap (Arts. 101–102; **not** EU 11h between shifts) | BLOCK | BLOCK |
| LAB-RS-002 | Weekly rest (Art. 104 Friday ≥ 24 h) | WARNING | WARN/ESCALATE |
| LAB-RS-003 | Consecutive working days cap | WARNING | WARN |
| LAB-RS-004 | Consecutive-shift detection | WARNING | WARN |

## C. Overtime (LAB-OT-*)
| Code | Rule | Default | Action |
|---|---|---|---|
| LAB-OT-001 | OT eligibility (contracted hours first) | BLOCK | BLOCK |
| LAB-OT-002 | OT approval required | BLOCK | APPROVAL_REQ |
| LAB-OT-003 | OT hour cap (incl. weekly legal max) | WARNING | WARN/ESCALATE |
| LAB-OT-004 | OT rate = hourly wage + 50% basic | ALLOW | CALC |
| LAB-OT-005 | Holiday / emergency OT premium & approval | WARNING | CALC + APPROVAL |
| LAB-OT-006 | OT authorization chain (Dept → Nursing Director) | BLOCK | APPROVAL_REQ |
| LAB-OT-007 | OT payroll interface validation + audit | BLOCK | VALIDATE |

## D. Annual / other leave (LAB-LV-*)
| Code | Rule | Default | Action |
|---|---|---|---|
| LAB-LV-001 | Annual leave balance validation (≥ 21 d) | BLOCK | CHECK_BALANCE |
| LAB-LV-002 | Carry-forward cap / policy | WARNING | WARN/ESCALATE |
| LAB-LV-003 | Leave expiry / use-by alert | WARNING | ALERT |
| LAB-LV-004 | Pro-rata / new-hire entitlement | ALLOW | CALC |
| LAB-LV-005 | Entitlement → 30 d after 5 yrs service | ALLOW | AUTO RECALC |
| LAB-LV-006 | **Approval checks dept staffing coverage** | BLOCK | COVERAGE_CHECK |
| LAB-LV-007 | Maternity / extended leave coordination | WARNING | APPROVAL_REQ |

## E. Contract & employment (LAB-CT-*)
| Code | Rule | Default | Action |
|---|---|---|---|
| LAB-CT-001 | Contract expiry alert | WARNING | ALERT |
| LAB-CT-002 | Probation expiry alert | WARNING | ALERT |
| LAB-CT-003 | Renewal deadline escalation | WARNING | ESCALATE |
| LAB-CT-004 | Job-title vs position mismatch | BLOCK | BLOCK |
| LAB-CT-005 | Contract vs position mismatch | WARNING | WARN |
| LAB-CT-006 | Salary vs grade mismatch | WARNING | WARN |
| LAB-CT-007 | Employment status validation | BLOCK | VALIDATE |
| LAB-CT-008 | Wage-category transfer requires written agreement | BLOCK | BLOCK |
| LAB-CT-009 | Unauthorized transfer / redeployment | BLOCK | BLOCK |
| LAB-CT-010 | Termination workflow approval | WARNING | APPROVAL_REQ |
| LAB-CT-011 | End-of-service calculation HR validation | WARNING | HR_VALIDATE |

## F. CBAHI — license / credential / competency / training
| Code | Rule | Default | Action |
|---|---|---|---|
| CBA-LIC-001 | Professional license validity | BLOCK | BLOCK |
| CBA-LIC-002 | License expiry alert pipeline | WARNING | ALERT |
| CBA-CRED-001 | Credential validity | BLOCK | BLOCK |
| CBA-COMP-001 | Competency validity / expiry | BLOCK | BLOCK |
| CBA-TRAIN-001 | Mandatory training compliance | BLOCK | BLOCK |
| CBA-TRAIN-002 | Patient-identification training | WARNING | CHECK_TRAINING |

## G. CBAHI — staffing, skill mix, safety, quality, documents
| Code | Rule | Default | Action |
|---|---|---|---|
| CBA-STAFF-001 | Minimum staffing (census+acuity+unit type) | BLOCK | BLOCK/ESCALATE |
| CBA-STAFF-002 | Minimum RN:patient ratio | WARNING | ESCALATE |
| CBA-SKILL-001 | Skill-mix compliance (RN/Senior/Charge/specialty) | BLOCK | BLOCK/ESCALATE |
| CBA-SAFE-001 | Unsafe-assignment detection | BLOCK | BLOCK |
| CBA-MED-001 | Medication-safety competency/authorization | BLOCK | VALIDATE |
| CBA-IP-001 | Infection-prevention competency | BLOCK | VALIDATE |
| CBA-EM-001 | Emergency-preparedness training | WARNING | CHECK_TRAINING |
| CBA-INCID-001 | Incident-reporting automated escalation | WARNING | ESCALATE |
| CBA-DOC-001 | Staff-file completeness | BLOCK | VALIDATE |
| CBA-QUAL-001 | Quality-indicator KPI monitoring | ADVISORY | MONITOR |

## H. Hospital policy (HOS-POL-*)
| Code | Rule | Default | Action |
|---|---|---|---|
| HOS-POL-001 | Shift-pattern limits / night frequency / **rest between shifts** (hospital policy — not EU 11h) | WARNING | WARN |
| HOS-POL-002 | Weekend assignment distribution | ADVISORY | INFORM |
| HOS-POL-003 | Rolling overtime exposure cap | WARNING | WARN/ESCALATE |
| HOS-POL-004 | Unit-authorization for assignment | BLOCK | VALIDATE |

> Category totals: **LABOR 35 · CBAHI 16 · HOSPITAL 4**. Each row in `compliance_rule_catalog.csv` carries its `trigger_event`, `module_owner`, `legal_reference` (**article numbers**, not paraphrases), and `exception_allowed` for direct loading into `compliance_rule`.
>
> **LAB-WH-001 is pattern-aware.** A 12-hour ICU/ED shift on a registered Art. 100 shift-system unit is not a Labor Law violation by duration alone. `exception_allowed=True`. Between-shift rest lives on **HOS-POL-001**, not LAB-RS-001. Confirm every `legal_reference` against the current Labor Law text and CBAHI edition before go-live. Sick / Hajj / marriage / bereavement / paternity leave are statutory but **out of this 55-row seed** (see LAB-LV-007 notes).
