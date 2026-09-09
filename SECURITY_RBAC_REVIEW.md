# Security and RBAC review

**Review date:** 2026-09-09 UTC  
**Scope:** `org-directory/`, `rbac/`, migrations 005–008, and the RBAC v2 design/engines.  
**Conclusion:** this is a useful prototype and shadow-mode reference implementation, but it is **not production-ready for hospital identity, ADT, bed control, scheduling, or clinical transactions**.

## Executive summary

The most important risks are:

1. The runtime still uses demo/persona-slot identities, local password authentication, a browser-stored bearer token, and no SSO/MFA.
2. The v1 engine previously treated a facility grant as a wildcard. It could allow an unknown resource or a resource in another facility. The evaluator now resolves active resource ancestry and denies unknown/inactive resources.
3. `RBAC_SHADOW_MODE=false` selects the v1 engine; it does **not** switch enforcement to v2. A safe, explicit v2 enforcement mode and a signed rollout gate are still required.
4. `SYS_ADMIN` still has all clinical permissions and a standing SoD waiver in the seed. The v2 governance package correctly identifies this as prototype debt, but it is still present in the live v1 seed.
5. The API authenticates most reads but does not yet provide transaction-bound enforcement for the actual ADT/bed/scheduling writes. Calling a GET evaluation endpoint must not be treated as authorization for a later write.

**Recommended disposition:** keep the v1 engine in isolated demo/shadow use only. Do not connect it to real staff, patient, ADT, bed, or roster data until the blocking identity, permission, SoD, clinical-safety, and degraded-mode decisions are approved and implemented.

## Validation performed

The following checks were run:

- Python compilation of application, migration, RBAC, and test modules: **pass**.
- `python3 tests/test_security_fixes.py`: **24 tests passed**.
- `python3 tests/test_shadow_integration.py`: **6 integration checks passed**.
- Part 2 identity, Part 3 authorization, and Part 4 clinical-safety test/validator scripts: **pass**.
- Fresh local bootstrap using `SEED_PASSWORD` followed by `python3 migrations/migrate.py`: migrations **1–9 applied**, including the Python v2 seed and one-active-policy invariant.
- `python3 -m pytest -q` could not run because pytest is not installed in the environment; the repository's unittest-style scripts were run directly instead.

## Findings and recommendations

Severity uses **Critical**, **High**, and **Medium**. “Fixed in this review” means the prototype defect was corrected in the working tree; it does not make the surrounding production control complete.

### C-01 — Shared credentials and public login enumeration — OPEN

**Evidence:** `org-directory/seed.py`, `org-directory/um.py`, `org-directory/static/login.js`, and the `/api/auth/accounts` login picker.

The original seed path gave every account `Demo@2026`; the browser stored the returned bearer token in both `sessionStorage` and `localStorage`; local authentication has no MFA; and account identifiers/display names are exposed to an unauthenticated demo picker. The v2 governance charter explicitly says shared credentials and public account lists are prohibited in production.

**Recommendation:**

- Use hospital SAML/OIDC/Entra/AD SSO as the only normal authentication path.
- Require MFA/step-up (AAL2) for privileged access and high-risk clinical actions.
- Map an immutable HR employee/staff identifier to the identity account; never reuse a job/persona slot for a different employee.
- Remove public account enumeration outside an isolated demo profile.
- Use a Secure, HttpOnly, host-only cookie or a short-lived in-memory access token; do not return a long-lived bearer token to JavaScript/localStorage.
- Add joiner/mover/leaver reconciliation, account lock/disable, and authentication-event auditing.

**Prototype hardening applied:** seeding now refuses to create a shared-password database unless `DEMO_MODE=true` is explicitly set or an out-of-band `SEED_PASSWORD` is provided; it no longer prints the password. The production login page now has username/password controls, new session rows store token digests, and the browser no longer writes the bearer to localStorage. This is not a substitute for SSO/MFA or a memory-only/HttpOnly production session.

### C-02 — Facility scope and resource validation — FIXED IN THIS REVIEW; keep regression coverage

**Original defect:** `RbacEngine._scope_contains()` returned `True` for every resource when the grant scope was `FACILITY`. A bed coordinator could receive `ALLOW` for `UNIT:NOPE`, `FACILITY:OTHER`, or an unknown resource. A future/inactive grant was also a risk if the identity helper and engine disagreed on effective dates.

**Recommendation:** every decision must:

1. allow only `FACILITY`, `DEPARTMENT`, or `UNIT` resource types;
2. resolve the resource through active facility → department → unit records;
3. verify the grant scope contains that exact ancestry;
4. deny unknown, inactive, ambiguous, or cross-facility resources; and
5. evaluate grant effective dates at the same instant used by the identity/session layer.

