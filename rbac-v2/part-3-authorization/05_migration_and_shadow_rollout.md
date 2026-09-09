# Part 3 — Migration and Shadow Rollout

## 1. Additive boundary

`authorization_schema.sql` creates only `_v2` tables and triggers. It does not alter `role`, `permission`, `role_permission`, `persona`, `role_grant`, `sod_rule`, `rbac_decision_log`, the current API, or seed behavior.

## 2. Migration inventory

Before populating shadow policy, reconcile:

- every legacy role and permission against the signed atomic matrix;
- every active legacy grant to a Part 2 immutable user and validated scope;
- free-text scopes that are missing, inactive, ambiguous, or in the wrong facility;
- open-ended and expired grants;
- identities holding multiple roles and all overlapping SoD conflicts;
- `SYS_ADMIN` clinical entitlements and current waiver use;
- current consumers of `/api/rbac/evaluate` and protected operations that bypass it;
- decision-log completeness and correlation to committed writes.

Do not auto-convert a renamed demo persona into a production identity. Part 2 reconciliation must supply the immutable mapping.

## 3. Shadow comparison

1. Load an approved draft policy version and validated scopes.
2. Map reconciled legacy grants to v2 requests/grants without activating production enforcement.
3. Evaluate current and v2 engines for the same identity, permission, resource, time, and request context.
4. Classify differences as expected policy correction, data-quality issue, engine defect, or unresolved governance decision.
5. Treat every unexplained high-risk legacy-allow/v2-deny and legacy-deny/v2-allow difference as blocking.
6. Repeat after source, policy, and engine corrections using a new policy version where semantics changed.

## 4. Enforcement prerequisites

- Part 1 role, permission, SoD, scope, and audit decisions signed;
- Part 2 privileged identity mapping complete and approved;
- atomic permission mapping covers every protected endpoint/background job;
- zero orphan active privileged grants and zero invalid active scopes;
- all required SoD rules encoded and negative-tested;
- delegation policy signed before any delegation activation;
- Part 4 clinical and BCP dependencies integrated for protected clinical writes;
- zero unexplained high-risk shadow differences;
- authorization latency, availability, audit durability, and rollback accepted.

## 5. Rollback

Cutover must use a controlled feature flag and preserve the last approved policy. Rollback stops v2 enforcement, revokes newly created derived entitlements where required, and preserves all requests, decisions, and lifecycle evidence. It never restores an insecure standing SoD waiver or authorizes use of demo identities in production.

Policy rollback selects a previously approved immutable version; it does not edit historical role/permission membership. Decisions remain reproducible against the version recorded at decision time.
