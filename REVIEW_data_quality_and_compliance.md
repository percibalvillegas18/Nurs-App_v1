# Independent Audit — Source Reconciliation + Compliance/DDL Holes

**Date:** 2026-09-09  
**Scope:** Reconcile `Department & Bed.csv` against `Hospital_Nursing_Organizational_Structure.md`, then review the 55-rule catalogue and both PostgreSQL DDLs.  
**Status:** Findings recorded 2026-09-09. **Applied in-repo:** DQ-10/12/13 seed + `06` (capacity_class, Jail/UCC/OR reclass, 243→234 wording, occupancy formula); LAB-WH-001 pattern-aware Art. 100; LAB-RS-001 = Arts. 101–102; legal_reference column article-backed; WH-01 test no longer blocks 12h shift-system rosters. **Still open:** DQ-1/2 merge, DQ-14 coverage map, DQ-18 MOH license register, remaining DDL integrity holes in Part 2.

---

## How to read this

The two source files describe **different things**. Treating them as one master list is the main risk called out in `01_implementation_plan.md` §0 — and it is still the main risk.

| File | What it actually is | What it is not |
|---|---|---|
| Org chart | Workforce / accountability tree (E1–E2, L1–L7, functions) | A department/unit/bed register. No unit codes, no bed counts, no cost centers. |
| `Department & Bed.csv` | Physical/service location list with a numeric “Bed” column | A nursing reporting line. No DON, no Education/Quality/Informatics, no medical specialties as org nodes. |

They share **no natural key**. Join is only possible after a **coverage assignment** (position scoped to a location). That mapping does not exist in either source.

---

# Part 1 — CSV vs org chart (data quality)

## 1.1 Numbers that do check out

Computed from the raw CSV (43 data rows) and the normalized seed:

| Metric | Raw CSV | Normalized seed (`normalized_department_unit.csv`) | `org_rollup.csv` |
|---|---|---|---|
| Locations | 43 | 43 | 43 |
| Departments | 4 | 4 | 4 |
| Sum of numeric Bed | **524** | — | — |
| Assignable (is_bedded=yes) | 38 rows with a number | **36 units / 515 beds** | **515** |
| Non-bedded | 5 blank Bed | **7** (5 support + EDAD + ORAD) | 7 implied |
| Emergency | 113 | 106 (−7 EDAD) | 106 |
| Surgical | 31 | 29 (−2 ORAD) | 29 |
| Critical | 99 | 99 | 99 |
| General & Specialty | 281 | 281 | 281 |

DQ-9 arithmetic is correct: 7 + 2 = 9; 524 − 9 = 515.

`unit_code` values are unique (43/43).

## 1.2 Hygiene still in the raw file (DQ-6/DQ-5 confirmed)

- **Leading space on DEPARTMENT** for all Surgical (4) and Critical Care (3) rows.
- **Leading space on Nursing Unit** for most General & Specialty rows.
- **Embedded newline + tab** in Endoscopy (`"(DIAGNOSTIC & SPECIALTY) \t\nEndoscopy Unit"`).
- **CRLF** line endings.
- **Spelling:** `Fastrack` (should be Fast-track); `Obgyne` vs Obstetrics/Gynecology; `ED Navigation` vs `ED Navigator`.
- **Inconsistent group labels:** `(SPECIALIZED & DIAGNOSTIC)` vs `(DIAGNOSTIC & SPECIALTY)` — DQ-3, already normalized in the seed.

The loader **must** strip + collapse whitespace; the seed already does. Do not load the raw CSV directly.

## 1.3 Structural mismatch: org chart lines vs CSV departments

### Nursing operations (org chart) vs CSV home

