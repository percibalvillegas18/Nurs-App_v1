# UI Placement Recommendations

Where each ingested element surfaces in the platform. Grouped by module screen. Designed to keep the **location/org tree** as a reusable navigation spine and keep **clinical census** visible without leaking PII to workforce screens.

## 1. Org Directory module
- **Org Tree panel** (left, expandable): Faculties → Departments → Unit Groups → Units. Rooted at hospital; supports both the nursing line and whole-hospital views with a toggle.
- **Department & Unit registry screen** (tab): table of the 43 units grouped by department; columns = unit code, name, unit_type, care_setting, licensed_capacity, is_bedded, owning group, status. Inline edit + effective-date history. Quick search by name/code.
- **Unit detail view**: attributes + tabs for Beds, Assignments (which managers/positions cover it), Capacity history, Occupancy trend, Reconciliation report link.
- **Org (workforce) structure view**: tree of org_node reporting lines (Hospital Director → DON → Deputy → Nursing Ops → Manager → Charge → Staff); toggles to the position level (L1–L7). Person/position assignments shown on each node.
- **Assignment manager**: match workforce positions to departments/units via scope picker (this is the bridge the org chart needs to reach the bed/unit tree).

## 2. ADT / Registration
- Admission form: **Department & Unit autocomplete** bound to the location registry (not free text) to preserve data integrity.
- **Bed availability picker** embedded in the admit/transfer dialog, filtered by unit and bed features (telemetry/vent/isolation) and gender/bed-class rules.
- Current-location banner on the patient/encounter header.

## 3. Bed / Resource Management
- **Bed board** (primary screen, one per unit, grid of beds color-coded by `bed_status`): READY (green) / RESERVED (amber) / OCCUPIED (blue) / CLEANING (striped) / OUT_OF_SERVICE (grey) / BLOCKED (red).
- **Filters:** unit, department, care setting, bed class/features, isolation.
- **Capacity & occupancy header** on each unit card: occupied/available/licensed, occupancy %, amber/red threshold chips.
- **Bed actions** (assign/reserve/release/mark cleaning/out-of-service/block) with required reason → audit.
- **Room & bed admin** screen for managing the auto-provisioned rooms/beds vs a manually uploaded bed-number list.

## 4. House Supervisor / Surge & Escalation
- **House board:** rollup of all units' occupancy + alerts; one-tap drill-down to any unit's bed board.
- **Surge console:** current surge level, threshold breach list, recommended decant/overflow actions, escalation ladder status and SLA timers, decision/override log.

## 5. Scheduling / Rostering & HNWMS (read context)
- Scheduling screens consume **unit + capacity** as the staffing frame: show required-vs-available nurses per unit driven by census/occupancy, without showing patient-identifiable data.
- Unit pickers across scheduling/roster are bound to the same location registry to stay consistent with ADT/Bed.

## 6. Workforce / HR modules
- Position/assignment pickers bound to org tree; department = cost-center mapping shown read-only.

## 7. Reporting / Analytics dashboards
- **Bed board & capacity** (per role, per scope), **Occupancy heat-map** (units × time), **Turnover**, **Reconciliation reports** (signed), and the **DON/Hospital Director** rollups per the org file's Management Dashboard structure (headcount, staffing gap, census, cost).
- Alert center listing amber/red breaches, prolonged cleaning, surge activations, reconciliation mismatches.

## 8. System / Admin
- **Registry administration** (location + org taxonomy), **Vocabulary/status** maintenance, **Integration monitor** (last sync, error queue), **Audit viewer** (filter by object/role/time/source), **Reconciliation runner**.
