# Configuration Checklist — Org Structure, Departments & Bed Capacity

Use as the build/QA checklist alongside `01_implementation_plan.md`. Items are grouped by wave; mark **☐** when done. Every change is audited and versioned.

## A. Source reconciliation & master taxonomy (Wave P0)
- [ ] Archive original source files with immutable load IDs (`Department & Bed.csv`, `Hospital_Nursing_Organizational_Structure.md`).
- [ ] Confirm department vocabulary (4): Emergency & Acute Care · Surgical & Perioperative · Critical Care & Intensive · General & Specialty.
- [ ] Confirm unit count & **classed** totals against `artifacts/org_rollup.csv`: **43 units**; raw 524; INPATIENT_LICENSED **281** (or **267** excl. DQ-1a); ED_STRETCHER **118**; mixed-class 515 is history only (`06` DQ-10). Do not sign 515 as licensed beds.
- [ ] Adjudicate CSV anomalies from `06_source_reconciliation.md`:
  - `ICU-EXT` (Critical Care, 14) vs `ICU-EXT-2` (Gen & Spec, 14) — duplicate? two sites? split licensing?
  - `PLASTER` (Surgical, 9) vs `PLASTER-2` (Gen & Spec, 9).
  - `ED-NAV`(3) vs `ED-NAV-2`(5) — both classed SUPPORT/non-bedded; confirm merge.
  - Confirm DQ-12: Jail = secure inpatient; UCC re-parented to Emergency; OR/PACU/clinics not licensed beds.
  - Support/admin rows (5) have **no bed count** → confirm they are non-bedded locations, not missing data.
  - Embedded newline+tab inside the Endoscopy cell — confirm parsed correctly.
- [ ] Map org-chart positions to `position_code` + `position_level` (L1–L7 / E1–E2) with a sign-off table.
- [ ] **Bed granularity decision:** Capacity-mode vs Bed-registry-mode; if registry mode, record room-bay sizing and confirm with **physical count audit** before go-live.

## B. Org Directory & Location registry (Wave P1)
- [ ] Load facility, departments, unit_groups, nursing_units from `normalized_department_unit.csv` via loader; reconcile **by capacity_class** (INPATIENT_LICENSED 281/267, ED 118, 43 units, 4 departments). Record 524 and 515 only as source-history deltas.
- [ ] Unit codes unique & stable; load mapping unit↔department↔group↔care-setting.
- [ ] Load workforce positions + org nodes from org chart; wire reports-to (org_node parent).
- [ ] Configure controlled vocabularies (unit_type, care_setting, bed_class, bed_status) with no free-text drift.
- [ ] Publish registry to consumers (ADT, Scheduling, HNWMS, Payroll cost-centers).

## C. Bed registry provisioning (Wave P2)
- [ ] Provision room/bed records from `licensed_capacity` **only where `capacity_class=INPATIENT_LICENSED`** (optional separate ED-stretcher / PACU-bay pools). Do not provision ADT beds for OR/procedure/clinic/support.
- [ ] Validate `bed` count == `licensed_capacity` per inpatient unit; flag any mismatch.
- [ ] Set bed features/classes (ICU=telemetry/vent, isolation/neg-pressure units flagged).
- [ ] Physical room/bed audit: reconcile synthetic numbering to actual signage and unit bed counts — use `artifacts/physical_bed_audit_form.md`. This also resolves DQ-1/DQ-2 (duplicate vs real second site) per `07_adjudication_decision_records.md`.
- [ ] Bed lifecycle state machine live (READY/RESERVED/OCCUPIED/CLEANING/OUT_OF_SERVICE/BLOCKED) with state-log auditing.

## D. RBAC & scoping (Wave P1/P2)
- [ ] Create roles per §3 role catalogue; bind each grant to FACILITY/DEPARTMENT/UNIT scope.
- [ ] Charge Nurse scoped to own unit only; Unit Manager to own department/units; House Supervisor/DON facility-wide.
- [ ] Separate **bed control** permissions from **scheduling** permissions.
- [ ] Set up delegation & auto-escalation ladder (Charge→Manager→Deputy DON→DON).
- [ ] MFA on privileged roles; quarterly recertification scheduled.

## E. ADT + Bed workflows & surge (Wave P3)
- [ ] Configure ADT state machine + bed auto-assignment rules (gender/bed_class, isolation, telemetry/vent needs).
- [ ] Cleaning SLA (e.g., 45 min) & triggers to move bed CLEANING→READY.
- [ ] Capacity thresholds: amber (≥85%) / red (≥95%) occupancy; alert rules.
- [ ] Surge levels 1–4 + escalation ladder & notification routing configured.
- [ ] Integration events (HL7 ADT A01/A02/A03, FHIR Location/encounter) enabled & tested.

## F. Reporting / analytics (Wave P4)
- [ ] Enable occupancy %, turnover, available/blocked/cleaning/out-of-service metrics.
- [ ] Build dashboard set (Bed board, capacity heat-map, house supervisor, DON & Hospital Director rollups).
- [ ] Scheduled reports + alert subscriptions per role.

## G. Integration, migration & reconciliation cadence
- [ ] APIs published per `01_implementation_plan.md` §5.2.
- [ ] Scheduled reconciliations: daily census↔occupancy; weekly capacity↔licensing; monthly full audit (all signed).
- [ ] Consumer sync event-driven; conflict rule per field owner documented.

## H. Security & compliance (Wave P5)
- [ ] Immutable audit log on all registry/bed/assignment/access events.
- [ ] Row-level data segregation by facility/dept/unit; PII masking for non-clinical roles.
- [ ] Regulatory mapping documented (confirm governing body — e.g., CBAHI + MOH licensed-bed registry in Saudi Arabia, and any national data-protection law), and controls evidenced.
- [ ] Retention/residency/DR aligned to facility SLA; backups tested.
- [ ] Access recertification + penetration/review schedule.

## I. Go-live acceptance
- [ ] All test cases in `05_test_acceptance_criteria.md` pass.
- [ ] Signed-off taxonomy by DON + Licensing; UAT completed by super-users per department.
- [ ] Rollback & re-import plan tested; effective-dated history retained.