| Org-chart clinical line (Nursing Operations) | CSV home | Fit |
|---|---|---|
| Emergency Nursing | `EMERGENCY & ACUTE CARE` (5 units) | Good |
| Operating Room Nursing | `SURGICAL & PERIOPERATIVE SERVICES` (OR, PACU, Plaster, OR Admin) | Partial — Plaster is procedure space, not OR nursing |
| ICU / Critical Care | `CRITICAL CARE & INTENSIVE SERVICES` (ICU Main, ICU Ext, HDU) | Good — until “2nd Location” rows |
| Inpatient / Medical Nursing | Buried in `GENERAL & SPECIALTY` · ACUTE GENERAL CARE | Weak — no Medical vs Surgical split |
| Pediatric Nursing | One row: Pediatric Ward (15) | Weak — also ED Maternal & Child (32) lives under Emergency |
| Maternity / Obstetric Nursing | Labor & Delivery (15) + Obgyne (17) | Weak — plus ED Maternal & Child (32) |
| Specialty Nursing | Catch-all remainder of Gen & Spec (31 of 43 units) | Overloaded dump |

**Nursing functional orgs that have zero CSV locations (expected, but unmapped):**  
Nursing Education & Development · Nursing Quality & Patient Safety · Nursing Informatics · Nursing Administration / Workforce Management (Manpower Planning → Analytics). These must be `org_node` rows, not `nursing_unit` rows. The seed has none of them.

**Hospital executive chart vs CSV:** Medical Director specialties (Internal Medicine, Cardiology, Anesthesia, Orthopedics, …), Pharmacy, Laboratory, Quality, IT, Patient Services **do not appear** as departments. Radiology, Blood Collection, Non-Invasive Lab appear as *nursing units with “beds”* — they are diagnostic services, not nursing wards.

**Implication:** You cannot derive the L1–L7 reporting tree from the CSV, and you cannot derive bed capacity from the org chart. P0 must produce an explicit **position → location coverage map** (Unit Manager of Ward 3A, Charge of ICU Main, …). That artifact does not exist yet.

## 1.4 “Bed” is not one thing — mixed capacity semantics (new **DQ-10**)

The CSV column is named `Bed`. The plan stores it as `nursing_unit.licensed_capacity` and, in bed-registry mode, auto-provisions that many `bed` rows. That is only valid if every number is a **licensed inpatient bed**. It is not.

| Unit | Count | Likely real meaning | Treat as licensed inpatient bed? |
|---|---|---|---|
| ICU Main / Ext / HDU | 79 / 14 / 6 | Critical-care beds | Yes (pending audit) |
| Wards 3A/4A/4B/5B, Rehab, Pedi, Obgyne, AKU, Jail | 20–12 | Inpatient beds | Yes (Jail is inpatient, not ambulatory) |
| Labor & Delivery | 15 | LDR / delivery rooms | Confirm vs MOH bed class |
| ED Resus / Fastrack / Maternal & Child | 39 / 32 / 32 | ED stretchers / observation | Usually **not** in licensed bed census |
| ED Navigation | 3 | Wayfinding / holding? | Unlikely |
| OR Suites | 12 | Operating **tables** | No |
| PACU | 8 | Recovery bays | No (or separate PACU class) |
| Plaster (×2) | 9 + 9 | Procedure rooms | No |
| OPD | 19 | Clinic rooms/chairs | No |
| UCC | 15 | Urgent-care bays | ED-like, not Gen&Spec ward |
| Radiology / EEG / Blood / Endoscopy | 6 / 2 / 2 / 5 | Modality rooms / chairs | No |
| Diabetic Center / Specialty Clinics | 10 / 4 | Clinic slots | No |
| Day Surgery / Day Care | 9 / 3 | Trolleys / chairs | Ambulatory, not overnight beds |
| Newborn Screening | 3 | Screening stations | No |
| Discharge Unit | 2 | Discharge lounge | No |
| ED Admin / OR Admin | 7 / 2 | Offices (already reclassified) | No |

**If 515 is posted as licensed hospital beds, the figure is inflated.** A first-pass “true inpatient” band (wards + ICU/HDU + Jail, excluding ED/OR/PACU/clinics/diagnostics, and treating 2nd-location ICU/Plaster as duplicates) is roughly **~250–270**, not 515. That delta will break:

