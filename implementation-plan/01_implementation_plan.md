# Organizational Structure, Department Registry & Bed-Capacity Ingestion
## Implementation-Ready Plan for HIS / Nursing-Workforce Platform

**Version:** 1.0 · **Date:** 2026-09-09
**Author:** Hospital IT Systems Architecture
**Scope:** Ingest and operationalize two authoritative inputs:
1. `Hospital_Nursing_Organizational_Structure.md` — nursing + whole-hospital org hierarchy and reporting lines.
2. `Department & Bed.csv` — department registry with per-unit bed capacity.

These feed **Org Directory, ADT/MPI, Bed/Resource Management, Scheduling/Rostering, and HR/Payroll**, and must remain aligned with the existing **HNWMS** staff-master, scheduling, and analytics modules already specced in this repository.

> **Companion artifacts (same folder):**
> `02_erd_data_model.md` (ERD + entity/attribute spec + DDL), `03_configuration_checklist.md`, `04_ui_placement_recommendations.md`, `05_test_acceptance_criteria.md`, `06_source_reconciliation.md` (data-quality findings & cleaned taxonomy), `artifacts/normalized_department_unit.csv`, `artifacts/org_rollup.csv`, `artifacts/ddl_schema.sql`.

---

## 0. Executive Summary & Priority Ordering

The two inputs describe **two distinct but linked dimensions** of the same enterprise, and treating them as one flat file is the #1 source of downstream rework:

- **The organizational chart** is a **workforce / accountability taxonomy** (positions and reporting lines: Hospital Director → DON → Deputy → Nursing Ops → Unit Manager → Charge → Staff).
- **The Department & Bed file** is a **physical service / location taxonomy** (facility → department → service line group → nursing unit → bed), carrying **licensed/capacity bed counts**.

The bridge between them is an **assignment/coverage relation**: staffing positions (workforce side) are granted scope over care locations (location side) — e.g. a *Unit Manager (workforce position)* owns the *"Ward 3A" location*. Bed *capacity* is a property of the **unit**, and individual **beds** are provisioned from that capacity for ADT assignment.

### Priority ordering (build in this sequence)

| # | Wave | Outcome | Blocks |
|---|------|---------|--------|
| P0 | **Source reconciliation & canonical taxonomy** | Cleaned, validated, versioned master lists (departments, units, groups, capacity, workforce positions). Data-quality defects resolved *before* any code or loading. | everything |
| P1 | **Org Directory & Location registry** | Org Directory (locations + workforce nodes), RBAC foundation, controlled vocabularies, `unit` ↔ `department` ↔ `position` links. | RBAC, all downstream |
| P2 | **Bed registry provisioning** | From capacity counts → physical room/bed registry; bed lifecycle state machine. | ADT, Bed mgmt |
| P3 | **ADT + Bed assignment/release + surge** | Admission/transfer/discharge, auto bed assignment, escalation/surge protocols. | Scheduling staffing feeds |
| P4 | **Cross-module integration & census** | HL7/FHIR/API sync, census & occupancy, reporting/alerts. | Scheduling, analytics |
| P5 | **Hardening & governance** | Audit, data segregation, role reviews, regulatory mapping, reconciliation cadence. | all |

**Source-of-record ownership (who owns each element):**

| Element | System of Record | Our registry role |
|---|---|---|
| Employee/staff identity | HNWMS Staff Nurse Master Data / HR | consume |
| Workforce position & reporting line | HR/Org chart owner (this initiative) | Org Directory |
| Physical locations (facility/dept/unit/room/bed) | Facility/ADT location registry (this initiative) | **system of record** |
| Licensed bed capacity | Licensing authority + MOH/CBAHI | store as `licensed_capacity` |
| Patient/encounter + current location | EMR/ADT | consume via census |

---

## 1. Data Model

Full ERD in `02_erd_data_model.md`. Summary here. Three domains:

### 1.1 Location / operational domain (registry = our source of truth)
- **facility** — the hospital (top node of physical tree). `facility_id PK`, name, region, mrn_prefix, licensor, status.
- **department** — the 4 service departments in the CSV (*Emergency & Acute Care, Surgical & Perioperative, Critical Care & Intensive, General & Specialty*). `department_id PK`, `department_code UK`, facility FK, name, `department_type` (BEDDED / NON_BEDDED).
- **unit_group** (a.k.a. *service line / care setting* node) — the parenthetical prefixes in the CSV (`ACUTE GENERAL CARE`, `SPECIALIZED & DIAGNOSTIC`, `SUPPORT & ADMINISTRATIVE`) and, at the top three service lines, the department itself acts as the group. `unit_group_id PK`, department FK, name, `care_setting` (INPATIENT_WARD / AMBULATORY_DIAGNOSTIC / BEDDED_SERVICE_LINE / NON_BEDDED_SUPPORT).
- **nursing_unit** (a.k.a. ward / care area) — the 43 care areas in the CSV. `unit_id PK`, `unit_code UK`, department FK, unit_group FK, `unit_name`, `care_setting`, `unit_type` (Ward/ICU/ED/OR/PACU/Clinic/Support…), **`licensed_capacity`** (the CSV "Bed"), `is_bedded` flag. **Assignable-bed target:** the CSV's 38 bed-count rows include 2 Admin & Support areas (`EDAD`, `ORAD`) reclassified to non-bedded → **36 bedded + 7 non-bedded** (see `06` DQ-9).
- **room** — grouping level inside a unit. `room_id PK`, unit FK, room_number, room_type (private/shared/bay), isolation capability.
- **bed** — physical assignable resource. `bed_id PK`, unit FK, room FK, bed_number, bed_class, care_features (telemetry/vent/neg-pressure), `is_licensed`, `is_operative`, lifecycle `bed_status`.

**Bed granularity decision (senior note).** The CSV reports **unit-level capacity counts only** (source total 524; **operational assignable = 515** after DQ-9 — see `06`). There is **no room/bed-number detail**. Therefore the physical `bed`/`room` rows are **auto-provisioned from `licensed_capacity`** (i.e., the 36 bedded units = 515 beds) using configurable room-bay sizing, and the resulting room/bed numbering is a **stated assumption** that MUST be reconciled in Wave P0/P2 with a physical count (see §7 Reconciliation). Two supported loading modes:
- **Capacity mode:** store `licensed_capacity` on the unit only (best if bed-management is unit/ward-occupancy based).
- **Bed-registry mode (recommended for ADT room/bed):** generate one `bed` row per capacity unit, grouped into `room` records, enabling individual bed assignment and state. Provide `room_size` default and per-unit override.

### 1.2 Workforce / accountability domain (consumed from HR + HNWMS)
- **person** (staff master; owned by HR/HNWMS) — `person_id`, name, license, dept-of-record.
- **workforce_position** (role definition from org chart) — `position_id PK`, `position_code` (DON, ADON, NURSE_MANAGER, CHARGE_NURSE…), title, `position_level` (L1–L7), org node FK, functional area.
- **org_node** — generic node of the reporting tree (Director of Nursing, Nursing Operations, ICU…) enabling `parent_org_node_id` → *reports-to* hierarchy. Flexible for both hospital and nursing org charts.
- **assignment** — person holding a position, **scoped** to a department/unit, effective-dated: `assignment_id`, person FK, position FK, **scope_type** (FACILITY/DEPARTMENT/UNIT), **scope_id**, effective_from, effective_to, status. This is the *bridge table* to the location domain.

### 1.3 Encounter / ADT domain (owned by EMR, mirrored/consumed)
- **encounter**, **patient** (MPI) — consumed, not duplicated.
- **encounter_location / bed_occupancy** — current department/unit/room/bed + timestamps; event-sourced from ADT.
- **bed_occupancy_log** — historical bed states.

**Key relationships:** facility 1—N department; department 1—N unit_group; unit_group 1—N nursing_unit; nursing_unit 1—N room 1—N bed; assignment (position) M—N nursing_unit via scope. Encounter references a bed (current) and a unit (owning). Bed status changes drive occupancy.

### 1.4 Primary keys & natural keys
- All PKs surrogate (bigint/guid). Natural keys enforced unique: `facility_code`, `department_code`, `unit_code`, `bed_number+room+unit`, `position_code`. Never delete — soft-delete + effective-dating so history and audit survive.

---

## 2. System Mapping (element → module/table)

