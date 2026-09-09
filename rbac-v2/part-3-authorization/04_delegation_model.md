# Part 3 — Constrained Delegation Model

## 1. Principle

Delegation is a temporary derived entitlement, not a copied role and not impersonation. It is linked to one active source grant and can only reduce its permission, scope, and time boundaries.

## 2. Required fields and controls

- named delegator and delegate accounts;
- one direct source grant owned by the delegator;
- exact validated scope equal to or narrower than the source scope;
- explicit subset of permissions already present in the source role;
- exact start and end timestamps within the source grant window;
- structured reason and justification;
- independent approver; neither delegator nor delegate may approve;
- `allow_redelegation = 0` by default;
- activation-time and use-time SoD evaluation;
- automatic expiry and immediate revocation;
- append-only activation, use, revocation, and expiry evidence.

Part 3 does not permit delegation sourced from another delegation. Future redelegation requires a governance revision and explicit ancestry/depth controls.

## 3. Scope subset rules

| Source grant | Delegation allowed |
|---|---|
| Facility AIGH | Facility AIGH, a department in AIGH, or a unit in AIGH |
| Department CRIT | Department CRIT or a unit in CRIT |
| Unit ICU-MAIN | Unit ICU-MAIN only |

Cross-facility, sibling-department, and sibling-unit delegation is rejected. Inactive scopes reject activation and use.

## 4. Permission subset rules

A delegated permission must:

1. belong to the source role in the same policy version;
2. be marked delegable in the permission catalogue;
3. not be prohibited by the approved delegation policy;
4. not create an overlapping blocking SoD conflict for the delegate;
5. pass Part 4 qualification/eligibility checks when clinically sensitive.

For example, a Unit Manager can delegate an approved operational review only if that atomic permission belongs to the Unit Manager role. They cannot delegate `BED_CONTROL`, because that permission is outside the approved Unit Manager boundary.

## 5. Lifecycle

`REQUESTED` → `APPROVED` → `ACTIVE`, or `REJECTED`. An active delegation becomes `SUSPENDED`, `REVOKED`, or time-expired. Evaluation treats it as inactive immediately when the source grant is inactive, revoked, outside its effective window, or its policy is retired.

## 6. Governance gate

The schema and tests demonstrate safe mechanics, but no production delegation may activate until `GOV-DEL-01` and `GOV-DEL-02` define the approved permission subset, maximum duration, approval matrix, qualification requirements, notifications, and recertification behavior.