- MOH / CBAHI bed-license reconciliation  
- Occupancy % (`occupied ÷ licensed_capacity`) in `01` §6  
- M1 demand (`Required Nurses = Census ÷ ratio`) if “beds” include chairs and tables  

HNWMS M1.2 already distinguishes **licensed / approved / operational / staffed / occupied / planned**. The location DDL has only `licensed_capacity` + `is_bedded`. **DQ-10:** add `capacity_class` (INPATIENT_LICENSED / ED_STRETCHER / OR_TABLE / PACU_BAY / AMBULATORY_CHAIR / PROCEDURE_ROOM / SUPPORT) and **do not** auto-provision `bed` rows for non-inpatient classes.

## 1.5 Duplicate / mis-parented “2nd Location” rows (DQ-1, DQ-2 — still open)

| Seed code | Name | Dept / care_setting | Count | Twin |
|---|---|---|---|---|
| `ICUE_2` | ICU Extension (2nd Location) | Gen&Spec / **AMBULATORY_DIAGNOSTIC** | 14 | `ICUE` Critical Care 14 |
| `PLAS_2` | Plaster Unit (2nd Location) | Gen&Spec / AMBULATORY_DIAGNOSTIC | 9 | `PLAS` Surgical 9 |
| `EDNA_2` | ED Navigator (2nd Location) | Gen&Spec / AMBULATORY_DIAGNOSTIC | 5 | `EDNA` Emergency 3 |

Signals already in `07`: identical counts on ICU/Plaster; clinically impossible parent group. Additional signal this audit adds:

- Classifying an ICU extension as `AMBULATORY_DIAGNOSTIC` is a **taxonomy error even if the site is real**.  
- UCC (15) sits under Gen&Spec, not Emergency — likely the same “everything leftover dumped in column 1 = GENERAL & SPECIALTY” pattern.  
- ED Maternal & Child (32) vs inpatient L&D/Obgyne/Pedi is a possible **double-count of maternity/pediatric capacity** (new **DQ-11**).

Default in `07` (merge ICU/Plaster duplicates) is reasonable. Until DON + Licensing sign the physical audit, **do not** treat 515 as an auditable licensed total.

## 1.6 Classification errors in the *cleaned* seed (new **DQ-12**)

These survived normalization. They will poison staffing ratios and ADT if loaded as-is.

| Code | Problem | Recommended care_setting / unit_type |
|---|---|---|
| `JAIL` | Jail Ward, 12, tagged `AMBULATORY_DIAGNOSTIC` | `INPATIENT_WARD` (or `SECURE_INPATIENT`); needs security-clearance skill-mix |
| `URGE` | Urgent Care under Gen&Spec | Parent under Emergency (or own ED-family group); not diagnostic |
| `ICUE_2` | ICU as ambulatory | If kept: Critical Care / ICU |
| `PLAS` / `PLAS_2` | Plaster as bedded service line | Procedure / clinic, `is_bedded=no` unless audit finds overnight trolleys |
| `OPER` | OR 12 as licensed beds | `unit_type=OR`, capacity_class=OR_TABLE, not ADT beds |
| `RECO` | PACU 8 as licensed beds | `unit_type=PACU` |
| `OUTP`, `SPEC`, `DIAB`, `RADI`, `ELEC`, `BLOO`, `ENDO`, `NEWB`, `DISC`, `EDNA` | “Beds” on clinics/diagnostics/navigation | Non-ADT resources; `is_bedded=no` or a non-bed resource table |
| `WARD`…`WARD_4` | Opaque codes | Use `W3A`, `W4A`, `W4B`, `W5B` |

`unit_code` generation (first 4 letters + `_2`) is unstable. Next “Ward 5A” becomes `WARD_5`. Natural keys should encode the **ward identity**.

## 1.7 Document inconsistencies (new **DQ-13**)

