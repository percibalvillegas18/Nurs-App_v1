# Nurs-App_v1

Hospital nursing platform repository. Contains the HNWMS (Hospital Nursing Workforce Management System) package and the **Organizational Structure / Department & Bed Capacity implementation plan**.

## Contents
- `HNWMS_Complete_Package.md` — Hospital Nursing Workforce Management System spec (Version 1.0).
- `Hospital_Nursing_Organizational_Structure.md` — source: nursing + whole-hospital org chart.
- `Department & Bed.csv` — source: department/unit/bed-capacity registry (raw 524 bed values across 4 departments / 43 units; operational/assignable 515 after reclassifying 2 Admin & Support rows).
- `implementation-plan/` — implementation-ready ingestion plan & artifacts (see its `README.md` for the document map; start at `01_implementation_plan.md`).
- `compliance-guardrails/` — Saudi Labor Law & CBAHI automated guardrail layer design for HNWMS (rules engine architecture, data model + DDL, 55-rule catalogue, module integration, exceptions/approvals, dashboards, tests). Start at `01_architecture_integration.md`.