The v1 engine now implements those checks, and `user_from_conn()` now includes grant effective dates when deriving administrative roles. The v2 structured scope model should become the only production source of authorization scope.

### H-01 — v2 is shadow-only and the cutover flag is misleading — OPEN

`app.py` creates `ShadowRbacAdapter` only while `RBAC_SHADOW_MODE` is true. When it is false, the code falls back to `RbacEngine` v1; it does not run v2-only enforcement. `rbac/cutover_v2.py` previously described setting the flag to false as the next step to stop v1 alongside v2, which could create a false sense of completion.

**Recommendation:** replace the boolean with an explicit, audited mode:

- `v1` — legacy prototype only;
- `shadow` — v1 decision returned, v2 observed and compared;
- `v2_enforced` — v2 decision returned and protected writes are transaction-bound;
- `disabled` — fail closed for protected operations.

The service must refuse `v2_enforced` unless policy, identity, scope, clinical-safety, audit durability, and rollback gates are satisfied. Do not use a production `--force` cutover switch. Keep the previous approved policy immutable for rollback.

### H-02 — migration/readiness drift — FIXED IN THIS REVIEW; add CI coverage

`migrations/migrate.py` originally applied only SQL files. It created the v2 tables but skipped Python migration 008, which creates the active shadow policy, v2 identity/grant mappings, and `rbac_shadow_divergence_log`. The old readiness check looked only for `authorization_policy_v2`; this could mark a partial install as shadow-active and make `/api/rbac/shadow/status` fail.

The runner now executes migration 008 in order, and the app distinguishes schema presence from a seeded active runtime. Keep a clean-install test that runs exactly the documented seed/migration commands and checks:

- one active policy;
- all active grants map to real approved identities/scopes;
- divergence logging is available;
- partial migrations are reported as not ready; and
- rollback 008 leaves v1 usable without silently deleting unrelated v2 data.

### H-03 — standing `SYS_ADMIN` clinical power and SoD waiver — OPEN / BLOCKING

**Evidence:** `org-directory/seed.py` grants `SYS_ADMIN` `BED_CONTROL`, `ADT_WRITE`, `SCHED_WRITE`, `APPROVE`, and other clinical permissions; `sod_rule.waive_roles` contains `SYS_ADMIN`.

This violates least privilege and lets one standing technical identity bypass the main bed-control/scheduling conflict. The v2 governance documents correctly call this prototype debt, but documentation does not mitigate the live seed.

**Recommendation:**

- Remove clinical permissions and the permanent waiver from `SYS_ADMIN`.
- Split technical administration into narrowly scoped `IDENTITY_ADMIN`, `ROLE_CATALOG_ADMIN`, `POLICY_PUBLISH`, `AUDIT_ADMIN`, and diagnostics permissions.
- Use event-scoped break-glass only for approved operational bundles; require step-up, exact resource scope, short expiry, alerting, and independent review.
- Never allow break-glass to grant identity, role, policy, credential, audit-delete, or permanent SoD-waiver permissions.

### H-04 — Authentication is not the same as authorization on API routes — OPEN

The API requires a session for most routes, but route authorization is incomplete. In particular, consumer reads, audit data, RBAC catalog/grant data, shadow status, and scenario execution need distinct permissions and data filtering. The scenario endpoint also performs writes to decision evidence when called by GET.

The working tree now protects the grant/audit/policy/shadow inspection routes with `AUDIT_READ`, but the larger consumer contract still needs a complete route matrix and scoped responses.

**Recommendation:** define and enforce a route/action matrix, for example:

| API/action | Required control |
|---|---|
| Org/unit read | `ORG_READ` plus facility/department/unit scope |
| People/profile read | own record or explicit `STAFF_PROFILE_READ` scope |
| Credential/document read | `CREDENTIAL_READ`, minimum necessary fields, audit |
| Grant/policy/SoD read | `RBAC_READ`/`AUDIT_READ` |
| Grant request/approve/activate | separate permissions and dual control |
| Taxonomy write | `ORG_ADMIN`/`ORG_WRITE`; no clinical power |
| Bed assign/release/block | atomic bed permission plus Part 4 context gate |
| Roster draft/review/publish | separate scheduler permissions and SoD |
| Break-glass activation/review | separate event-scoped permissions |

Do not rely on UI hiding. Enforce the matrix in server middleware and in each consumer service.

### H-05 — evaluation is not transaction-bound — OPEN / BLOCKING for clinical writes