| Claim | Where | Reality |
|---|---|---|
| Top-level service-line beds **243** called “normalized” | `06` §2 | 243 = **raw** 113+31+99. After DQ-9 it is **234** (106+29+99). `org_rollup.csv` is correct (234). `06` mixes raw and operational in one “normalized” sentence. |
| Occupancy = occupied ÷ **licensed_capacity** | `01` §6 | HNWMS M1.2: occupied ÷ **operational** beds. Using 515 (or 524) as denominator will understate occupancy. |
| “38 bedded” then “36 bedded” | `06` | Both true at different stages; the summary table still leads with 38. Fine if labelled; easy to mis-quote. |
| ERD: `UNIT_GROUP \|\|--o{ NURSING_UNIT` | `02` | Seed leaves `unit_group` **blank** for all Emergency/Surgical/Critical units (nullable FK). Either require a group for every unit (recommended) or change the ERD to optional. |
| “All changes effective-dated; no destructive deletes” | `02` §3 | Location DDL has **no** `effective_from`/`effective_to`, no `deleted_at`, no history tables except `bed_state_log`. |

## 1.8 What the org chart still needs as data (not in CSV)

To stand up Org Directory + RBAC as specified:

1. **org_node tree** for Hospital Director → E2 leads, and DON → L2 functions → L3 unit managers.  
2. **workforce_position** catalogue (DON, ADON, Workforce Mgr, Education, Quality, Informatics, Unit Manager, Charge, Team Leader, Staff Nurse, Assistant).  
3. **assignment** rows: which person, which position, **which unit/dept**.  
4. Cost center (mentioned in system mapping, absent from DDL).  
5. Confirm org **scope**: nursing line only vs full hospital (sign-off item 6 in `06` §5) — still open.

None of (1)–(4) can be generated from the CSV.

## 1.9 Recommended P0 dispositions (beyond existing DQ-1…9)

| ID | Finding | Blocking? | Proposed default |
|---|---|---|---|
| DQ-10 | Mixed “Bed” semantics | **Yes** | Add `capacity_class`; only INPATIENT_LICENSED (+ maybe ED_STRETCHER as a separate pool) generate `bed` rows |
| DQ-11 | Maternity/pediatric split across ED + inpatient | Yes for census | Keep both; tag ED Maternal & Child as ED observation, not obstetric ward |
| DQ-12 | Seed care_setting / unit_type wrong (Jail, UCC, OR, clinics) | **Yes** | Reclassify before load; Jail = inpatient; OR/PACU/clinics ≠ licensed beds |
| DQ-13 | 243 vs 234; occupancy formula; missing effective dating | Medium | Fix `06` wording; occupancy uses operational beds; add effective dates to DDL |
| DQ-14 | No position↔location coverage map | **Yes** for RBAC/scheduling | Build from org chart + unit list; DON sign-off |
| DQ-15 | `unit_code` scheme (`WARD`, `WARD_2`) | Medium | Replace with stable codes (`W3A`, `ICU`, `ED-RESUS`, …) |
| DQ-16 | UCC parented to Gen&Spec | Medium | Re-parent to Emergency unless facility org says otherwise |
| DQ-17 | Support names (`Non-Maternal & Child Health Coord`) | Low | Confirm real names in audit (possible leftover “Non-” from grouping) |
| DQ-18 | No MOH/CBAHI licensed-bed total to reconcile against | **Yes** for go-live | Obtain the facility bed-license register; 515 must not be submitted as licensed until that match |

**Do not load `normalized_department_unit.csv` into production until DQ-1/2/9/10/12/18 are signed.**

---

# Part 2 — Compliance rules and DDL holes

The 55-rule layer is a coherent *control-point* design (pre-write ALLOW/WARN/BLOCK, no silent override, leave checks coverage not just balance). The holes below are what would fail legal review, hospital operations, or a schema review.

## 2.1 What is solid

