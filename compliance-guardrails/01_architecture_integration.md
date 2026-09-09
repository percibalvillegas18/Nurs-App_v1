# HNWMS Compliance Guardrail Layer — Saudi Labor Law & CBAHI
## Architecture & HNWMS Integration (Design Document)

**Version:** 1.0 · **Date:** 2026-09-09
**Scope:** Operationalize Saudi Labor Law (HRSD/MOL) + CBAHI + Hospital Policy as an **automated guardrail/decision layer** inside the HNWMS — replacing manual, document-based checking.

> Companion files in this folder: `02_rules_data_model.md`, `03_compliance_rule_catalog.md`, `04_guardrail_controls_by_module.md`, `05_severity_exceptions_approvals.md`, `06_dashboards_kpis_reports.md`, `07_test_acceptance_criteria.md`, `README.md`, and `artifacts/ddl_compliance_engine.sql` + `artifacts/compliance_rule_catalog.csv`.
> This doc is written against the existing `HNWMS_Complete_Package.md` (Staff Nurse Master Data SSOT; modules M1–M13).

---

## 1. Positioning & Core Principle

The package already states the goal (safe, compliant rostering) but relies on **manual** rule-following by HR/Nursing. This design inserts an **automated control point** so the system **prevents or flags** transactions that would create labor-law, credentialing, staffing, or patient-safety risk.

**Core principle (per the spec and the package):**

> The **Staff Nurse Master Data + Compliance Rules Engine** is the control point **before** a nurse is assigned to a shift / an OT is approved / a leave is granted / a deployment is published.

The rules engine is a **cross-cutting horizontal layer** (like Module 9) that *evaluates* but does not own master/transactional data — it reads from the modules and enforces decisions on them. It is not a "static document"; it is real-time ALLOW / INFORM / WARN / BLOCK logic with controlled exceptions.

```text
              STAFF NURSE MASTER DATA (SSOT)
                       │
    ┌──────────────────┼──────────────────────┐
    ▼                  ▼                      ▼
  HR/HCM + M10       LMS / M11 + M8        SCFHS + M3 (Credentialing)
  (contract/status)  (training/competency)  (license/credential)
    │                  │                      │
    └──────────────────┼──────────────────────┘
                       ▼
            COMPLIANCE RULES ENGINE  (this layer)
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
   Labor Law      CBAHI Rules     Hospital Policy
    Rules            Rules           Rules
         │             │              │
         └─────────────┼──────────────┘
                       ▼
        ┌────────────────────────────┐
        │     COMPLIANCE DECISION    │   ALLOW / INFORM / WARN / BLOCK
        └────────────────────────────┘
                       │
      ┌────────────────┼─────────────────┐
      ▼                ▼                 ▼
  NURSING SCHEDULER   ATTENDANCE        LEAVE        (M5)          (M6)        (M7)
      │                │                 │
      └────────────────┼─────────────────┘
                       ▼
                 DEPLOYMENT (M4)  ·  PAYROLL
                       ▼
              COMPLIANCE AUDIT (immutable)
                       ▼
             NURSING DASHBOARD (M9 + new compliance KPIs)
```

---

## 2. What the Engine Guards (control domains)

Mapped one-to-one from the spec, each resolved to rule codes in `03`:

1. **Working hours & rest** (LAB-WH-*, LAB-RS-*) — daily/weekly/Ramadan hours, rest between shifts, weekly rest, consecutive & double shifts, holiday work.
2. **Overtime** (LAB-OT-*) — eligibility, approval, hour caps, rate (hourly + 50%), holiday/emergency OT, payroll interface, audit.
3. **Annual & other leave** (LAB-LV-*) — entitlement/balance/accrual/carry-forward/expiry/pro-rata, and the **critical staffing-coverage gate** (approval must not create unsafe staffing).
4. **Contract & employment** (LAB-CT-*) — expiry/probation/renewal, position/title/salary mismatches, wage-category transfer agreement, unauthorized transfer, termination, end-of-service.
5. **Professional licensing / credentialing / competency** (CBA-LIC/CRED/COMP, CBA-TRAIN) — license/credential/competency validity before assignment, mandatory & patient-safety training.
6. **Minimum staffing & skill mix** (CBA-STAFF-*, CBA-SKILL-*) — required vs scheduled staffing by census/acuity/unit type; skill-mix (RN/Senior/Charge/specialty) presence.
7. **Patient-safety & quality** (CBA-SAFE/MED/IP/EM/INCID/QUAL/DOC) — unsafe-assignment prevention, medication/IP/emergency competency, incident escalation, file completeness, quality KPIs.
8. **Hospital policy** (HOS-POL-*) — shift patterns, night-shift frequency, weekend distribution, rolling OT exposure, unit authorization.

---

## 3. Evaluation Points (where the engine is invoked)