The current contract exposes `GET /api/rbac/evaluate`. It returns a decision, but there are no real bed/ADT/roster mutation endpoints in this repository that atomically couple the decision to the protected write. A caller could evaluate once and perform a different or later write after a grant, patient, bed, or policy changes.

**Recommendation:** protected services should call a central PDP/middleware immediately before the write and pass:

- immutable subject/account ID and assurance level;
- operation-specific permission;
- exact resource ID and current resource version;
- current staff assignment/shift/care context;
- policy version and a unique request/correlation ID;
- transaction/write intent and a short decision TTL.

The write service must reject missing, expired, mismatched, or `ERROR` decisions in the same transaction. High-risk writes fail closed during dependency failure; an approved, finite continuity route is separate from normal authorization.

### H-06 — permission granularity and clinical context are insufficient — OPEN

The v1 catalog bundles high-impact operations into `ADT_WRITE`, `SCHED_WRITE`, `APPROVE`, and `BED_CONTROL`. It does not itself evaluate employment status, assignment, shift, license, competency, care context, staffing/acuity guardrails, or clinical safety freshness. Part 4 is still shadow-only.

**Recommendation:** decompose at minimum into:

- `BED_ASSIGN`, `BED_RELEASE`, `BED_BLOCK`, `BED_VIEW`;
- `ADT_ADMIT`, `ADT_TRANSFER`, `ADT_DISCHARGE`;
- `SCHED_DRAFT`, `SCHED_REVIEW`, `SCHED_PUBLISH`;
- `CARE_ASSIGNMENT_WRITE`;
- `GRANT_REQUEST`, `GRANT_APPROVE`, `GRANT_ACTIVATE`;
- `CREDENTIAL_SUBMIT`, `CREDENTIAL_VERIFY`;
- `BREAK_GLASS_ACTIVATE`, `BREAK_GLASS_REVIEW`; and
- narrowly scoped read/admin permissions.

Use RBAC for the baseline, ABAC/context predicates for assignment/shift/care/credential state, and the Part 4 safety composer for eligibility and guardrails. A Part 3 `ALLOW` must not by itself authorize a clinical transaction.

### H-07 — v2 cutover must not manufacture identity verification — FIXED IN THIS REVIEW

Migration 008 creates human accounts as `PENDING_VERIFICATION` with `LEGACY_LOCAL`; the old cutover script promoted them by assigning `persona_code@migrated.local` and setting `email_verified_at`. That is not proof of a real person, verified email, SSO subject, or MFA.

The cutover script now blocks pending/legacy-local/unverified human identities and never creates placeholder email addresses. Complete HR/SSO/credential reconciliation first. The migration service accounts also need a formally approved, separately controlled bootstrap process; a hard-coded “system approver” is not a human approval.

### M-01 — session and password security — PARTIALLY FIXED; still OPEN

The browser still has a bearer-token path, sessions are long-lived for a prototype (12 hours), password changes do not use a current-password/step-up requirement for administrators, and there is no auth-version check in the live v1 session path. New sessions now store a SHA-256 token digest at rest while accepting legacy raw-token rows for migration; the legacy rows must be rotated out.

**Recommendation:** use Secure/HttpOnly/SameSite cookies behind TLS; rotate on login/privilege change; add revocation reason and auth-version checks; add per-account and per-IP throttling, lockout/alerting, reauthentication for password/admin changes, and MFA. Prefer removal of local passwords through SSO.

### M-02 — audit and shadow evidence quality — OPEN

The v2 evidence is append-only, but the legacy decision/event tables are not equivalently protected. Shadow divergence logging is best-effort and catches all exceptions, so a full log failure can be invisible. The divergence report denominator is the legacy decision log, while scenario calls and v2 decisions are not always one-to-one with that denominator. Read-only scenario requests can also create audit rows repeatedly.

**Recommendation:**

- make audit writes durable or raise/alert when evidence cannot be recorded;
- add a correlation/request ID to both legacy and v2 decisions;
- calculate divergence only over comparable paired evaluations;
- make scenario execution an admin-only test operation or run it against a disposable database;
- protect legacy audit tables with append-only controls and restricted DB credentials;
- define retention, legal hold, export, and independent review ownership.

The v2 evaluator now rejects reuse of an idempotency key with a different account, permission, resource, policy, or context. Keep a regression test for that property.

### M-03 — document upload integrity and privacy — PARTIALLY FIXED; still OPEN

Uploads still allow a client-supplied MIME type and legacy rows may have no checksum. The working tree now catches only the expected pre-migration missing-column case and verifies a stored SHA-256 before download. Admin-role users can still see all profile documents, including national ID and credentials, without a separate minimum-necessary permission model.

