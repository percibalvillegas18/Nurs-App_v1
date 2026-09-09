# Part 3 — Atomic Permission and Validated Scope Model

## 1. Versioned policy catalogue

Roles and permissions belong to an immutable policy version. A published version is not edited in place. A successor version is drafted, reviewed, tested, activated, and later retired while historical decisions keep their original version.

The Part 3 schema supplies the mechanism, not signed hospital policy content. Current roles remain mapped in the Part 1 boundary matrix until `GOV-RBAC-01` is approved.

## 2. Required permission decomposition

| Legacy permission | Target atomic permissions | Control reason |
|---|---|---|
| `ADT_WRITE` | `ADT_ADMIT`, `ADT_TRANSFER`, `ADT_DISCHARGE`, `ADT_CORRECT` | Different workflows, scopes, and correction evidence |
| `SCHED_WRITE` | `SCHED_PREPARE`, `SCHED_REVIEW`, `SCHED_APPROVE`, `SCHED_PUBLISH` | Enforces preparer/final-approver separation |
| `APPROVE` | Workflow-specific approvals such as `BED_EXCEPTION_APPROVE`, `GRANT_APPROVE`, `DELEGATION_APPROVE`, `LICENSE_EXCEPTION_APPROVE` | Generic approval is too broad to govern safely |
| Ambiguous patient assignment | `CARE_ASSIGNMENT_WRITE` versus existing `BED_CONTROL` | Clinical care assignment never implies physical-bed authority |

Permissions have a risk class and flags for MFA, Part 4 context, and whether delegation may be considered. Exact role bundles remain pending accountable approval.

## 3. Strong scope references

`authorization_scope_v2` contains exactly one foreign key to a facility, department, or unit. Free-text scope codes cannot create grants.

| Grant scope | Facility target | Department target | Unit target |
|---|---:|---:|---:|
| Facility AIGH | AIGH only | Active department in AIGH | Active unit whose department is in AIGH |
| Department CRIT | Deny | CRIT only | Active unit in CRIT |
| Unit ICU-MAIN | Deny | Deny | ICU-MAIN only |

Facility scope is not a global wildcard. Inactive scope records or inactive directory resources deny. Scope containment is calculated from the authoritative `facility` → `department` → `nursing_unit` relationships at decision time.

## 4. Context boundaries

Part 3 models authorization scope only. These constraints are explicitly deferred to Part 4 and must not be guessed by the RBAC engine:

- effective staff employment and assigned unit;
- scheduled shift and handover/grace windows;
- patient/care relationship;
- professional license, competency, training, and occupational restrictions;
- staffing, skill mix, acuity, and compliance guardrails;
- break-glass eligibility and event-scoped bundles.

Permissions marked `requires_part4 = 1` produce a Part 3 result that must be composed with those controls before the protected transaction commits.

## 5. Resource identifiers

Callers use `FACILITY`, `DEPARTMENT`, or `UNIT` and the stable directory code. Unknown type/code, duplicate resolution, wrong-facility ancestry, or inactive resource denies. Patient, roster, bed, and other domain objects must resolve to one of these directory anchors before authorization; callers cannot supply an untrusted scope claim as the answer.
