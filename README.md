# Nurs-App_v1

Hospital nursing platform repository. Contains the HNWMS (Hospital Nursing Workforce Management System) package and the **Organizational Structure / Department & Bed Capacity implementation plan**.

## Contents
- `HNWMS_Complete_Package.md` — Hospital Nursing Workforce Management System spec (Version 1.1).
- `Hospital_Nursing_Organizational_Structure.md` — source: nursing + whole-hospital org chart.
- `Department & Bed.csv` — source: department/unit/capacity registry (raw 524 values across 4 departments / 43 units). **515 is a mixed-class remainder after DQ-9, not licensed inpatient.** Seed classes capacity (`06` DQ-10): proposed licensed inpatient **281** (or **267** if `ICU-EXT-2` merged).
- `implementation-plan/` — implementation-ready ingestion plan & artifacts (see its `README.md` for the document map; start at `01_implementation_plan.md`).
- `org-directory/` — Wave P1 location registry app (login, My profile, consumer APIs). P0 still unsigned. The demo/local bootstrap requires an explicit credential setting; production authentication is not implemented.
- `rbac/` — HNWMS RBAC v1 contract (`engine.py` + `/api/rbac/evaluate`) remains the authoritative prototype engine. The v2 identity/authorization package is shadow-only pending the governance gates in `rbac-v2/`; it must not be described as production-approved.
- `compliance-guardrails/` — Saudi Labor Law & CBAHI automated guardrail layer design for HNWMS (rules engine architecture, data model + DDL, 55-rule catalogue, module integration, exceptions/approvals, dashboards, tests). Start at `01_architecture_integration.md`.
