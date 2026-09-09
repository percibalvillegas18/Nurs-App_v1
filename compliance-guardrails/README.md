# HNWMS Compliance Guardrail Layer — Saudi Labor Law & CBAHI

Implementation-ready design for an **automated compliance/guardrail layer** inside the Hospital Nursing Workforce Management System (HNWMS) — turning Saudi Labor Law (HRSD/MOL), CBAHI, and Hospital Policy requirements into real-time **ALLOW / INFORM / WARN / BLOCK** controls at the Staff Master → Deployment/Scheduling/Attendance/Leave control points.

Read order: **`01_architecture_integration.md`** → `02_rules_data_model.md` → `03_compliance_rule_catalog.md` → `04_guardrail_controls_by_module.md` → `05_severity_exceptions_approvals.md` → `06_dashboards_kpis_reports.md` → `07_test_acceptance_criteria.md`.

## Document map
| # | Document | Contents |
|---|---|---|
| 01 | Architecture & HNWMS integration | Positioning, control domains, evaluation points, integration model, principle |
| 02 | Rules data model & ERD | Mermaid ERD + entity specs (rule master, params, evaluation, exceptions, audit, staffing) |
| 03 | Compliance rule catalogue | 55 rules (LAB-WH/RS/OT/LV/CT, CBA-LIC/CRED/COMP/TRAIN/STAFF/SKILL/SAFE, HOS-POL) |
| 04 | Guardrail controls by module | Which rule fires in M1/M3/M4/M5/M6/M7/M8/M9/M10/M12/Staff Master/Payroll |
| 05 | Severity, exceptions & approvals | 4-level severity, employee/shift status, exception & approval authority matrix |
| 06 | Dashboards, KPIs & reports | Nursing Director KPIs, dashboard layers, alerts, report set |
| 07 | Test & acceptance criteria | Rules-engine + per-domain + exception/audit + KPI test cases |

## Artifacts
| File | Contents |
|---|---|
| `artifacts/ddl_compliance_engine.sql` | PostgreSQL DDL: rule master + scope/parameter, calendar, eligibility snapshot, evaluation, exception, audit, compliance status, staffing/skill-mix |
| `artifacts/compliance_rule_catalog.csv` | Machine-readable seed of the 55-rule catalogue (codes, category, trigger, severity, action, legal reference, module, exception flag) |

## Headline design points
- **Control point principle:** Staff Nurse Master Data + Rules Engine is evaluated **before** a nurse is assigned/scheduled/approved for OT/leave.
- **Balance ≠ safe:** Leave approval also checks departmental staffing coverage; schedule approval checks minimum staffing + skill mix + shift patterns, not just individual legal eligibility.
- **No silent overrides:** exceptions are reason/risk/mitigation-gated, time-limited, multi-approver, fully audited.
- **Parameterised & seasonal:** thresholds are configurable & effective-dated (Ramadan, holidays) — no hard-coded compliance.
- **Authoritative note:** defaults reflect the spec's stated values (8h/48h, 6h/36h Ramadan, 21→30-day leave, OT = wage+50%). Confirm all parameters against current law/policy/CBAHI before go-live.
