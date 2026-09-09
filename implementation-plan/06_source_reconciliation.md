# Source Reconciliation & Cleaned Taxonomy

This document records the **data-quality analysis** of the two source files, the **canonical cleaned taxonomy** used for loading, and the **open questions that need sign-off** before go-live. It is the factual basis for `03_configuration_checklist.md` and `05_test_acceptance_criteria.md`.

> Source files: `Hospital_Nursing_Organizational_Structure.md` (whole-hospital + nursing org chart) and `Department & Bed.csv` (department/unit/bed).

---

## 1. Source inventory & structure

**`Department & Bed.csv`** — 3 columns: `DEPARTMENT, Nursing Unit, Bed`. **44 rows = header + 43 data rows.**

**`Hospital_Nursing_Organizational_Structure.md`** — structured Markdown containing:
- Nursing org chart (Director of Nursing → Deputy → Nursing Ops clinical areas → Nursing Administration/Workforce → Nursing Unit Management).
- Recommended management hierarchy **L1–L7** (DON → … → Nursing Assistant) and executive structure **E1–E2**.
- Expanded whole-hospital org chart (Hospital Director → Medical/CMO, DON, Operations/Admin, Quality, Pharmacy/Diagnostics, IT/Health Informatics, Patient & Corporate Services).
- Nursing reporting line, enterprise integration matrix, and management dashboard structure.

---

## 2. Reconciliation results (computed)

| Metric | Value | Source |
|---|---|---|
| Departments | **4** | CSV col 1 |
| Nursing units (bedded) | **38** | CSV col 2 |
| Support/admin locations (non-bedded, blank Bed) | **5** | CSV |
| **Total locations** | **43** | CSV |
| **Licensed bed capacity (grand total)** | **524** | sum of Bed col |
| Dept rollups | Emergency & Acute Care **113** · Surgical & Perioperative **31** · Critical Care & Intensive **99** · General & Specialty **281** | computed (see `org_rollup.csv`) |

**Care-setting / unit-group rollups** (normalized): top-level bedded service lines **243** (Emergency+Surgical+Critical), ACUTE GENERAL CARE **159**, SPECIALIZED & DIAGNOSTIC **122**, SUPPORT & ADMIN **0** bedded. Sum 243+159+122 = **524** ✓.

> **Raw-source vs operational-capacity reconciliation.** The table and rollups above report the **raw** `Department & Bed.csv` ("sum of Bed col" = 524, "38 bedded"). Two of those 38 rows are **Admin & Support** areas that carry a numeric "Bed" but are **not assignable patient beds** — see **DQ-9**. After adjudication the registry seed (`normalized_department_unit.csv`, `org_rollup.csv`) reflects **operational assignable capacity = 515 beds across 36 bedded + 7 non-bedded units**. The 9-bed difference (EDAD 7 + ORAD 2) is the adjudication delta and is preserved as raw-source history in this document.

---

## 3. Data-quality findings (must adjudicate — all blocking-ish)

| # | Finding | Detail | Recommended disposition |
|---|---|---|---|
| DQ-1 | **Near-duplicate unit names** | `ICU Extension` (Critical Care, 14) vs `ICU Extension (2nd Location)` (Gen & Spec, 14); `Plaster Unit` (Surgical, 9) vs `Plaster Unit (2nd Location)` (Gen & Spec, 9) | Confirm whether these are genuinely two physical sites or a duplicate row assigned to the wrong department. If two sites, keep both with distinct codes; if duplicate, correct the department. **Blocking** for clean loading. |
| DQ-2 | **Spelling inconsistency** | `ED Navigation` (3, Emergency) vs `ED Navigator (2nd Location)` (5, Gen & Spec) | Adjudicate intended name; align taxonomy. |
| DQ-3 | **Inconsistent group labels** | `SPECIALIZED & DIAGNOSTIC` and `DIAGNOSTIC & SPECIALTY` both appear as parenthetical group prefixes | Normalize both to a single controlled value (this plan uses `SPECIALIZED & DIAGNOSTIC`). |
| DQ-4 | **Support/admin rows have blank Bed** | 5 rows under "SUPPORT & ADMINISTRATIVE SERVICES - …" carry no bed count | Treat as **non-bedded locations** (`is_bedded=false`), NOT missing data. Requires confirmation that these truly have no beds. |
| DQ-5 | **Malformed cell** | Endoscopy row: `"(DIAGNOSTIC & SPECIALTY) \n\tEndoscopy Unit"` contains embedded newline+tab inside the quoted field | Parser must handle embedded separators (correctly does); normalizes to group `SPECIALIZED & DIAGNOSTIC`, unit `Endoscopy Unit`, capacity 5. |
| DQ-6 | **Leading whitespace** | Several rows have a leading space on DEPARTMENT (e.g. ` SURGICAL…`) | Strip; match by normalized key. |
| DQ-7 | **Grouping not uniform across departments** | Only `GENERAL & SPECIALTY SERVICES` rows carry parenthetical group prefixes; Emergency/Surgical/Critical rows are flat | Model top-level service lines as their own implicit group (care_setting BEDDED_SERVICE_LINE). Decide a consistent presentation. |
| DQ-8 | **Capacity is unit-level only** | No room/bed numbers exist in source | Decide Capacity-mode vs Bed-registry-mode; registry-mode numbering is synthetic and needs a **physical bed audit** (§ in checklist A / C). |
| DQ-9 | **Admin & Support rows carry a numeric "Bed" but are not assignable patient beds** | `ED Administration & Support` (Emergency) = 7 and `OR Administration & Support` (Surgical) = 2 appear in the 38 bedded rows, yet are staff/office support areas by name | **Reclassify as NON_BEDDED_SUPPORT** (`is_bedded=false`, capacity nil) — removes 9 from assignable capacity (515) and from bedded-unit count (36). **Applied** in the registry seed; confirm against the physical/office-space count during Wave P2 so licensed vs operational capacity is stated correctly. |

