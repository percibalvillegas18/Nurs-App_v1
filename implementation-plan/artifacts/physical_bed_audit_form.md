# Physical Bed & Space Audit — Instrument

**Purpose:** Walk the facility and reconcile the **actual** assignable bed/room inventory against the location registry (`normalized_department_unit.csv`) and its `licensed_capacity`. This run closes DQ-8 (unit-level capacity, no room/bed detail) and definitively resolves DQ-1a/DQ-1b/DQ-2 (real second site vs duplicate) and DQ-4/DQ-9 (bedded vs non-bedded support spaces).

**When:** Wave P0/P2, before the bed registry is treated as authoritative. **Who:** Facilities/Licensing + Nursing Operations + IT (registry owner). Each unit gets one completed sheet.

---

## A. Per-unit audit sheet (fill one per unit)

### 1. Identification
| Field | Value |
|---|---|
| Unit name (registry) | |
| Unit code (registry) | e.g. `INTE`, `ICUE`, `ICUE_2`, `PLAS`, `PLAS_2`, `EDNA`, `EDNA_2`, `EDRE` |
| Department / group | |
| Registry `licensed_capacity` | |
| Registry `is_bedded` | yes / no |

### 2. Physical confirmation
| Question | Answer | Notes |
|---|---|---|
| Does a physical area with this exact name/signage exist? | Yes / No | If No → likely a duplicate row (see DQ disposition) |
| Is it a **separate physical footprint** from any other unit here? | Yes / No / N/A | Separate entrance/floor/zone? |
| How many **actual beds** are on site (counted)? | number | |
| How many are **licensed** (per license register)? | number | |
| How many are **operational/assignable** today? | number | |
| Are any beds **out-of-service / non-licensed**? | count + list | isolation, maintenance, storage |
| Is this a **clinical bedded area** or a support/office/room? | Bedded / Non-bedded | Non-bedded → office, staff room, waiting, procedure room without beds |
| If the name says "(2nd Location)": is this a real second site or the same as the primary? | Real second site / Same as primary (duplicate) | Core of DQ-1a/1b/DQ-2 |

### 3. Room inventory (capture one line per room; use extra sheets as needed)
| Room # | Room type (private/shared/bay/isolation) | No. of beds | Features (telemetry/vent/neg-pressure) | Assignable? |
|---|---|---|---|---|
| e.g. 3A-01 | shared | 2 | telemetry | yes |
| | | | | |
| | | | | |
**Room/bed count total (this unit):** ______

### 4. Reconciliation vs registry
| Metric | Registry | Physical | Delta |
|---|---|---|---|
| Bedded unit count | | | |
| Total beds | | | |
| Assignable beds | | | |
> Any delta → update the registry + record as a reconciliation finding. Deltas here settle whether "2nd Location" items are duplicates (physical = none / same as primary) or real.

### 5. Photographs / floor-plan reference
| Ref | Description |
|---|---|
| Floor plan no. | |
| Photo / sheet refs | |

### 6. Completed by
Auditor name/role · Date · Unit owner confirmation · Licensing confirmation

---

## B. Global audit checklist (run across all 36 bedded + 7 non-bedded registry units)
- [ ] Confirm each of the 7 non-bedded units has no assignable beds (DQ-4/DQ-9; incl. `EDAD`, `ORAD`, and the 5 SUPPORT & ADMINISTRATIVE rows).
- [ ] Confirm `ED Navigation` (`EDNA`) bedded-vs-non-bedded status (DQ-9 follow-on).
- [ ] Resolve each flagged pair: `ICUE` vs `ICUE_2`, `PLAS` vs `PLAS_2`, `EDNA` vs `EDNA_2` (DQ-1/DQ-2) via §A.2.
- [ ] Sum of physically counted assignable beds across all units reconciles to the registry total (target **515** assignable; source 524) — record any delta and its cause.
- [ ] Record every delta as a reconciliation finding; update `normalized_department_unit.csv` + `org_rollup.csv` only after sign-off.
- [ ] Approvals: Nursing Operations (ops), Facilities/Licensing (license count), DON. Registry applied by IT.

> Template rows for one-off use: copy §A per unit. `06_source_reconciliation.md` §5 lists DQ-9, bed-granularity and physical-audit sign-offs that this instrument satisfies.
