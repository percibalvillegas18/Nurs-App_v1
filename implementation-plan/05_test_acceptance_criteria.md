# Test & Acceptance Criteria

Companion to the implementation plan. Two sections: **import/validation test cases** (data-integrity focused, grounded in the real CSV) and **workflow/functional acceptance criteria**.

## 1. Import / validation test cases

| ID | Scenario / input | Expected result |
|---|---|---|
| TC-01 | Load full `Department & Bed.csv` (raw import) | 43 units staged; **4 departments**; raw totals match source: 524 bed values, 38 rows with a Bed + 5 blank-bed rows. Zero unexplained delta at staging. |
| TC-01a | Adjudicate to operational target | After reclassifying `EDAD` (7) & `ORAD` (2) Admin & Support rows → **515 assignable beds, 36 bedded + 7 non-bedded**; 9-bed delta logged as DQ-9. |
| TC-02 | Emergency dept rows (39,32,32,3,7) | Raw subtotal 113 (5 bed-value rows); operational 106 after `EDAD` reclassified non-bedded (4 bedded + 1 non-bedded). |
| TC-03 | `ICU Extension` (Critical, 14) vs `ICU Extension (2nd Location)` (Gen & Spec, 14) | Flagged as **near-duplicate** for human adjudication; both load under distinct departments pending decision. |
| TC-04 | `Plaster Unit` (Surgical) vs `Plaster Unit (2nd Location)` (Gen & Spec) | Same duplicate-detection rule; routed to adjudication. |
| TC-05 | `ED Navigation` vs `ED Navigator (2nd Location)` naming | Spelling-difference rule flags pair; no silent merge. |
| TC-06 | Endoscopy cell containing embedded newline+tab (`"(DIAGNOSTIC & SPECIALTY) \nEndoscopy Unit"`) | Parsed as one record; unit_name `Endoscopy Unit`; capacity 5; group normalized `SPECIALIZED & DIAGNOSTIC`. |
| TC-07 | 5 support/admin rows with blank Bed | Loaded as **non-bedded** (`is_bedded=false`, capacity null), not dropped or given capacity 0-as-error. Care_setting `NON_BEDDED_SUPPORT`. |
| TC-08 | Duplicate group labels `SPECIALIZED & DIAGNOSTIC` and `DIAGNOSTIC & SPECIALTY` | Both normalized to single controlled value `SPECIALIZED & DIAGNOSTIC`; counts reconciled. |
| TC-09 | Leading whitespace / full-width spaces on department & unit names | Trimmed; department match by normalized key; no phantom departments. |
| TC-10 | Capacity boundary: unit with 0 | Accepted only if explicitly a non-bedded support location; otherwise error. |
| TC-11 | Negative or non-numeric Bed | Rejected with descriptive error; staged record quarantined; not silently coerced. |
| TC-12 | Orphan unit (references missing department) | Referential integrity violation; load blocked; reported. |
| TC-13 | Duplicate unit in same department | Rejected / flagged by unique `unit_code`. |
| TC-14 | Re-run / re-import same file | Idempotent merge; no duplicate keys; history version appended; previous version preserved. |
| TC-15 | Unit code uniqueness across registry | `unit_code` UK enforced; conflict reported with suggested disambiguation. |

## 2. Functional / acceptance criteria (ADT · Bed · RBAC · Reporting)

| ID | Criteria | Given / When | Expected |
|---|---|---|---|
| AC-01 | Admission assigns bed | Patient admitted to Ward 4A with male/standard needs | Auto best-fit bed READY→OCCUPIED; occupancy +1; ADT A01 emitted; audit row written. |
| AC-02 | Bed feature matching | Admission needs ventilation → targets ICU unit only | Bed offered only from units/beds with `VENTILATED` feature; non-matching excluded. |
| AC-03 | Isolation block | Infection-control blocks a bed | Bed → BLOCKED (reason recorded); excluded from availability; occupancy recomputed. |
| AC-04 | Discharge releases bed | Discharge order on occupied bed | Bed OCCUPIED→CLEANING→(after SLA)→READY; occupancy −1; ADT A03. |
| AC-05 | Transfer moves state | Transfer Ward 4A→4B | Source bed CLEANING; target OCCUPIED; census/encounter location updated; A02 emitted. |
| AC-06 | Cleaning SLA escalation | Bed CLEANING > SLA | Prolonged-cleaning alert raised to Charge/Manager. |
| AC-07 | Threshold alert | Unit occupancy ≥ red threshold | Alert + surge/escalation triggered per §4.3; notification to scope roles. |
| AC-08 | Surge level ladder | Level breach auto-escalates | Level 1→2→3→4 as conditions persist; escalation ladder followed; decisions logged. |
| AC-09 | RBAC unit scoping | Charge Nurse (Ward 4A) opens ICU | Denied (403) by row-level scope; no ICU rows returned. |
| AC-10 | RBAC separation of duties | Scheduler attempts bed release | Denied — no bed-control permission. |
| AC-11 | Audit completeness | Any bed/registry/assignment change | Immutable log row: who/what/when/before/after/reason/source; retrievable in Audit viewer. |
| AC-12 | Capacity reconciliation | Daily census vs bed-registry occupancy | Deltas reported; mismatch =0 or explicit explainable exceptions. |
| AC-13 | Licensed-capacity integrity | `sum(bed is_licensed)` per unit | Equals unit `licensed_capacity`; else reconciliation flags it. |
| AC-14 | Reporting correctness | Occupancy % on known unit | = occupied ÷ licensed_capacity; rolls up dept/facility correctly. |
| AC-15 | Non-bedded support units | Open support unit occupancy | Not counted in bed capacity/occupancy; visible only to permitted roles. |
| AC-16 | Data segregation / masking | Non-clinical role views census | Counts/occupancy only; no MRN/PII exposed. |
| AC-17 | Effective-dated assignment | Manager transfer mid-period | Old assignment effective_to set; new begins; no history loss. |

## 3. Overall acceptance / go-live gate
- [ ] TC-01…TC-15 all pass (with zero unexplained reconciliation deltas).
- [ ] AC-01…AC-17 pass with documented evidence.
- [ ] Taxonomy signed off by DON + Licensing; physical room/bed audit done (if Bed-registry mode).
- [ ] UAT completed by at least one super-user per department; defects triaged to zero open critical/high.
- [ ] Rollback + re-import rehearsal successful; audit trail intact.
