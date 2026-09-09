# Source Reconciliation & Cleaned Taxonomy

This document records the **data-quality analysis** of the two source files, the **canonical cleaned taxonomy** used for loading, and the **open questions that need sign-off** before go-live. It is the factual basis for `03_configuration_checklist.md` and `05_test_acceptance_criteria.md`.

> Source files: `Hospital_Nursing_Organizational_Structure.md` (whole-hospital + nursing org chart) and `Department & Bed.csv` (department/unit/bed).
>
> **2026-09-09 update:** Applied **DQ-10 / DQ-12 / DQ-13** to the registry seed (`normalized_department_unit.csv`, `org_rollup.csv`). The CSV column named `Bed` is **not** a single licensed-inpatient measure. **Do not quote 515 (or 524) as MOH/CBAHI licensed beds.**

---

## 1. Source inventory & structure

**`Department & Bed.csv`** — 3 columns: `DEPARTMENT, Nursing Unit, Bed`. **44 rows = header + 43 data rows.**

**`Hospital_Nursing_Organizational_Structure.md`** — structured Markdown containing:
- Nursing org chart (Director of Nursing → Deputy → Nursing Ops clinical areas → Nursing Administration/Workforce → Nursing Unit Management).
- Recommended management hierarchy **L1–L7** (DON → … → Nursing Assistant) and executive structure **E1–E2**.
- Expanded whole-hospital org chart (Hospital Director → Medical/CMO, DON, Operations/Admin, Quality, Pharmacy/Diagnostics, IT/Health Informatics, Patient & Corporate Services).
- Nursing reporting line, enterprise integration matrix, and management dashboard structure.

The two files **do not share a natural key**. The org chart is a workforce/accountability tree; the CSV is a location/capacity list. Join is only via a **position → location coverage map** (not in either source — see DQ-14 / §5).

---

## 2. Reconciliation results (computed)

### 2.1 Raw source (unchanged)

| Metric | Value | Source |
|---|---|---|
| Departments | **4** | CSV col 1 (after trim) |
| Total locations | **43** | CSV |
| Rows with a numeric Bed | **38** | CSV col 3 |
| Support/admin rows with blank Bed | **5** | CSV |
| **Sum of Bed column** | **524** | raw |

**Raw dept sums:** Emergency & Acute Care **113** · Surgical & Perioperative **31** · Critical Care & Intensive **99** · General & Specialty **281**.

**Raw top-level service-line sum (Emergency+Surgical+Critical) = 113+31+99 = 243.** That 243 figure is **raw CSV only**. After DQ-9 it is **234** (106+29+99). After DQ-10 it is **not** a licensed-bed total at all (those three departments mix stretchers, tables, bays, and ICU beds).

### 2.2 After DQ-9 (admin/support numeric “beds” removed from assignable)

Two Admin & Support rows carried a number but are not patient beds: `ED-ADMIN` 7 + `OR-ADMIN` 2 = **9**. Mixed-class remainder **515**. This is **historical / mixed-class**, kept for source traceability. It is **not** operational licensed capacity.

### 2.3 After DQ-10 / DQ-12 (capacity class — current seed)

See `artifacts/org_rollup.csv`. Resource counts still sum to the raw 524 when `source_bed_count` is used.

| capacity_class | Units | Resource count | ADT `bed` rows? | Counts as MOH licensed inpatient? |
|---|---|---|---|---|
| **INPATIENT_LICENSED** | 14 | **281** (incl. `ICU-EXT-2` 14) | Yes | **Yes — pending license register** |
| ↳ excl. DQ-1a pending duplicate | 13 | **267** | Yes | Proposed if `ICU-EXT-2` merged |
| ED_STRETCHER | 4 | **118** | Optional separate ED pool | No |
| PACU_BAY | 1 | **8** | Optional PACU pool | No |
| OR_TABLE | 1 | **12** | No | No |
| PROCEDURE_ROOM | 8 | **41** | No | No |
| AMBULATORY_CHAIR | 6 | **47** | No | No |
| SUPPORT | 9 | **0** (source numbers 17 not assignable) | No | No |

**Patient-placeable (`is_bedded=yes`):** 19 units · 281 + 118 + 8 = **407** slots (inpatient + ED stretchers + PACU). Still not a licensed-bed total.

**Department unit counts after UCC re-parent:** Emergency **6** · Surgical **4** · Critical **3** · General & Specialty **30**.

**Check:** 281+118+12+8+41+47 + support source 17 = **524** ✓.

---

## 3. Data-quality findings

