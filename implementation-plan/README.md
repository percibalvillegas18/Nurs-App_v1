# Implementation Plan — Org Structure, Department Registry & Bed Capacity

Implementation-ready deliverables for ingesting the organizational chart, department registry, and bed capacity into the HIS / nursing-workforce platform. Sources: `Hospital_Nursing_Organizational_Structure.md` + `Department & Bed.csv`.

## Documents (read `01` first)
| # | Document | Contents |
|---|---|---|
| 01 | `01_implementation_plan.md` | Priority plan, data model summary, system mapping, RBAC, ADT/bed/surge workflows, integration & migration, reporting/alerts, security & compliance, RACI |
| 02 | `02_erd_data_model.md` | Mermaid ERD + entity/attribute specs |
| 03 | `03_configuration_checklist.md` | Wave-by-wave build/QA checklist |
| 04 | `04_ui_placement_recommendations.md` | Screen-level placement of every element |
| 05 | `05_test_acceptance_criteria.md` | Import/validation + functional acceptance test cases |
| 06 | `06_source_reconciliation.md` | Data-quality findings, cleaned taxonomy, open sign-off questions |
| 07 | `07_adjudication_decision_records.md` | DQ-1/DQ-2 proposed dispositions + per-item decision/sign-off records; how the physical audit resolves them |
| 08 | `08_signoff_don_licensing.md` | One-page DON + Licensing (+ HR/Legal) P0 sign-off: 267 vs 281, DQ-1/2, 12h Art. 100, maternity |

## Artifacts
| File | Contents |
|---|---|
| `artifacts/normalized_department_unit.csv` | Cleaned 43-unit load source with `capacity_class` and stable `unit_code`s (canonical registry seed) |
| `artifacts/org_rollup.csv` | Classed rollups: licensed inpatient **281** (or **267** excl. DQ-1a), ED stretchers 118; mixed-class 515/524 are history only |
| `artifacts/ddl_schema.sql` | PostgreSQL DDL for all domains |
| `artifacts/physical_bed_audit_form.md` | Physical bed & space audit instrument (per-unit sheet + global checklist) to reconcile the registry and resolve DQ-1/DQ-2/DQ-8/DQ-9 |

## Key figures
- **4 departments · 43 locations.** Raw CSV Bed sum **524**. DQ-9 mixed-class remainder **515** is **not** licensed inpatient (see `06` DQ-10).
- **Proposed licensed inpatient: 281** (14 units, includes pending `ICU-EXT-2`) or **267** if DQ-1a is merged. ED stretchers **118** (UCC re-parented to Emergency). Patient-placeable (inpatient+ED+PACU) **407**.
- Occupancy % uses operational **inpatient** beds, not 515/524.
- Start at **Wave P0**: execute `06_source_reconciliation.md`, run the physical audit (`artifacts/physical_bed_audit_form.md`), confirm DQ dispositions per `07_adjudication_decision_records.md`, obtain sign-offs, then provision Org Directory + Bed registry per `03_configuration_checklist.md`.
