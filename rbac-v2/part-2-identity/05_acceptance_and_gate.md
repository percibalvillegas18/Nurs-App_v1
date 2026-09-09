# Part 2 — Acceptance Catalogue and Gate

## 1. Schema acceptance

- schema applies twice without error;
- all v2 foreign keys are enabled and valid;
- invalid account, employment, credential, assurance, and lifecycle states are rejected;
- SSO account without external subject is rejected;
- email normalization violations are rejected;
- duplicate normalized email, provider subject, account/staff link, employee number, and session token hash are rejected;
- unit/department mismatch is rejected;
- overlapping effective primary employment assignments are rejected;
- credential submitter cannot verify their own credential;
- append-only authentication and lifecycle events reject update/delete;
- session expiry must be after issue time;
- a session requires an active account and matching current `auth_version`;
- a local credential can be attached only to a local-auth account;
- credential expiry cannot precede issue date;
- existing tables and data remain unchanged.

## 2. Lifecycle acceptance

| ID | Scenario | Expected result |
|---|---|---|
| ID-T01 | HR supplies a new active employee with verified SSO identity | Separate staff/account records linked by immutable IDs; no role implied |
| ID-T02 | Display name matches an existing person but immutable key differs | Reconciliation issue; no automatic merge |
| ID-T03 | Employee moves from W3A to ICU-MAIN | Old assignment closes; new effective assignment created; Part 3 grant review queued |
| ID-T04 | Employee leaves | Account disabled/archived per policy; sessions revoked; history retained |
| ID-T05 | Account is locked but employment remains active | Authentication denied; employment history unchanged |
| ID-T06 | License expires | Clinical eligibility becomes blocked in Part 4; account may retain remediation access |
| ID-T07 | User submits own renewed license | Credential remains pending until independent verification |
| ID-T08 | Verifier attempts to verify own submission | Deny and audit |
| ID-T09 | Password/provider binding changes | Increment auth version; previous sessions rejected |
| ID-T10 | Duplicate verified work email is supplied | Reject and create reconciliation issue |
| ID-T11 | SSO subject changes unexpectedly | Block rebind pending controlled identity recovery |
| ID-T12 | Service account attempts clinical break-glass | Deny in Part 4 policy |

## 3. Security acceptance

- no password, raw session token, SSO assertion, MFA secret, or recovery secret appears in logs;
- production cookie and transport settings pass security review;
- token in URL is rejected;
- public production account enumeration is disabled;
- demo mode cannot start in production configuration after Part 5 cutover controls are implemented;
- privileged authentication requires approved MFA assurance;
- recovery and emergency administrator flows are tested by different authorized identities;
- rate-limit and lockout controls resist user enumeration and do not create unbounded memory/state growth;
- session revocation is effective across all application instances.

## 4. Part 2 technical result

| Gate | Result |
|---|---|
| Architecture and ownership specification | COMPLETE |
| Authentication and session requirements | COMPLETE |
| Lifecycle workflows | COMPLETE |
| Additive shadow schema | COMPLETE |
| Executable schema tests | COMPLETE when `validate_part2.py` passes |
| Production source reconciliation | **PENDING HR/IT DATA** |
| Part 1 blocking governance approvals | **PENDING** |
| Runtime authentication cutover | **NOT AUTHORIZED** |

## 5. Required sign-off

| Role | Confirms | Name/decision/date |
|---|---|---|
| HR Data Owner | Immutable employee ID, employment states, JML source | `[PENDING]` |
| Identity/IT Owner | SSO provider, subject, verified email, recovery | `[PENDING]` |
| Information Security | MFA, sessions, logging, recovery, service identities | `[PENDING]` |
| HR Credentialing | Credential source, verification, expiry/suspension | `[PENDING]` |
| DON / Clinical Safety | License impact and remediation access | `[PENDING]` |
| Privacy / Legal / Internal Audit | Data minimization, retention, access, legal hold | `[PENDING]` |
| Application Owner | Migration, feature flags, monitoring, rollback | `[PENDING]` |