| # | Finding | Detail | Disposition |
|---|---|---|---|
| DQ-1 | **Near-duplicate unit names** | `ICU-EXT` (Critical Care, 14) vs `ICU-EXT-2` (Gen & Spec, 14); `PLASTER` (Surgical, 9) vs `PLASTER-2` (Gen & Spec, 9) | **Open.** Seed keeps both rows. `ICU-EXT-2` care_setting corrected to `CRITICAL_CARE` / `INPATIENT_LICENSED` (no longer ambulatory). `PLASTER-2` classed `PROCEDURE_ROOM`. Merge vs re-parent still needs physical audit (`07`). |
| DQ-2 | **Spelling + count** | `ED-NAV` (3, Emergency) vs `ED-NAV-2` (5, Gen & Spec) | **Partial.** Both classed `SUPPORT` / non-bedded (navigation is not beds). Name/count merge still open. |
| DQ-3 | **Inconsistent group labels** | `SPECIALIZED & DIAGNOSTIC` vs `DIAGNOSTIC & SPECIALTY` | **Applied.** Single controlled group name `SPECIALIZED & DIAGNOSTIC` (diagnostic units also have `care_setting=DIAGNOSTIC`). |
| DQ-4 | **Support/admin blank Bed** | 5 SUPPORT & ADMINISTRATIVE rows | **Applied.** `is_bedded=no`, `capacity_class=SUPPORT`. Confirm on audit they have no beds. |
| DQ-5 | **Malformed cell** | Endoscopy quoted field with newline+tab | **Applied.** Parsed as `ENDO` / Endoscopy Unit / 5. |
| DQ-6 | **Leading whitespace** | Surgical & Critical dept names; most Gen & Spec unit names | **Applied** in seed (strip). Raw file unchanged. |
| DQ-7 | **Grouping not uniform** | Only Gen & Spec had parenthetical groups | **Applied.** Every unit now has a `unit_group` (EMERGENCY / PERIOPERATIVE / CRITICAL CARE / ACUTE GENERAL CARE / SPECIALIZED & DIAGNOSTIC / SECURE CARE / SUPPORT & ADMINISTRATIVE SERVICES). |
| DQ-8 | **Capacity is unit-level only** | No room/bed numbers | Unchanged. Physical audit still required. Provision `bed` rows **only** for `INPATIENT_LICENSED` (and optionally ED/PACU pools) — not for OR/procedure/clinic/support. |
| DQ-9 | **Admin numeric “Bed”** | ED Administration 7, OR Administration 2 | **Applied.** `SUPPORT`, non-bedded. Mixed-class 524→515 delta retained as history. |
| **DQ-10** | **Mixed “Bed” semantics** | CSV `Bed` mixes licensed inpatient, ED stretchers, OR tables, PACU bays, clinic chairs, procedure rooms | **Applied in seed.** New `capacity_class`. Occupancy and MOH reporting use **INPATIENT_LICENSED** only (281 incl. pending DQ-1a / **267** if merged). |
| **DQ-11** | **Maternity/pediatric split** | ED Maternal & Child (32 stretchers) vs L&D (15) + Obgyne (17) + Peds (15) | **Applied.** `ED-MC` stays ED_STRETCHER (`DQ11_ED_OBS`); inpatient maternity/peds stay `INPATIENT_LICENSED`. Do not add them together as one obstetric bed total. |
| **DQ-12** | **Wrong care_setting / parent** | Jail tagged ambulatory; UCC under Gen & Spec; OR/PACU/clinics as licensed beds; opaque `WARD`/`WARD_2` codes | **Applied.** Jail = `SECURE_WARD` / `INPATIENT_LICENSED`. UCC **re-parented** to Emergency / `ED_STRETCHER`. OR=`OR_TABLE`, PACU=`PACU_BAY`, clinics/diagnostics = chair/procedure. Stable codes: `W3A`…`W5B`, `ICU-MAIN`, `ED-RESUS`, … |
| **DQ-13** | **Doc math / occupancy formula** | `06` previously called raw **243** “normalized”; occupancy used mixed `licensed_capacity` | **Applied here.** 243 = raw. Occupancy % = occupied **inpatient** beds ÷ **operational inpatient** capacity (HNWMS M1.2), not ÷ 515. |
| DQ-14 | **No position↔location map** | Org chart and CSV cannot be joined | **Open.** Required for RBAC/scheduling before P1. |
| DQ-18 | **No external license register** | 281/267 not reconciled to MOH/CBAHI bed license | **Open. Blocking for go-live.** |

---

## 4. Canonical cleaned taxonomy (what gets loaded)

Seed file: **`artifacts/normalized_department_unit.csv`**.

Columns: `unit_code, department, unit_group, unit_name, unit_type, care_setting, capacity_class, source_bed_count, bed_capacity, is_bedded, dq_flag`.

### 4.1 Departments (4) — unit counts after UCC re-parent

