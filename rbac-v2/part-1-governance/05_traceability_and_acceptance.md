# Part 1 Traceability, Risk, and Acceptance

## 1. Traceability to the current repository

| Control | Current evidence | Current result | RBAC v2 requirement | Owning part |
|---|---|---|---|---:|
| Unit Manager does not place patients | `rbac/README.md`; `org-directory/seed.py` | Implemented by omission of `BED_CONTROL` | Preserve and test explicitly | 1/3 |
| Scheduler separated from bed control | `rbac/README.md`; `sod_rule`; role seed | Implemented, but SYS_ADMIN has standing waiver | Remove role waiver; use event-scoped elevation | 1/3/4 |
| Charge unit scope | `role_grant`; `RbacEngine._scope_contains` | Implemented for seeded unit grants | Add assignment/context validity and wrong-facility tests | 3 |
| Facility bed control | `BED_COORD`, `HOUSE_SUP` seed roles | Implemented | Preserve with operation-specific permissions | 1/3 |
| Staff Nurse visibility | `STAFF` role | Basic `ORG_READ` and `BED_READ` | Add approved shift/care context; keep no `BED_CONTROL` | 1/3 |
| Real-person identity | `persona` stable demo slots; `app_user` | Not production-suitable; slot can be renamed/reused | Immutable person/account mapping; close old grants on personnel change | 2 |
| Authentication assurance | Demo password/local sessions | Prototype only | Verified identity, SSO/MFA, recovery and session revocation | 2 |
| Grant lifecycle | `role_grant.effective_from/effective_to/status` | Partial | Add requester/approver/issuer/revocation/reason/policy version | 3 |
| SoD evaluation | `RbacEngine._sod_hit` | Returns only first hit | Evaluate and record all applicable conflicts | 3 |
| Scope reference integrity | `scope_type` + free `scope_code` | No direct FK; facility grant treated broadly | Validated scope entity and exact facility containment | 3 |
| Delegation | README identifies not built | Missing | Constrained subset linked to source grant | 3 |
| Clinical eligibility | Profile license fields; guardrail specification | Not enforced by RBAC | Effective source-backed eligibility at protected transaction | 4 |
| Compliance exception | Guardrail documents and DDL | Designed | Keep separate from authorization elevation | 4 |
| Break-glass | SYS_ADMIN standing waiver only | Unsafe target model | Step-up, finite event, exact bundle, audit, expiry and review | 4 |
| Authorization audit | `rbac_decision_log` | Minimal fields | Correlation, policy, grant, context, eligibility and elevation references | 3/4 |
| Migration/shadow mode | Not implemented | Missing | Additive migration, decision comparison and rollback | 5 |

## 2. Part 1 risks and controls

| Risk | Severity | Control/containment | Target part |
|---|---|---|---:|
| Governance language is mistaken for approved hospital policy | Critical | Prominent status labels and named approval evidence required | 1 |
| Removing SYS_ADMIN clinical access without continuity design disrupts emergencies | Critical | Approve break-glass policy before enforcing removal; implement in controlled phases | 4/5 |
| Current reusable persona slots misattribute historical actions | Critical | Freeze production reuse; migrate to immutable identities; retain historical mapping | 2/5 |
| Broad permissions hide unsafe combinations | High | Decompose `ADT_WRITE`, `SCHED_WRITE`, and `APPROVE` before enforcement expansion | 3 |
| Free-text scope references create orphan or cross-facility access | High | Validated scope references, ancestry tests, default deny | 3 |
| Shift-only restriction blocks legitimate handover or late documentation | High | Separate read/write contexts; approve grace and correction workflows | 1/3 |
| License expiry disables remediation access | High | Separate clinical eligibility from account status | 2/4 |
| Authorization elevation is confused with compliance exception | Critical | Independent records, decisions, approvals, and audit IDs | 4 |
| Policy change cannot be reconstructed | High | Version every policy/grant decision and preserve append-only evidence | 3/5 |

## 3. Part 1 document validation

The Part 1 package must satisfy all of the following before it is committed:

- all current seeded roles appear exactly once in the role-boundary matrix;
- every current permission is represented in at least one current-role entry;
- the existing `BED_CONTROL`/`SCHED_WRITE` conflict is traced;
- proposed `SCHED_PUBLISH` is explicitly mapped as the future decomposition of current `SCHED_WRITE`;
- Unit Manager, Scheduler, Charge, Bed Coordinator, House Supervisor, DON, Staff, HR, Auditor, and System Administrator have explicit allowed/prohibited boundaries;
- role and SoD CSVs parse as RFC 4180-compatible CSV;
- every `BLOCKING` decision has accountable approvers;
- no approval placeholder is marked approved;
- no Part 1 artifact changes runtime code, seed data, database schema, or API behavior.

## 4. Governance acceptance scenarios

| ID | Scenario | Expected governance decision |
|---|---|---|
| GOV-T01 | Unit Manager requests routine patient placement authority | Reject; retain approval/block boundary |
| GOV-T02 | Scheduler requests bed placement to resolve a staffing shortage | Reject normal grant; use operational escalation, not role combination |
| GOV-T03 | Charge Nurse places a patient in their effective assigned unit | Permit in target matrix subject to eligibility, context, and guardrail |
| GOV-T04 | Charge Nurse places in another unit without effective delegation/elevation | Deny |
| GOV-T05 | System Administrator performs routine bed placement | Deny in v2 target |
| GOV-T06 | Staff Nurse performs care assignment | Evaluate under separate `CARE_ASSIGNMENT_WRITE`; never infer `BED_CONTROL` |
| GOV-T07 | Nurse license expires | Block clinical deployment/assignment; retain approved remediation access |
| GOV-T08 | Requester tries to approve own privileged grant | Deny |
| GOV-T09 | Break-glass activator tries to close their own review | Deny |
| GOV-T10 | Authorization engine is unavailable for a high-risk write | Fail according to approved BCP; never silently allow |
| GOV-T11 | Scope references a unit in another facility | Deny |
| GOV-T12 | Compliance exception is approved but user lacks authorization | Deny; exception does not grant permission |
| GOV-T13 | Break-glass grants authorization but staffing rule blocks transaction | Block or follow separately approved compliance exception route |

## 5. Part 1 gate result

| Gate | Result |
|---|---|
| Artifact completeness | PASS when automated repository validation succeeds |
| Technical consistency with current repository | PASS subject to listed prototype debt |
| Runtime impact | NONE — documentation only |
| Governance approval | **PENDING** |
| Authorization to begin production-facing Part 2 changes | **NOT YET GRANTED** |

