# HNWMS RBAC v2 — Five-Part Major Revision

This folder controls the approved five-part revision path for HNWMS identity and authorization.

| Part | Package | Status |
|---:|---|---|
| 1 | Governance and approved clinical boundaries | **DRAFT COMPLETE — AWAITING APPROVAL** |
| 2 | Identity, authentication, and lifecycle | NOT STARTED |
| 3 | RBAC engine, scopes, SoD, and delegation | NOT STARTED |
| 4 | Clinical eligibility, guardrails, and break-glass | NOT STARTED |
| 5 | Migration, validation, rollout, and final approval | NOT STARTED |

Part 1 is documentation and control definition. It does not alter the live RBAC engine, seed data, database schema, API behavior, or approved P0 capacity status.

## Part 1 artifacts

- `part-1-governance/01_governance_charter.md`
- `part-1-governance/02_role_boundary_matrix.csv`
- `part-1-governance/03_sod_catalog.csv`
- `part-1-governance/04_decision_register.md`
- `part-1-governance/05_traceability_and_acceptance.md`
- `part-1-governance/validate_part1.py`

## Gate rule

Part 2 implementation may be designed, but production-facing changes must not be presented as approved until every `BLOCKING` Part 1 decision has a named approver, decision, conditions, and date. Any later change to a Part 1 boundary requires impact analysis and regression against the Part 1 acceptance catalogue.
