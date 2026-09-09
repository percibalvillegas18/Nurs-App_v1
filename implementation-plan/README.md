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

## Artifacts
| File | Contents |
|---|---|
| `artifacts/normalized_department_unit.csv` | Cleaned 43-unit load source (canonical registry seed) |
| `artifacts/org_rollup.csv` | Facility/department/unit-group capacity rollups (524 beds, 4 depts, 43 units) |
| `artifacts/ddl_schema.sql` | PostgreSQL DDL for all domains |

## Key figures (from source)
- **4 departments · 43 locations (38 bedded + 5 support/admin) · 524 licensed beds**.
- Dept beds: Emergency **113** · Surgical **31** · Critical/ICU **99** · General & Specialty **281**.
- Start at **Wave P0**: execute `06_source_reconciliation.md`, obtain sign-offs, then provision Org Directory + Bed registry per `03_configuration_checklist.md`.
