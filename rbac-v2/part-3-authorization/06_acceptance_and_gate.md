# Part 3 — Acceptance Catalogue and Gate

## 1. Automated acceptance

- schema applies twice without error;
- only additive `_v2` tables are created;
- policy-version, account, role, permission, scope, grant, and delegation references are valid;
- facility scope is limited to its facility hierarchy;
- department and unit containment is exact;
- unknown or inactive resource, permission, account, policy, or grant denies;
- expired, suspended, and revoked grants/delegations deny at decision time;
- self-approved grants and delegations are rejected;
- dual-control activation identity is enforced;
- delegation time, scope, and permission are subsets of the source grant;
- non-delegable permission is rejected;
- all simultaneous applicable SoD rules are returned and any blocking rule denies;
- decision and lifecycle evidence is append-only;
- Unit Manager has no `BED_CONTROL`, Scheduler has no `BED_CONTROL`, and Charge control is unit-scoped in the tested draft policy;
- `CARE_ASSIGNMENT_WRITE` remains distinct from `BED_CONTROL`;
- Part 1 and Part 2 regression validators pass.

## 2. Required integration acceptance before enforcement

- every protected operation calls the central evaluator server-side immediately before commit;
- authorization decision/request ID is attached to the protected write;
- no UI-only or client-supplied scope enforcement;
- simultaneous policy/grant change cannot create a time-of-check/time-of-use bypass;
- shadow comparison reaches zero unexplained high-risk differences;
- service timeout and dependency failure follow approved `GOV-BCP-01` behavior;
- performance and availability targets are signed and measured;
- Part 4 checks are composed for every `requires_part4` permission.

## 3. Approval record

| Gate | Result |
|---|---|
| Part 3 technical package | **PASS when `validate_part3.py` succeeds** |
| Runtime authorization change | NONE |
| `GOV-RBAC-01/02/03` and `GOV-SCOPE-01` | `[PENDING]` |
| `GOV-DEL-01/02` | `[PENDING]` |
| Part 1 overall approval | `[PENDING]` |
| Production data reconciliation | `[PENDING]` |
| Shadow comparison | `[NOT RUN]` |
| Runtime RBAC v2 cutover | **NOT AUTHORIZED** |

## 4. Accountable acceptance

| Area | Required approver |
|---|---|
| Role/permission boundaries | DON, workflow owners, IT Security, Application Owner |
| Scope containment | Org Directory Owner, DON, IT Security |
| SoD catalogue/enforcement | DON, Internal Audit, IT Security |
| Delegation | DON, Nursing Operations, HR, IT Security |
| Decision evidence | Internal Audit, Privacy/Legal, IT Security |
| Production enforcement | Change authority plus all dependencies above |

No placeholder is evidence of approval.