| department | units | INPATIENT_LICENSED | Other (not licensed inpatient) |
|---|---|---|---|
| EMERGENCY & ACUTE CARE | **6** | 0 | ED stretchers 118 + support |
| SURGICAL & PERIOPERATIVE SERVICES | **4** | 0 | OR 12 + PACU 8 + plaster 9 + support |
| CRITICAL CARE & INTENSIVE SERVICES | **3** | **99** | — |
| GENERAL & SPECIALTY SERVICES | **30** | **182** (156 wards + Jail 12 + ICU-EXT-2 14) | clinics/diagnostics/support |
| **Facility** | **43** | **281** (or **267** excl. DQ-1a) | remainder of 524 |

### 4.2 Controlled values

**care_setting:** `INPATIENT_WARD` · `CRITICAL_CARE` · `EMERGENCY` · `PERIOPERATIVE` · `AMBULATORY` · `DIAGNOSTIC` · `SUPPORT`

**unit_type:** `WARD` · `SECURE_WARD` · `ICU` · `HDU` · `LDR` · `ED` · `UCC` · `OR` · `PACU` · `CLINIC` · `DIAGNOSTIC` · `PROCEDURE` · `THERAPY` · `SUPPORT`

**capacity_class:** `INPATIENT_LICENSED` · `ED_STRETCHER` · `PACU_BAY` · `OR_TABLE` · `PROCEDURE_ROOM` · `AMBULATORY_CHAIR` · `SUPPORT`

**is_bedded:** `yes` only when a patient can be placed (inpatient bed, ED stretcher, PACU bay) — 19 units. ADT **licensed-bed** occupancy still uses `capacity_class=INPATIENT_LICENSED` only.

### 4.3 Headline figures (use these)

| Label | Value | Use for |
|---|---|---|
| Raw CSV Bed sum | 524 | Source traceability only |
| After DQ-9 mixed-class | 515 | History of admin reclass only |
| **Proposed licensed inpatient (incl. DQ-1a row)** | **281** | Upper bound until audit |
| **Proposed licensed inpatient (if DQ-1a merged)** | **267** | Default if physical audit finds no second ICU extension |
| ED stretchers | 118 | ED board, not MOH beds |
| Patient-placeable slots | 407 | Inpatient + ED + PACU |

### 4.4 Workforce hierarchy (from org chart) → positions

Unchanged; **not** derived from the CSV:

- **E1** Hospital Director · **E2** Medical Director/CMO, Director of Nursing, Operations Director, Quality Lead, IT/Health-Informatics, Pharmacy/Diagnostics, Patient & Corporate Services.
- **L1** Director of Nursing (`DON`) · **L2** Deputy/Assistant DON (`ADON`), Nursing Administration/Workforce Manager, Nursing Education Manager, Nursing Quality Manager, Nursing Informatics Manager · **L3** Nursing/Unit Manager · **L4** Charge Nurse · **L5** Team Leader/Senior Nurse · **L6** Staff Nurse · **L7** Nursing Assistant.
- Functional nursing lines: Nursing Operations (Inpatient, ICU/Critical, Emergency, OR, Pediatrics, Maternity/OB, Specialty) and Workforce Management map to `org_node` + RBAC scopes via a coverage map that still must be built (DQ-14).

Display-name clean-up in seed: `Fastrack` → `Fast-track`. Source CSV spelling is unchanged.

---

## 5. Sign-off required before go-live

1. **DQ-1/DQ-2** — definitive names & departments for ICU Extension, Plaster Unit, ED Navigator pairs (`07` + physical audit).
2. **DQ-4** — confirmation the 5 support areas are non-bedded.
3. **DQ-9** — confirmation `ED-ADMIN` (7) and `OR-ADMIN` (2) are non-assignable (already applied in seed).
4. **DQ-10 / licensed vs operational** — confirm `capacity_class` mapping with Licensing; occupancy uses operational **inpatient** beds.
5. **DQ-12** — confirm Jail as secure inpatient, UCC under Emergency, OR/PACU/clinics not licensed beds; confirm new `unit_code`s (`W3A`, `ICU-MAIN`, `ED-RESUS`, …).
6. **DQ-11** — confirm ED Maternal & Child is ED observation, not an obstetric ward double-count.
7. **Bed granularity** — capacity-mode vs bed-registry-mode; if registry, provision beds only for `INPATIENT_LICENSED` (+ optional ED/PACU pools) using `artifacts/physical_bed_audit_form.md`.
8. **DQ-18** — obtain the MOH/CBAHI **bed-license register** and reconcile 281/267 (not 515).
9. **DQ-14** — position ↔ unit coverage map from the org chart.
10. **Org scope** — full hospital org chart vs nursing line only for RBAC (recommend: both, nursing line detailed).
11. **Owners/RACI** sign-off per `01_implementation_plan.md` §9.

After sign-off, proceed to `03_configuration_checklist.md` Wave P0/P1. **Do not load this seed as a licensed-bed register until items 1, 4, 5, 8 are signed.**
