# Physical bed audit — desk run (not a floor walk)

**When:** 2026-09-09 · **Who:** Org Directory loader (IT)  
**What this is:** Pre-fill of `physical_bed_audit_form.md` from the classed registry.  
**What this is not:** A physical count. Every unit is `walk_status = NOT_WALKED`. Floor-plan / license-register fields are blank on purpose.

Take `physical_bed_audit_unit_sheets.csv` onto the floor (one row = one sheet). Sign `08_signoff_don_licensing.md` before treating counts as authoritative.

## Desk reconciliation (registry only)

| Check | Result |
|---|---|
| Units loaded | **43** |
| `source_bed_count` sum | **524** (matches raw CSV) |
| INPATIENT_LICENSED | **281** (includes `ICU-EXT-2` 14, DQ-1a pending) |
| If DQ-1a merged | 267 |
| ED_STRETCHER | **118** (UCC under Emergency) |
| Physical beds counted | **0 — not walked** |
| MOH/CBAHI license total | **blank (DQ-18)** |

## Blocking until the walk + sign-off

1. `ICU-EXT-2` / `PLASTER-2` / `ED-NAV-2` — real second site vs duplicate (`07`).
2. License register total vs 267 or 281.
3. Confirm Jail (secure inpatient) and UCC (ED family) on the floor.
4. Do **not** provision P2 `bed` rows from 515/524.

## Desk recommendations (not applied as merges)

| Unit | Recommendation |
|---|---|
| ICU-EXT-2 | PROPOSE_MERGE (keep in seed until signed) |
| PLASTER-2 | PROPOSE_MERGE |
| ED-NAV / ED-NAV-2 | KEEP_NON_BEDDED |
| All others | Count per `capacity_class` on the walk |

Instrument: `physical_bed_audit_form.md`. Sheets: `physical_bed_audit_unit_sheets.csv`.
