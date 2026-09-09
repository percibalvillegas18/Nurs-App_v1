# P0 Sign-off — DON + Licensing (+ HR/Legal)

**Hospital:** AIGH — Nursing / Facility Licensing  
**Date:** _______________  
**Purpose:** Approve the classed unit registry and labor-hour interpretation **before** any production load or Wave P1 build.  
**Sources:** `06_source_reconciliation.md` · `07_adjudication_decision_records.md` · `artifacts/normalized_department_unit.csv` · `artifacts/physical_bed_audit_form.md` · `compliance-guardrails/artifacts/compliance_rule_catalog.csv`

**Do not quote 524 or 515 as licensed beds.** Occupancy = occupied inpatient ÷ operational inpatient.

| Figure | Value | Use |
|---|---|---|
| Locations / departments | 43 / 4 | Registry size |
| Raw CSV `Bed` sum | 524 | Source history only |
| Mixed-class after DQ-9 | 515 | History only (admin 7+2 removed) |
| **Licensed inpatient (incl. `ICU-EXT-2`)** | **281** | Upper bound until audit |
| **Licensed inpatient (if `ICU-EXT-2` merged)** | **267** | Default if no second ICU site |
| ED stretchers (incl. UCC under Emergency) | 118 | ED board — not MOH beds |
| Jail Ward | 12 inpatient | Secure ward, not ambulatory |

Circle **one** per row. Evidence = physical audit / floor plan / license register.

| # | Question | Decision | Impact |
|---|---|---|---|
| **DQ-1a** | Is `ICU-EXT-2` (14) a real second ICU site? | Merge duplicate · Keep + re-parent to Critical Care · Non-bedded | Merge → inpatient **267** |
| **DQ-1b** | Is `PLASTER-2` (9) a real second plaster site? | Merge · Keep + re-parent to Surgical · Procedure only | Procedure rooms, not licensed beds |
| **DQ-2** | `ED-NAV` (3) vs `ED-NAV-2` (5) | One unit (name+count) · Two units · Both stay non-bedded | Seed already `SUPPORT` |
| **DQ-10** | CSV `Bed` is mixed-class (inpatient / ED / OR / clinic)? | **Accept classes as seeded** · Amend (attach list) | ADT beds only for `INPATIENT_LICENSED` |
| **DQ-12** | Jail = secure inpatient; UCC = Emergency stretcher; OR/PACU/clinics ≠ licensed beds; codes `W3A`/`ICU-MAIN`/`ED-RESUS`? | **Accept** · Amend | |
| **DQ-18** | MOH/CBAHI license register total = _____ beds | Matches 267 · Matches 281 · Other: _____ | **Blocking** until filled |
| **WH** | 12-hour nursing roster is an Art. 100 approved shift system (3-week average), not an 8h Art. 98 wall? | **Yes — 12h allowed** · No (8h wall) · Other: _____ | LAB-WH-001 |
| **Maternity** | Statutory maternity duration to configure | 10 weeks · 12 weeks · Other: _____ | LAB-LV-007 |

| Role | Name | Signature | Date |
|---|---|---|---|
| Director of Nursing | | | |
| Licensing / Facilities | | | |
| HR / Legal (hours + leave only) | | | |
| Applied in registry by (IT) | | | |

**After this sheet is signed:** run `artifacts/physical_bed_audit_form.md`, update the seed to the circled inpatient total, then Wave P1 (`03_configuration_checklist.md`). Unsigned = **do not load**.