| Source element | Org Directory | ADT / MPI | Bed / Resource Mgmt | Scheduling / Rostering | HR / Payroll | HNWMS |
|---|---|---|---|---|---|---|
| Hospital Director / exec tree | org_node (E1–E2) | — | — | — | position hierarchy | governance viewer |
| Director of Nursing & reporting line | org_node + workforce_position (L1–L7) | — | unit oversight role | coverage approver | position/job | dashboard owner |
| Nursing Operations clinical areas | unit_group / department | admit location mapping | owning department | demand driver | cost center | staffing demand source |
| Nursing Admin / Workforce Mgmt | org_node | — | — | scheduling config | HR functions | modules (recruitment→analytics) |
| **Department** (4) | department | admission dept | owning dept | unit → dept grouping | cost center | unit taxonomy |
| **Unit / Ward** (43: 36 bedded + 7 non-bedded) | nursing_unit | ADT assign unit | bed pool owner | staffing schedule unit | pay location | roster unit |
| **Bed capacity** (515 assignable; 524 raw source) | unit `licensed_capacity` | availability source | bed registry (room/bed) | capacity for staffing ratios | — | census input to staffing |
| Nursing Manager / Charge / Team / Staff | workforce_position + assignment | scope approvals | bed release authority | shift roles | pay grade | roles/groups |

**Integration principle:** One **location master** (Org Directory) publishes unit codes that **ADT, Bed Mgmt, Scheduling, Payroll, and HNWMS all consume** — never re-keyed. Census flows EMR→Bed Mgmt→(staffing demand)→HNWMS.

---

## 3. RBAC: Roles, Supervisory Hierarchy & Department-based Access

**Model = RBAC (role→permission) + data scoping (role grant bound to dept/unit) + org hierarchy (for delegation/escalation).** Three tables: `role`, `role_grant(user_or_position, scope_facility/dept/unit)`, `permission`.

### 3.1 Role catalogue (mapped from org chart)

| Role | Level | Modules/granted | Data scope | Permissions (highlights) |
|---|---|---|---|---|
| System / Integration Admin | — | all | all | config, taxonomy, integration, audit view |
| Org Directory Admin | — | Org Directory | all | CRUD facility/dept/unit, vocab, mappings |
| ADT / Registration Clerk | frontline | ADT/MPI | assigned dept(s)/unit(s) | register, admit, bed *request*, discharge initiate |
| Bed Coordinator / Patient Placement | P3 | Bed Mgmt | all or region | assign/release bed, transfer, override with approval |
| House Supervisor / Nursing Operations | L2/L3 | Bed + ADT + coverage | all units | surge & escalation authority, cross-dept reassignment |
| Charge Nurse | L4 | ADT, Bed, Staffing | **own unit** | unit bed readiness, per-bed state, staff assignments |
| Unit / Nursing Manager | L3 | all unit-level | own dept/units | approve transfers, capacity config, escalate |
| Deputy / Assistant DON | L2 | read-across + approvals | all nursing | dept-level review, escalation |
| Director of Nursing | L1 | analytics | all | dashboards, approvals, staffing governance |
| Workforce Mgmt / Scheduler | — | Scheduling/HNWMS | by dept | roster, leave, must NOT move beds without Bed role |
| HR / Payroll | — | HR/Payroll | by cost center | salary; **read-only** on locations |
| Regulatory / Audit | — | read-only audit | all | log review, compliance |

**Hard rule:** Clinical *bed control* (assign/release/override) is isolated from *staff scheduling*. A scheduler cannot change a bed; a charge nurse cannot change another unit's beds.

### 3.2 Supervisory hierarchy & delegation
- Derived from **workforce_position level (L1–L7)** + **org_node reports-to** + **assignment scope**.
- **Delegation** for approvals: out-of-office auto-escalates up the reporting line (Charge→Unit Manager→Deputy DON→DON), limited by level and scope.
- **Least privilege** default; managers get their dept/units; DON/admin get facility.

### 3.3 Department-based access
- Every grant is **bound to a scope**. A Charge Nurse grant scoped to `unit=Ward 4A` cannot read `ICU`.
- Non-bedded/support areas (no beds) grant only non-clinical roles.
- Access decision = `permission ⊕ role grant scope ∋ resource dept/unit ⊕ org-line` (row-level security / column masks as needed).

---

## 4. Workflows

### 4.1 Admission / Transfer / Discharge (ADT) with bed integration
State machine per encounter location: **Requested → Assigned → In-Bed → In-Transfer → Discharged** (+ **On-Hold/Cleaning → Ready** for beds).

**Admission:** register → admit with desired dept/unit → **auto bed-assign** (rules: gender/bed_class, isolation needs, telemetry/vent features, unit type) → ADT A01 (admit) → confirm In-Bed → occupancy +1.
**Transfer:** clinical order → Bed Coordinator selects target unit/bed (respecting feature/isolation) → ADT A02 → source bed → Cleaning; target bed → Occupied → census transfer event.
**Discharge:** order → ADT A03 → bed → Cleaning → Ready → occupancy −1 → discharge revenue/records trigger.

