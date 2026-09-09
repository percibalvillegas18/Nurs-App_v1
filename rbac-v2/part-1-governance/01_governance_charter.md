# Part 1 — Governance Charter and Clinical Authorization Boundaries

**Status:** DRAFT COMPLETE — AWAITING ACCOUNTABLE APPROVAL  
**Baseline date:** 2026-09-09  
**Applies to:** HNWMS, Org Directory, Scheduling, ADT/Bed Management, Staff Profile, Compliance Guardrails  
**Does not approve:** Production deployment, real-person migration, P0 bed capacity, or a license/credential override

## 1. Purpose

This charter establishes who owns HNWMS identity and authorization policy, which current clinical boundaries remain binding, how future changes are approved, and what must be proven before Part 2 begins. It converts the RBAC v2 proposal into reviewable governance controls without changing the currently running prototype.

## 2. Binding baseline

The following existing decisions remain in force unless the decision register is formally approved to change them:

1. Unit Manager approves and may block a bed but does not place a patient.
2. Scheduler may publish a roster and read census but must not receive `BED_CONTROL`.
3. Charge Nurse may exercise `BED_CONTROL` only for an effective assigned unit.
4. Bed Coordinator and House Supervisor may exercise facility-level bed control according to operational policy.
5. DON and ADON perform governance, escalation, analytics, and audit oversight; they do not perform routine placement.
6. Staff Nurse self-service and census visibility do not include physical-bed placement.
7. `CARE_ASSIGNMENT_WRITE` and `BED_CONTROL` are separate permissions in the target model.
8. Authorization break-glass and compliance-rule exception are separate workflows; one never implies the other.
9. Unknown identity, permission, scope, resource, context, eligibility, or policy version defaults to deny.
10. The unsigned P0 bed inventory remains outside RBAC v2 approval.

## 3. Required correction to the current prototype

The current seed grants `SYS_ADMIN` the conflicting `BED_CONTROL` and `SCHED_WRITE` permissions and the current SoD rule names `SYS_ADMIN` as a standing waiver. This is acceptable only as identified prototype debt. The RBAC v2 target removes permanent clinical power from System Administrator and permits emergency authority only through an event-scoped, time-limited, independently reviewed elevation.

No code change is made in Part 1 because this change affects clinical continuity and must first receive the approvals recorded under `GOV-RBAC-02` and `GOV-BG-01`.

## 4. Governance principles

- **Real-person accountability:** Production identities are immutable and cannot be reusable job slots.
- **Least privilege:** Roles contain the minimum atomic permissions required for their duty.
- **Validated scope:** Facility, department, and unit references must resolve to active authoritative records.
- **All-conflict SoD:** Every applicable conflict is evaluated; the engine does not stop after the first match.
- **Independent approval:** A requester cannot approve their own grant, delegation, credential, exception, or emergency review.
- **Effective dating:** Grants, assignments, credentials, delegation, and elevation have explicit start/end lifecycle controls.
- **Separate states:** Account, employment, credential, and clinical eligibility statuses are not collapsed into one field.
- **Transaction-bound decisions:** High-risk checks occur immediately before the protected write.
- **Versioned policy:** Every authorization decision records its policy version and matched evidence.
- **Append-only evidence:** Operational actors cannot modify their own authorization or clinical decision history.
- **No silent bypass:** Every override is attributable, finite, visible, and reviewed.
- **No production demo access:** Shared credentials and public demonstration account lists are prohibited.

## 5. Authority and accountability

| Governance domain | Accountable owner | Required consulted owners | Minimum evidence |
|---|---|---|---|
| Nursing role boundaries | Director of Nursing | Nursing Operations, Unit Managers, Clinical Safety | Signed role-boundary matrix |
| Identity and authentication | CIO/IT Security | HR Data Owner, Privacy, Application Owner | Identity source decision and authentication assurance standard |
| Person/employment data | HR Data Owner | Nursing Administration, Payroll, Privacy | Authoritative identifier and joiner/mover/leaver workflow |
| License/credential state | HR/Credentialing | DON, Nursing Education, Clinical Safety | Verification source, freshness, expiry and suspension policy |
| Bed and ADT permissions | Nursing Operations | Bed Management, ADT, DON, Clinical Safety | Workflow/permission mapping and negative tests |
| Scheduling permissions | Workforce Management | Unit Managers, DON, HR | Draft/review/publish responsibility mapping |
| SoD catalogue | Information Security | DON, Internal Audit, Application Owner | Approved conflict catalogue and exception prohibition |
| Delegation policy | DON | HR, Security, Nursing Operations | Delegable subset, duration, approval and review |
| Break-glass policy | DON | Risk/Quality, Security, IT Operations, Clinical Safety | Eligible roles, bundles, duration, alerts and review SLA |
| Compliance rules/exceptions | DON and Quality | HR, Nursing Operations, Legal/Compliance | Signed rules, parameters, approvers and degraded-mode policy |
| Audit retention/access | Internal Audit/Legal | Privacy, Security, Quality | Retention, access, legal hold and export policy |

## 6. Change-control workflow

1. Requester submits a change with business reason, affected roles/permissions/scopes, clinical risk, and desired effective date.
2. Application Owner performs technical impact and dependency analysis.
3. Clinical Safety and Security classify risk and identify required testing.
4. Accountable owner approves, rejects, or returns with conditions.
5. A second authorized person implements the versioned policy change.
6. Automated positive, negative, scope, SoD, audit, and rollback tests run.
7. Change is deployed through the approved release process.
8. Post-change review confirms expected decisions and absence of unexpected access.

Emergency changes follow the approved emergency-change process, remain time-limited where possible, and require retrospective review. Direct database editing of roles, permissions, grants, SoD rules, delegations, or elevation is prohibited in production.

## 7. Access review cadence

Recommended minimum controls, pending approval:

- privileged grants: monthly review;
- all active grants: quarterly recertification;
- joiner/mover/leaver reconciliation: daily automated comparison plus exception queue;
- dormant accounts: monthly review;
- expiring licenses/credentials: daily evaluation with staged alerts;
- delegations: daily active/expired reconciliation;
- break-glass: immediate alert, review within 24 hours, monthly trend review;
- role/permission and SoD catalogue: quarterly and after material workflow change.

## 8. Part 1 completion definition

Part 1 is technically complete when all artifacts exist and validate. It is governance-approved only when:

- all `BLOCKING` decisions in `04_decision_register.md` are signed;
- the role and SoD CSVs are approved without unresolved clinical ambiguity;
- every current permission is mapped to an accountable owner;
- the prototype conflicts and migration risks are accepted with an owner and target part;
- the acceptance catalogue is approved by DON, Security, Clinical Safety, HR, and Application Owner.