---

## 4. Canonical cleaned taxonomy (what gets loaded)

### 4.1 Departments (4) — operational assignable capacity
| department | department_type | assignable beds | source "Bed" total | delta |
|---|---|---|---|---|
| EMERGENCY & ACUTE CARE | BEDDED | **106** | 113 | −7 (EDAD) |
| SURGICAL & PERIOPERATIVE SERVICES | BEDDED | **29** | 31 | −2 (ORAD) |
| CRITICAL CARE & INTENSIVE SERVICES | BEDDED | **99** | 99 | 0 |
| GENERAL & SPECIALTY SERVICES | BEDDED | **281** | 281 | 0 |
| **Facility total** | | **515** | **524** | −9 |

### 4.2 Care settings / unit groups (controlled values)
`INPATIENT_WARD` (ACUTE GENERAL CARE) · `AMBULATORY_DIAGNOSTIC` (SPECIALIZED & DIAGNOSTIC) · `BEDDED_SERVICE_LINE` (top-level Emergency/Surgical/Critical areas) · `NON_BEDDED_SUPPORT` (SUPPORT & ADMINISTRATIVE).

### 4.3 Loaded unit list
The 43 locations and their normalized attributes are in **`artifacts/normalized_department_unit.csv`** (unit_code, department, unit_group, unit_name, care_setting, bed_capacity, is_bedded). This is the controlled source for the Org Directory + Bed registry seed; **36 are bedded, 7 are non-bedded** (the 5 SUPPORT & ADMINISTRATIVE rows plus reclassified `EDAD` ED Administration & Support and `ORAD` OR Administration & Support). Department/unit-group rollup totals are in **`artifacts/org_rollup.csv`**.

### 4.4 Workforce hierarchy (from org chart) → positions
Levels and example `position_code`s:
- **E1** Hospital Director · **E2** Medical Director/CMO, Director of Nursing, Operations Director, Quality Lead, IT/Health-Informatics, Pharmacy/Diagnostics, Patient & Corporate Services.
- **L1** Director of Nursing (`DON`) · **L2** Deputy/Assistant DON (`ADON`), Nursing Administration/Workforce Manager, Nursing Education Manager, Nursing Quality Manager, Nursing Informatics Manager · **L3** Nursing/Unit Manager · **L4** Charge Nurse · **L5** Team Leader/Senior Nurse · **L6** Staff Nurse · **L7** Nursing Assistant.
- Functional nursing lines: Nursing Operations (Inpatient, ICU/Critical, Emergency, OR, Pediatrics, Maternity/OB, Specialty) and Workforce Management (Manpower Planning → Workforce Analytics) map to org_node + RBAC scopes.

---

## 5. Sign-off required before go-live

1. **DQ-1/DQ-2** — definitive names & departments for the duplicate/spelling pairs (ICU Extension, Plaster Unit, ED Navigator).
2. **DQ-4** — confirmation the 5 support areas are non-bedded.
3. **DQ-9** — confirmation `ED Administration & Support` (7) and `OR Administration & Support` (2) are non-assignable support spaces (operational capacity = 515 vs source 524); align licensed vs operational capacity wording with the licensing body.
4. **Bed granularity** — capacity-mode vs bed-registry-mode; if registry, approve room-bay sizing & conduct physical audit.
4. **Org scope** — confirm whether to model the full hospital org chart or nursing line only for RBAC (recommend: both, nursing line detailed for clinical roles).
5. **Regulatory body** — confirm governing accreditation/licensing & bed-license registry (e.g., CBAHI/MOH) that the capacity numbers must reconcile to.
6. **Owners/RACI** sign-off per `01_implementation_plan.md` §9.

After sign-off, proceed to `03_configuration_checklist.md` Wave P0/P1.