Each step writes an audit entry and, where integration is live, emits the HL7 ADT / FHIR encounter-location message.

### 4.2 Bed assignment / release
- **Bed registry** states: `Ready → Reserved → Occupied → Cleaning → Out-of-Service` (+ `Blocked` for infection/isolation).
- Assignment: best-fit matching (clinical need vs bed features), then reserve → patient arrival → occupied.
- Release: discharge/transfer → cleaning (with SLA, e.g., target 45 min) → ready.
- **Out-of-service / block** management for maintenance & infection control; reconciles vs `licensed_capacity`.
- Full state audit; no orphan bed states; every change attributable.

### 4.3 Escalation & surge protocols
- **Thresholds** (configurable, see §6) on the unit/department/facility.
- **Surge levels:** Level 1 (unit alert) → Level 2 (departmental load-balancing, elective deferral) → Level 3 (facility surge, open overflow/decant beds) → Level 4 (regional/crisis).
- **Escalation ladder:** Charge Nurse → Unit Manager → House Supervisor / Nursing Operations → Deputy DON → DON → Hospital Director. Each step is a role + scope + SLA; auto-notify; log every decision (who, when, why, override).

---

## 5. Integration & Migration

### 5.1 Source formats & import pipeline
| Input | Format | Import approach |
|---|---|---|
| Departments, units, capacity | CSV (`Department & Bed.csv`) | Parser → **staging** → validation → canonical load |
| Org hierarchy | Markdown (structured text/tree + tables) | Semi-automated parse → **manual QA review** → org_node/position load |

**Loader:** Extract → stage (raw, immutable) → normalize/clean (see `06_source_reconciliation.md`) → validate → match/merge against existing registry → apply with effective date → audit log. **Never** destructive overwrite; load is **merge/versioned**.

### 5.2 API endpoints (recommended surface, POST/GET/PATCH)
- Org Directory: `/departments`, `/units`, `/unit-groups`, `/facilities`, `/positions`, `/org-nodes`, `/assignments`
- Bed/Resource: `/units/{id}/beds`, `/beds/{id}/status`, `/beds/available?dept=`, `/units/{id}/capacity`
- Census/Occupancy: `/census?facility&dept&unit`, `/occupancy`, `/beds/available`
- Registry of standard: **FHIR R4** `Organization`, `Location` (physical units/rooms/beds), `HealthcareService`; **HL7 v2 ADT** (A01/A02/A03/A04) & bed/occupancy; REST for internal modules.

### 5.3 Synchronization strategy
- **Location/org registry:** system of record here; **event-driven publish** (CDC / webhook) to consumers (ADT, Scheduling, HNWMS, Payroll cost-center).
- **Census:** EMR is authoritative; **event + scheduled** (near-real-time, e.g. 5-min) pull into Bed Mgmt for occupancy & demand.
- **Staff:** pull from HR/HNWMS master; positions scope from Org Directory.
- **Conflict rule:** last-writer per field by designated owner; reconciliations scheduled (daily capacity, monthly full).

### 5.4 Validation rules (examples)
- Department name non-empty & unique; known vocabulary of 4 depts.
- Unit code unique & non-null; unit belongs to exactly one department.
- `licensed_capacity` integer ≥ 0; ≤ facility licensed total; bed count matches capacity (bed-registry mode).
- Care-setting must be consistent with bedded/non-bedded (support/admin → no beds).
- Position level L1–L7; assignment scope exists in location registry; no orphan scopes.
- Duplicate/near-duplicate names (e.g., "ICU Extension" vs "ICU Extension (2nd Location)") flagged for adjudication — dispositions & decision records in `07_adjudication_decision_records.md`, confirmed by the physical audit.

### 5.5 Reconciliation
- **Migration-time:** count & total checks vs source (raw 524 beds; 4 depts; 38 bed-count rows + 5 blank-bed support rows; 43 units) and vs **operational target** (515 assignable; 36 bedded + 7 non-bedded). The 9-bed delta is the `06` DQ-9 adjudication (EDAD 7 + ORAD 2). Compare staged vs loaded vs source and report exact deltas with the adjudication delta separately documented.
- **Operating-time:** daily *census vs bed-registry occupancy*; weekly *capacity config vs licensing submission*; monthly *full audit vs source of truth*. Every run produces a signed reconciliation report (see P0/P5).
- **Physical count audit** at Wave P2 to validate the auto-provisioned room/bed numbering assumption (see `artifacts/physical_bed_audit_form.md`); the same run settles the DQ-1/DQ-2 duplicate-vs-real-site adjudications (`07_adjudication_decision_records.md`).