The engine is invoked **pre-write** (block before the bad transaction persists) and **reactively** (validate clock data, flag drift):

| Transaction / event | Guarded in module | Engine call | Typical gates |
|---|---|---|---|
| Roster/shift candidate publish | M5 | PRE-WRITE per row | license/credential/competency valid; hours/rest/OT caps; double/consecutive; skill mix & minimum staffing for the unit |
| OT approval | M6 | PRE-APPROVE | eligibility, caps, rate, authorization chain |
| Attendance/punch validation | M6 | POST + on-the-fly | hours vs scheduled, weekly rollups, OT detection |
| Leave approval | M7 | PRE-APPROVE | balance AND staffing coverage (not balance alone) |
| Deployment/assignment/redeployment | M4 | PRE-WRITE | eligibility check incl. license/credentials/competency/department authorization; transfer authorization |
| Position/contract/pay change | Staff Master / M10 | PRE-WRITE | title/position/salary mismatch; wage-category transfer agreement; status validation |
| License/credential/competency state change | M3/M8 | TRIGGER | re-evaluate affected scheduled shifts; alert/auto-replace |
| Roster read / analytics | M9 | READ/AGG | compliance KPIs, staffing gaps, dashboard |
| Payroll export | M6/Payroll | PRE-EXPORT | only approved, compliant OT/hours exported |

Each evaluation produces an **auditable evaluation_run + per-rule result** and an **ALLOW / WARN / BLOCK** verdict (lowest-severity that applies).

---

## 4. Guardrail examples (decision flow)

**Working-hours example**
```text
Staff Nurse → Existing scheduled hours + new requested shift
  → Compliance Engine
       ├─ within permitted limits  → ALLOW
       ├─ approaching threshold   → WARNING  (approval/escalation)
       └─ exceeds rule            → BLOCK / ESCALATE
```

**"Can Nurse A be scheduled?" (license gate)**
```text
Employment Active? → License Valid? → Required Credential Valid?
→ Required Competency Valid? → Department Authorized?
      YES → Schedule        NO → BLOCK
```

**Staffing/skill-mix (the key safety controls)**
```text
Patient Census + Acuity + Unit Type + Required Skill Mix
  → Required Staffing  → Compare vs Scheduled Staffing
       GREEN (meets) · AMBER (risk) · RED/BLOCK (below requirement)
```
The engine must **not** auto-approve a schedule merely because every employee is legally eligible — it evaluates **operational and patient-safety** requirements (staffing level + skill-mix + shift patterns).

---

## 5. HNWMS Integration model & dependencies

| Feed | Provider | What the engine reads |
|---|---|---|
| Employment/contract/status/position/grade | Staff Master SSOT + HR/M10 | eligibility, authorization, mismatch rules |
| License/registration | M3 (SCFHS-verified) | CBA-LIC-* |
| Credentials | M3 | CBA-CRED-* |
| Competency | M8 | CBA-COMP-* |
| Training | M11/LMS | CBA-TRAIN-* |
| Scheduled hours / roster | M5 | hours/rest/OT, staffing & skill-mix |
| Actual attendance/OT | M6 | OT rules, weekly caps |
| Leave | M7 | leave rules + coverage |
| Census / acuity | EMR (ext.) | CBA-STAFF-* demand |
| Manpower plan | M1 | required staffing / skill mix |

**Engine position vs modules:** The engine is an **evaluator/controller**, not a module that owns records. It reuses module data and writes only: evaluation results, exception requests, compliance status, and the audit log. It must NOT create duplicate employee/license data — those remain SSOT-owned (M3/M8/Staff Master).

**Interface with existing "regulatory alignment" & M9:** M9 already lists regulatory compliance reports (CBAHI, MOH, Nitaqat/GOSI). This layer is the enforcement upstream of those reports; the same data feeds M9 dashboards and adds the compliance KPIs in `06`.

---

## 6. Data-model & artefacts summary

Full entity spec + Mermaid ERD in `02_rules_data_model.md`; runnable DDL in `artifacts/ddl_compliance_engine.sql`. The **`compliance_rule` master table** (with scope + parameter tables) is the configurable rule catalogue; thresholds are **parameterised** (not hard-coded) so HR/Legal/DON can tune and seasonally adjust (Ramadan, public holidays) without code.

Full rule catalogue (55 rules) with codes is in `03_compliance_rule_catalog.md` and `artifacts/compliance_rule_catalog.csv`.

**Authoritative note:** Default thresholds in this package reflect the values stated in the spec (e.g. 8h/48h standard, 6h/36h Ramadan, ≥21 days leave rising to ≥30 after 5 yrs, OT at hourly wage + 50%). As a senior-implementation control, **every default parameter must be confirmed against the current Saudi Labor Law and the hospital's approved policies and CBAHI edition before go-live** — parameters are intentionally editable in `compliance_rule_parameter`.
