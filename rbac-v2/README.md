# HNWMS RBAC v2 — Five-Part Major Revision

This folder controls the approved five-part revision path for HNWMS identity and authorization.

| Part | Package | Status |
|---:|---|---|
| 1 | Governance and approved clinical boundaries | **DRAFT COMPLETE — AWAITING APPROVAL** |
| 2 | Identity, authentication, and lifecycle | **TECHNICAL PACKAGE COMPLETE — SHADOW ONLY / AWAITING APPROVAL** |
| 3 | RBAC engine, scopes, SoD, and delegation | **TECHNICAL PACKAGE COMPLETE — SHADOW ONLY / AWAITING APPROVAL** |
| 4 | Clinical eligibility, guardrails, and break-glass | **TECHNICAL PACKAGE COMPLETE — SHADOW ONLY / AWAITING APPROVAL** |
| 5 | Migration, validation, rollout, and final approval | NOT STARTED |

Part 1 is documentation and control definition. It does not alter the live RBAC engine, seed data, database schema, API behavior, or approved P0 capacity status.

## Part 1 artifacts

- `part-1-governance/01_governance_charter.md`
- `part-1-governance/02_role_boundary_matrix.csv`
- `part-1-governance/03_sod_catalog.csv`
- `part-1-governance/04_decision_register.md`
- `part-1-governance/05_traceability_and_acceptance.md`
- `part-1-governance/validate_part1.py`

## Part 2 artifacts

- `part-2-identity/01_identity_architecture.md`
- `part-2-identity/02_authentication_security_requirements.md`
- `part-2-identity/03_identity_lifecycle_workflows.md`
- `part-2-identity/04_migration_and_rollback.md`
- `part-2-identity/05_acceptance_and_gate.md`
- `part-2-identity/identity_schema.sql`
- `part-2-identity/migration_inventory.sql`
- `part-2-identity/test_identity_schema.py`
- `part-2-identity/validate_part2.py`

## Gate rule

Part 2 implementation may be designed, but production-facing changes must not be presented as approved until every `BLOCKING` Part 1 decision has a named approver, decision, conditions, and date. Any later change to a Part 1 boundary requires impact analysis and regression against the Part 1 acceptance catalogue.

The Part 2 schema is additive and uses `_v2` shadow tables. It is not loaded by `org-directory/seed.py` or used by the current API. This preserves rollback and prevents an unsigned identity design from silently replacing the demo runtime.

## Part 3 artifacts

- `part-3-authorization/01_authorization_architecture.md`
- `part-3-authorization/02_permission_and_scope_model.md`
- `part-3-authorization/03_grant_and_sod_governance.md`
- `part-3-authorization/04_delegation_model.md`
- `part-3-authorization/05_migration_and_shadow_rollout.md`
- `part-3-authorization/06_acceptance_and_gate.md`
- `part-3-authorization/authorization_schema.sql`
- `part-3-authorization/engine_v2.py`
- `part-3-authorization/test_authorization_v2.py`
- `part-3-authorization/validate_part3.py`

Part 3 is also additive. It defines a versioned shadow policy, strongly referenced scopes, governed grants, all-conflict SoD evaluation, constrained delegation, and append-only decision evidence. It is not wired to `/api/rbac/evaluate`; the current `rbac/engine.py` remains unchanged until the approval and shadow-comparison gates pass.

## Part 4 artifacts

- `part-4-clinical-safety/01_safety_architecture.md`
- `part-4-clinical-safety/02_eligibility_and_freshness.md`
- `part-4-clinical-safety/03_guardrail_composition.md`
- `part-4-clinical-safety/04_exception_separation.md`
- `part-4-clinical-safety/05_break_glass_controls.md`
- `part-4-clinical-safety/06_degraded_mode_and_rollout.md`
- `part-4-clinical-safety/07_acceptance_and_gate.md`
- `part-4-clinical-safety/clinical_safety_schema.sql`
- `part-4-clinical-safety/safety_engine.py`
- `part-4-clinical-safety/test_clinical_safety.py`
- `part-4-clinical-safety/validate_part4.py`

Part 4 is additive and shadow-only. It composes current clinical evidence with the existing compliance-guardrail specification and Part 3 authorization decisions. It does not introduce staffing ratios or legal thresholds, activate break-glass, or authorize a clinical transaction before the accountable approvals and Part 5 rollout gate.