### 5.6 Test cases
Full table in `05_test_acceptance_criteria.md`; includes CSV with 39/32/32/3/7 rows, ICU Extension duplicate ambiguity, embedded-newline field parsing, blank-bed support rows, orphan unit, boundary capacity 0, negative, non-numeric.

---

## 6. Reporting & Alerts

- **Occupancy %** = current occupied beds ÷ `licensed_capacity` (unit/dept/facility rollups).
- **Turnover** = discharges + transfers-out per period (and bed-turnover per unit).
- **Available / blocked / cleaning / out-of-service** bed counts with dwell times.
- **Capacity thresholds:** configurable amber (e.g. ≥85%) and red (≥95%) occupancy; red-lines clean/discharge/blocked counts; triggers alerts + escalation (§4.3).
- **KPIs:** occupancy, availability, average LOS per unit, cleaning turnaround, denied-admission/divert minutes, time-to-bed-assign, surge activations.
- **Dashboards:** Org Directory overview, Bed board (live grid per unit), Occupancy & capacity heat-map, Turnover, House Supervisor board, DON & Hospital Director rollups (aligned with the dashboards already in the org file).
- **Alerts:** breach of amber/red threshold; extended cleaning; out-of-service spikes; surge auto-escalation; reconciliation mismatches.

---

## 7. Security & Compliance

- **Audit logs:** immutable, append-only record of every registry/bed/assignment change — who, what, when (UTC), before/after, reason, source (UI/API), scope. Cover CRUD + access attempts + exports.
- **Data segregation:** facility/dept/unit row-level security enforced by scope; MRN/PII masked for non-clinical roles; patient info never on workforce-side screens beyond census counts.
- **Access controls:** RBAC + scoping (§3), MFA for privileged roles, quarterly access recertification, session & least privilege defaults.
- **Regulatory context (confirm governing bodies):** align to the hospital's accreditation & licensing — e.g., in Saudi Arabia **CBAHI** standards, **MOH facility licensing / bed-license** registry, and national health-data protection (PDPL); plus international HIPAA/JCI analogues where applicable. Licensed-bed counts and org/unit taxonomy are auditable compliance artifacts.
- **Retention & residency:** data residency, retention schedules for audit/records, encrypted at rest & in transit, backup/DR aligned to facility SLA.

---

## 8. Deliverables

| Deliverable | File |
|---|---|
| ERD + data model + DDL | `02_erd_data_model.md`, `artifacts/ddl_schema.sql` |
| Configuration checklist | `03_configuration_checklist.md` |
| UI placement recommendations | `04_ui_placement_recommendations.md` |
| Test & acceptance criteria | `05_test_acceptance_criteria.md` |
| Source reconciliation & cleaned taxonomy | `06_source_reconciliation.md`, `artifacts/normalized_department_unit.csv`, `artifacts/org_rollup.csv` |
| This implementation plan | `01_implementation_plan.md` |

---

## 9. Responsibility Assignment (RACI – summary)

| Activity | Owner | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|---|
| Taxonomy & location registry | Org Directory Admin | IT/Informatics | DON / CIO | Nursing Ops | all |
| Bed capacity/license | Facility/Licensing | Org Directory + Bed mgr | Licensing authority lead | CBAHI/MOH liaison | DON |
| Org hierarchy & positions | HR | HR/Org Chart owner | HR Director | DON | Workforce |
| ADT/bed workflows | Nursing Ops | Bed Coord / IT | Deputy DON | EMR vendor | Managers |
| Staffing/scheduling integration | Workforce | HNWMS/Scheduling | Workforce Mgr | Charge/Managers | Finance |
| Security/audit/compliance | IT security | InfoSec | CIO | Compliance | all |
| Change management & UAT | Project Mgr | Super-users per dept | Sponsor (DON/CIO) | Nursing Managers | all |

**Recommended next action:** start **Wave P0** — execute `06_source_reconciliation.md`, get the org/department/bed taxonomy signed off by DON + Licensing, and provision the Org Directory + Bed registry schema from `ddl_schema.sql`.