**Recommendation:** validate file signatures and extension/MIME together; store outside the static tree; write file and metadata atomically; quarantine/scan files; require a checksum for all new/legacy records; enforce per-document authorization, retention, masking, and access audit.

## Recommended target RBAC model

### Roles

Use job roles only as curated bundles; never use them as identity. A practical baseline is:

- **Charge Nurse — unit/shift:** unit-scoped bed operations only while assigned and clinically eligible.
- **Bed Coordinator — facility:** bed placement/release across the facility; no roster publish.
- **House Supervisor — facility:** surge/operational placement under approved workflow; no standing technical administration.
- **Unit Manager — department/unit:** approvals, blocks, and operational oversight; no routine placement.
- **Scheduler — department:** draft/review/publish roster with separate publish/approval controls; no bed control.
- **ADT Clerk — department:** registration/request operations only; no placement.
- **Staff/Team Lead — unit/shift/care relationship:** minimum self-service and approved care-assignment actions; no bed control.
- **Org Administrator — organization data:** taxonomy/locations only; no clinical permissions.
- **Security/Identity Administrator — technical plane:** identities, policy/catalog diagnostics only; no clinical permissions.
- **Auditor — read-only:** append-only audit evidence, with export controls and no operational writes.
- **Break-glass operator:** no standing role expansion; exact event, bundle, unit, expiry, step-up, alert, and independent review.

### Mandatory SoD rules

At minimum enforce these as operation-level conflicts, not broad role labels:

- bed assignment vs roster publish when the effective scopes overlap;
- roster preparation vs final approval/publish where dual control applies;
- credential submission vs credential verification;
- grant request vs grant approval;
- grant approval vs grant activation for high-risk grants;
- delegation request vs delegation approval;
- break-glass activation vs post-event review; and
- operational write vs audit/policy evidence administration.

Evaluate **all** applicable conflicts and record them. Do not use a permanent `SYS_ADMIN` waiver. Scope overlap and effective time must be explicit.

### Decision sequence

```text
SSO/MFA identity
  -> active account and employment
  -> approved policy version
  -> atomic permission
  -> active resource and facility ancestry
  -> effective role/grant/delegation and scope
  -> all applicable SoD rules
  -> shift/care/license/competency eligibility
  -> staffing/acuity/compliance guardrails
  -> short-lived transaction-bound decision
  -> protected write and immutable audit evidence
```

Unknown input, inactive identity/resource, stale evidence, policy conflict, or engine/storage `ERROR` must deny or hold the protected operation. A separate, finite continuity/break-glass flow must be visible and reviewed.

## Priority implementation plan

### Before any real data or clinical integration

1. Approve the blocking decisions in `rbac-v2/part-1-governance/04_decision_register.md`.
2. Remove shared credentials/persona-slot production use; integrate SSO/MFA and HR identity mapping.
3. Remove the standing `SYS_ADMIN` clinical permissions/waiver.
4. Publish the atomic permission and endpoint matrix.
5. Add central middleware/PDP and transaction coupling for every protected write.
6. Add route/data-scope controls and audit access controls.
7. Implement Part 4 eligibility/guardrails and approved degraded-mode behavior.

### Before v2 enforcement

1. Reconcile every legacy person, grant, scope, and SoD conflict.
2. Require zero unmapped privileged identities, invalid scopes, and unexplained high-risk shadow differences.
3. Run comparable positive/negative, cross-facility, expiry, revocation, concurrent-write, and failure-mode tests.
4. Use an explicit `v2_enforced` feature flag with an emergency rollback to a previously approved policy, not an implicit boolean fallback.
5. Monitor authorization latency, error rate, decision/audit durability, policy version drift, active delegations, and break-glass use.

## Acceptance gates

Do not declare production-ready until all of the following are demonstrated in CI/staging:

- an expired/future/revoked grant cannot confer access anywhere, including admin helpers;
- unknown and cross-facility resources always deny;
- no scheduler can perform bed control, and no charge nurse can control another unit;
- no requester can approve/activate their own high-risk grant or exception;
- a reused request ID with changed inputs returns an error, not the prior allow;
- stale/missing license, assignment, shift, competency, guardrail, or policy evidence fails closed for protected writes;
- break-glass is step-up authenticated, exact-scope, finite, alerted, and independently reviewed;
- every decision is correlated to the protected write and immutable audit evidence;
- a partial migration cannot activate shadow/enforced mode; and
- rollback preserves evidence and does not restore shared credentials or standing waivers.
