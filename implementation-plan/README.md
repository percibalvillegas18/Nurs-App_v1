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

## Artifacts
| File | Contents |
|---|---|
| `artifacts/normalized_department_unit.csv` | Cleaned 43-unit load source (canonical registry seed) |
| `artifacts/org_rollup.csv` | Facility/department/unit-group capacity rollups (515 assignable beds, 4 depts, 43 units; source 524) |
| `artifacts/ddl_schema.sql` | PostgreSQL DDL for all domains |
| `artifacts/physical_bed_audit_form.md` | Physical bed & space audit instrument (per-unit sheet + global checklist) to reconcile the registry and resolve DQ-1/DQ-2/DQ-8/DQ-9 |

## Key figures
- **4 departments · 43 locations · 515 assignable beds** (36 bedded + 7 non-bedded). Raw source total is **524**; the 9-bed delta = 2 Admin & Support rows (`EDAD`, `ORAD`) reclassified non-bedded (see `06` DQ-9).
- Assignable dept beds: Emergency **106** · Surgical **29** · Critical/ICU **99** · General & Specialty **281** (source: 113 / 31 / 99 / 281).
- Start at **Wave P0**: execute `06_source_reconciliation.md`, run the physical audit (`artifacts/physical_bed_audit_form.md`), confirm DQ dispositions per `07_adjudication_decision_records.md`, obtain sign-offs, then provision Org Directory + Bed registry per `03_configuration_checklist.md`.
