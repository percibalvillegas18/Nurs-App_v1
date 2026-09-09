# Open Adjudications — Decision Records (DQ-1, DQ-2) & Physical Bed Audit

**Status:** Proposed defaults, **awaiting facility sign-off** (DON + Licensing). Applies to the raw-source items from `06_source_reconciliation.md`. Do not treat the "proposed disposition" as loaded until confirmed.

---

## 1. Why these can't be auto-resolved (honest scope)
The source file is internally ambiguous. Whether "ICU Extension (2nd Location)" is a real second site or a duplicate row, and whether its 14 "beds" are real assignable beds, is knowable only from the **physical facility / floor plan / bed-license register**. This document (a) records the strongest available signal from the data, (b) proposes a recommended default with an explicit decision, and (c) provides the physical-audit instrument (`artifacts/physical_bed_audit_form.md`) whose results settle each item. A facility owner confirms each in minutes.

---

## 2. The pattern the data shows

The three rows tagged **(2nd Location)** all appear under **GENERAL & SPECIALTY SERVICES**, in its diagnostic/specialty group — and each has a **bed count identical to a unit already recorded** in its clinically-correct department:

| Item (this row) | This row's dept/group | Bed | Matched unit | Matched dept/group | Bed |
|---|---|---|---|---|---|
| ICU Extension (2nd Location) | Gen & Spec · DIAGNOSTIC & SPECIALTY | 14 | ICU Extension | Critical Care & Intensive | 14 |
| Plaster Unit (2nd Location) | Gen & Spec · SPECIALIZED & DIAGNOSTIC | 9 | Plaster Unit | Surgical & Perioperative | 9 |
| ED Navigator (2nd Location) | Gen & Spec · DIAGNOSTIC & SPECIALTY | 5 | ED Navigation | Emergency & Acute Care | 3 |

**Two independent signals:**
1. **Identical bed counts** (ICU 14=14, Plaster 9=9) — a genuine "second site" having exactly the same licensed capacity as the primary is possible but noteworthy; more consistent with a **duplicated/mis-entered row**.
2. **Implausible grouping** — an ICU extension and an OR plaster suite are **not** "Diagnostic & Specialty" units of General & Specialty. Even if they are real second sites, their parent group is wrong (they belong to Critical Care / Surgical). The row's *care_setting* is therefore suspect regardless of the duplicate question.

**ED Navigation (3) vs ED Navigator (2nd Location) (5)** differs in both name and count, so it is **not** an identical duplicate — it is a spelling-variant pair with a count discrepancy.

---

## 3. Proposed dispositions (per item)

For each, the deciding question is a physical one: **is there a real, separately-licensed second location with assignable beds on site?**

### DQ-1a — ICU Extension (2nd Location)
| Decision | When to choose | Consequence |
|---|---|---|
| **MERGE as duplicate (default)** | No separate ICU-extension site/license exists; the 14 is a repeat of the Critical Care ICU Extension | Remove `ICUE_2` from registry; **no bed-count change** (14 already counted once under Critical Care); Gen&Spec drops by one unit row (→42 units), Surgical/Critical unchanged. |
| **KEEP as second site, re-parent** | A second physical ICU-extension location exists with 14 assignable beds | Move `ICUE_2` under **Critical Care & Intensive** (not Gen&Spec/Diagnostic); group/care_setting corrected; unit count unchanged (43). |
| **KEEP but reclassify non-bedded** | The "ICU Extension (2nd Location)" is actually a monitoring/office space, not beds | Set `ICUE_2` non-bedded; Gen&Spec assignable drops 14 → affects dept total; reassess. |

### DQ-1b — Plaster Unit (2nd Location)
| Decision | When to choose | Consequence |
|---|---|---|
| **MERGE as duplicate (default)** | No separate plaster-suite site/license | Remove `PLAS_2`; **no bed-count change** (9 already under Surgical). |
| **KEEP as second site, re-parent** | Real second plaster location | Re-parent `PLAS_2` under **Surgical & Perioperative**, correct group. |
| **Reclassify non-bedded** | It is an outpatient room, not 9 beds | Reassess Gen&Spec assignable. |

### DQ-2 — ED Navigation vs ED Navigator (2nd Location)
| Decision | When to choose | Consequence |
|---|---|---|
| **Rename to a single canonical unit** | They are the same function (ED patient-navigation) | Keep **one** unit; reconcile the name (Navigation vs Navigator) and the count discrepancy (3 vs 5) against physical reality — one of the two figures is likely the true bed/observation count. |
| **Keep two distinct units** | Genuinely two ED navigation/observation areas | Fix names to canonical forms; keep both counts. |
| **Reclassify as non-bedded** | Navigation is a coordination role, not beds | Remove from bedded registry (likely — navigation staff are not typically bedded). |

> **DQ-9 follow-on (add to audit):** `ED Navigation` (3) and `ED Administration & Support` (7, already reclassified) are functional/support areas. Confirm whether `ED Navigation` is bedded (observation bays) or non-bedded in the same audit pass.

---

## 4. Decision Record (sign-off form) — one per item
| Field | Value |
|---|---|
| Item code | DQ-1a / DQ-1b / DQ-2 (circle) |
| Deciding question answered | Is there a real second physical location with assignable beds? Yes / No / Different (non-bedded) |
| Chosen disposition | Merge / Keep+re-parent / Keep+reclassify non-bedded |
| Evidence (physical audit result / floor plan / license no.) | |
| Bed-count impact | +0 / +N / −N (state) |
| Approver (DON) | signature + date |
| Approver (Licensing) | signature + date |
| Applied in registry by | date |

---

## 5. How the physical audit closes these
Run `artifacts/physical_bed_audit_form.md` for each flagged unit. The audit records actual rooms/beds on site. A **real second site** shows a separate physical footprint and its own bed inventory; a **duplicate row** shows no footprint (only the one original ICU/plaster location exists). This yields a definitive disposition for DQ-1/DQ-2, and separately validates every bedded unit's count (DQ-8) and flags admin/support spaces (DQ-4/DQ-9). See `03_configuration_checklist.md` item C (physical room/bed audit) and §4/§5 in `06`.