- Control-point principle matches HNWMS BR #11.  
- 55 unique codes; counts match the catalogue (LABOR 35 · CBAHI 16 · HOSPITAL 4).  
- Parameterised thresholds + Ramadan calendar window.  
- Exception path requires reason / risk / mitigation / time limit / multi-approver.  
- Fail-closed + DON emergency override (`05` §6) is the right degraded-mode stance.  
- Verdict = strictest result is consistently specified in `02` §3 and `05` (ignore the “lowest severity” slip in `01` §3 and the DDL comment on `evaluation_run.overall_verdict`).

## 2.2 Legal accuracy — rules that are wrong or dangerous as specified

Defaults “must be confirmed against current law” is not enough when **acceptance tests hard-code the wrong default**.

### Critical: LAB-WH-001 as BLOCK at 8h, `exception_allowed=False`

Saudi Labor Law **Article 98**: 8h/day or 48h/week (Ramadan 6/36 for Muslim workers) — the catalogue has this right as a *baseline*.

It does **not** have:

- **Art. 99** — some operations 9h; hazardous 7h.  
- **Art. 100** — **shift work** may exceed 8/48 if the **3-week average** stays at 8/48, with ministry approval. This is how 12-hour nursing rosters are typically legal.  
- **Art. 101** — no more than **5 consecutive hours** without ≥30 min rest/prayer/meal; worker shall not remain at the workplace beyond the daily presence cap (commonly applied as 12h). Rest is **not** working time (Art. 102).  
- **Art. 104** — weekly rest **Friday**, ≥24 consecutive hours, paid.  
- **Art. 108** — listed exemptions.

**Acceptance test WH-01** (“Shift takes a nurse > 8 h/day → BLOCK”) would **reject every 12-hour ICU/ED roster**. Combined with `exception_allowed=False`, there is no legal path to publish a standard nursing shift.

**Fix:** LAB-WH-001 must be parameterised by **work pattern** (standard day vs approved shift system). For shift units, evaluate **average hours over the reference period** (Art. 100), not a hard 8h wall. Presence cap (Art. 101) is a separate rule. Exception flag cannot be False for hospital shift workers.

### LAB-RS-001 “≥ 11h continuous rest” is not Saudi Labor Law

An 11-hour daily rest is **EU Working Time Directive**, not HRSD. Saudi law’s rest rules are intra-shift breaks (Art. 101) and weekly Friday rest (Art. 104). Fatigue rest-between-shifts belongs under **HOS-POL-*** (hospital/CBAHI safety), not `LAB-RS` with a fake labor-law citation. As BLOCK + `exception_allowed=False`, a 07:00–19:00 then 07:00 next day (12h rest) passes, but many legitimate 8h rotations with ~8–10h off would be blocked if someone “corrects” the parameter to 11.

### LAB-WH-002 weekly 48h as WARNING only

If Art. 98 is the legal cap, exceeding it (outside Art. 100 averaging / approved OT) is a **violation**, not a dashboard warning. Inconsistent with LAB-WH-001’s BLOCK. Decide: either both are hard legal caps (with shift-averaging), or both defer to OT rules.

### Missing statutory leave types (HNWMS M7 lists them; catalogue does not)

HNWMS §7.1 already names sick, emergency, maternity, paternity, bereavement, study, unpaid. The engine only has annual + a vague “maternity/extended” (LAB-LV-007) with **no duration**. Typical private-sector baselines to encode as parameters (confirm 2026 text before go-live):

| Leave | Typical statutory baseline | Catalogue |
|---|---|---|
| Annual | Art. 109: ≥21 days; 30 after 5 consecutive years | LAB-LV-001/005 — OK |
| Sick | Art. 117: 30d full + 60d 75% + 30d unpaid (in a year) | **Missing** |
| Maternity | Sources currently split **10 weeks vs 12 weeks** — must confirm | LAB-LV-007, no number |
| Paternity / newborn | Often 3 days | Missing |
| Marriage | 5 days | Missing |
| Bereavement | 5 days | Missing |
| Hajj | 10–15 days, once, conditions | Missing |
| Weekly rest / Eid / National Day / Founding Day | Public holiday work = OT (Art. 107) | Only LAB-WH-005, no calendar of Saudi holidays |

### Other labor gaps vs HNWMS’s own glossary

HNWMS already cites **Nitaqat / GOSI** as regulatory reports (M9). **Zero rules.** Also missing:

- Iqama / work-permit / SCFHS *classification* (not just “license valid”) for expatriate nurses  
- Probation **max 90 days, extendable to 180 by written agreement** (LAB-CT-002 is an alert only)  
- Notice period / EOS (end-of-service) formula (LAB-CT-011 is “HR validates” with no calc)  
- GOSI contribution eligibility  
- Annual OT cap (practice/guidance often ~480h — confirm, do not invent)  
- On-call vs overtime distinction (HNWMS M5 has On Call; no rule)  
- Art. 101 meal/prayer break  
- Equal-pay / non-discrimination (Art. 3 / women’s work rules) — optional for a roster engine, but “Labor Law coverage” is overstated

### CBAHI / professional practice holes

Good: SCFHS license gate, credential, competency, mandatory training, staffing, skill-mix.

Thin or non-computable:

| Code | Hole |
|---|---|
| **CBA-SAFE-001** | “Unsafe assignment” has **no predicate**. It will either never fire or duplicate STAFF/SKILL/LIC. Needs explicit checks (acuity vs competency, isolation, high-alert meds, float without unit orientation). |
| **CBA-STAFF-002** | Ratio by unit/acuity — **no default ratios**. ICU vs ward vs ED vs OR are different; CBAHI/MOH edition must be bound per `unit_type`. |
| **CBA-SKILL-001** | No BLS/ACLS/PALS/NRP/TNCC **unit-required** certs (HNWMS M3.2 lists them). |
| **CBA-CRED-001** | One row for all credentials. Cannot express “ICU assignment requires ICU competency + ACLS”. That needs **requirement matrix** (position × unit_type × credential) — not in DDL. |
| Jail / maternity / peds | No security-clearance, no gender-of-nurse policy for female wards (common hospital policy in KSA), no pediatric-only competency. |
| Agency / locum / float pool | HNWMS glossary has Float Pool; no rule for contracted vs hospital staff, dual employment, or privilege. |
| PDPL | `01` §7 mentions PDPL; no rule, no data-class in DDL. |
| JCI | Glossary lists JCI; no rules. Fine if out of scope — say so. |

`legal_reference` on most rows is a paraphrase (“Saudi Labor Law + safety”), **not an article number**. Test pack §J requires “articles + CBAHI edition documented.” Currently fails its own gate.

## 2.3 Catalogue / severity model bugs

- **INFORM vs ADVISORY vs ALLOW vs WARN:** architecture uses ALLOW/INFORM/WARN/BLOCK; `severity_default` uses ADVISORY/WARNING/BLOCK/**ALLOW**; `evaluation_run` comment still says “lowest severity.” Pick one enum and use it in CSV, DDL CHECKs, and APIs.  
- **LAB-OT-004** severity ALLOW — a calculation is not a guardrail. Move to payroll logic; keep a VALIDATE that the rate parameter = 1.5.  
- **LAB-WH-003/004** action `RECALCULATE` is not an evaluation verdict. Recalc is a calendar effect; the *guard* is still WH-001/002 with seasonal parameters.  
- **CBA-SKILL-001** subcategory = `STAFFING` in CSV (should be `SKILL_MIX`).  
- **HOS-POL-004** overlaps CBA-CRED / unit authorization.  
- 13 rules have `exception_allowed=False`. At least LAB-WH-001 and LAB-RS-001 should not, in a hospital. License/employment BLOCK-without-exception is correct.

## 2.4 Org / bed DDL holes (`implementation-plan/artifacts/ddl_schema.sql`)

| Hole | Why it matters |
|---|---|
| No `capacity_class`, no operational vs licensed vs staffed | DQ-10; occupancy and MOH reporting |
| `licensed_capacity INTEGER NOT NULL DEFAULT 0` vs seed **blank** for non-bedded | Load will coerce to 0 or fail; ERD says “nil” |
| `UNIQUE (unit_id, room_id, bed_number)` with **nullable** `room_id` | PostgreSQL UNIQUE allows multiple NULLs → duplicate bed numbers |
| No exclusion/constraint: one **current** occupancy per bed | Two encounters can occupy one bed |
| `assignment.scope_id` polymorphic, **no FK** | Orphan scopes; ERD “must reference a real location” is unenforceable |
| `person` is 4 columns | Cannot evaluate Ramadan (religion), nationality (Nitaqat), gender (ward policy), FTE, contract type — and compliance engine needs those |
| No `effective_from` on facility/dept/unit | Contradicts `02` §3 |
| No soft-delete / status history | Contradicts “never reuse natural keys after soft-delete” |
| No `cost_center` | Called out in system mapping |
| No link `org_node` ↔ `department`/`nursing_unit` | Coverage map has nowhere to live except assignment |
| No CHECKs on status/type enums | `department_type` is free varchar |
| No `unit_type` in the CSV seed | DDL requires `unit_type NOT NULL` — loader must invent it |
| Occupancy formula not encoded | Views for census would help P4 |
| Two schemas, no shared `staff_id` / `unit_code` FK to HNWMS | See 2.6 |

RBAC tables promised in `01` §3 (`role`, `role_grant`, `permission`) **are not in the DDL at all**.

## 2.5 Compliance engine DDL holes (`ddl_compliance_engine.sql`)

| Hole | Why it matters |
|---|---|
| `staff_id`, `unit_code`, `dept_unit_id` are **untyped strings/bigints with no FK** | Engine can evaluate a ghost nurse on a ghost unit |
| No `facility_id` / tenant | Single-hospital today; still needed for audit partitions |
| `compliance_rule_parameter UNIQUE (rule_id, param_key, effective_from)` | In PostgreSQL, **NULL `effective_from` does not collide** — duplicate “current” params allowed |
| `working_calendar_adjustment` not actually related to parameters | ERD draws `compliance_rule_parameter \|\|--o{ working_calendar_adjustment` — false |
| `eligibility_snapshot` has no uniqueness `(staff_id, as_of)` | Duplicate snapshots; no invalidation when M3 license changes |
| Snapshot too thin | No religion, nationality, shift-system flag, unit authorizations list, cert set — so Ramadan, Nitaqat, HOS-POL-004 cannot be evaluated from it |
| No `overtime_candidate` / `punch_candidate` | `01` evaluation points include OT and punch; only shift + leave draft tables exist |
| No `credential_requirement(unit_type, position, credential_code)` | CBA-CRED/COMP/TRAIN cannot be data-driven |
| `skill_mix_rule` not effective-dated | Policy changes have no history |
| `staffing_requirement` no unique `(unit_code, shift, date)` | Duplicate demand rows |
| `guardrail_exception_request.risk_assessment` / `mitigation` **nullable** in DDL | `05` says mandatory. Schema does not enforce. |
| Approver columns are `VARCHAR(100)` names, not user ids | No SoD constraint (requester ≠ approver) in DB; only a test case (EX-03) |
| `compliance_audit_log` is a normal heap table | **Not immutable.** Anyone with UPDATE/DELETE can rewrite history. Need: no UPDATE/DELETE grants, or append-only (e.g. partitioned, trigger rejecting updates), hash-chain optional. |
| Almost no indexes except audit | `evaluation_rule_result(run_id)`, `shift_candidate(staff_id, shift_date)`, `staffing_requirement(unit_code, date)` will be hot |
| No CHECK on verdict/severity enums | “LOWEST” comment will become bad data |
| Degraded-mode **pending queue** (`05` §6) has no table | Fail-closed policy cannot be implemented as specified |
| No rule **version** / `rule_hash` on evaluation results | Changing a parameter rewrites history interpretation |
| Engine “must not duplicate staff/license data” vs `eligibility_snapshot` | Snapshot *is* a duplicate. Fine as a cache if TTL + invalidation exist — they don’t. |

## 2.6 The two DDLs do not meet

Org schema: `person.person_id`, `nursing_unit.unit_code`.  
Compliance schema: `staff_id`, `unit_code` varchar, no references.

HNWMS Staff Master is the declared SSOT. Neither DDL models it. If both scripts are applied to one database, you get **two employee tables and no join**. Integration contract (`09`) cannot be implemented from these scripts alone.

## 2.7 Tests that would fail a real hospital UAT

From `compliance-guardrails/07_test_acceptance_criteria.md`:

- **WH-01** BLOCK >8h — fails 12h roster (Art. 100).  
- **ST-04 NICU** — “illustrative”; registry has **no NICU**. Fine if rebound to `INTE`, but don’t ship the label into UAT scripts.  
- **ST-02** Medical ward 10 vs 9 → AMBER on CBA-STAFF-001, while CBA-STAFF-001 default is **BLOCK**. Severity collision.  
- **RG-07** Ramadan 6/36 for “applicable scope” — snapshot has no religion/Muslim flag.  
- **EX-04** “immutable audit” — schema allows updates.  
- **§J** legal_reference = article + CBAHI edition — CSV does not meet it.

---

# Priority punch-list

**Do before any registry load (P0)**  
1. Physical bed audit + DQ-1/2/9 sign-off.  
2. Introduce `capacity_class`; stop treating 515 as licensed beds.  
3. Reclassify Jail, UCC, OR, PACU, clinics/diagnostics in the seed; restable `unit_code`s.  
4. Fix `06` 243 vs 234.  
5. Draft position ↔ unit coverage map from the org chart.

**Do before any rules engine build**  
6. Rework LAB-WH-001/002 for Art. 100 shift averaging; move 11h rest to hospital policy; add Art. 101 break + Art. 104 Friday rest.  
7. Add sick / maternity (confirmed weeks) / Hajj / marriage / bereavement / paternity leave rules — or explicitly defer them to HR with a written out-of-scope.  
8. Replace paraphrase `legal_reference` with article + CBAHI edition + hospital policy ID.  
9. Make SAFE-001 computable; add unit×credential requirement matrix; add BLS/ACLS/PALS by `unit_type`.  
10. Unify severity enum; fix DDL comments (“strictest”, not “lowest”).

**DDL**  
11. FKs from engine `staff_id` / `unit_code` to Staff Master / `nursing_unit`.  
12. Enforce exception reason/risk/mitigation NOT NULL; unique current occupancy; unique param with coalesced dates.  
13. Append-only audit; degraded-mode queue table; OT/punch candidate tables.  
14. Add licensed vs operational capacity; RBAC tables actually named in `01`.  
15. Expand eligibility snapshot (religion, nationality, FTE, unit authorizations, certs) **or** evaluate live against SSOT (preferred) and drop the snapshot.

---

## Bottom line

- The **arithmetic** of 4 / 43 / 524 / 515 is consistent.  
- The **semantics** of “bed” and the **join** to the org chart are not. Loading the current seed as a licensed-bed register would misstate capacity by a large margin and mis-parent ICU/Plaster/UCC/Jail.  
- The **compliance design** is the right shape (pre-write engine, coverage gate, no silent override) but it is **not yet a Saudi hospital ruleset**: 8h BLOCK would stop 12h nursing, 11h rest is EU, statutory leave/GOSI/Nitaqat/iqama are missing, and both DDLs lack the integrity and Staff-Master join the prose assumes.

Confirm DQ-10/12/18 and LAB-WH-001 with DON + Licensing + HR/Legal before Wave P1.
