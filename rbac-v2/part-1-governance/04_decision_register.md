# Part 1 Governance Decision Register

**Status rule:** `PENDING` is not approval. A decision becomes effective only when the accountable approver, decision, conditions, and date are recorded. `BLOCKING` decisions prevent production activation of the affected control.

| ID | Priority | Decision | Recommended default | Accountable approvers | Status |
|---|---|---|---|---|---|
| GOV-RBAC-01 | BLOCKING | Final role-permission and scope matrix | Adopt `02_role_boundary_matrix.csv` and preserve current bed/roster boundaries | DON + Nursing Operations + IT Security + Application Owner | **PENDING** |
| GOV-RBAC-02 | BLOCKING | Permanent System Administrator clinical permissions and SoD waiver | Remove standing `BED_CONTROL`, `SCHED_WRITE`, `ADT_WRITE`, and clinical `APPROVE`; use event-scoped elevation only | DON + IT Security + Internal Audit | **PENDING** |
| GOV-RBAC-03 | BLOCKING | Atomic permission decomposition | Replace ambiguous `ADT_WRITE`, `SCHED_WRITE`, and `APPROVE` with operation-specific permissions before broad deployment | Workflow Owners + DON + IT Security | **PENDING** |
| GOV-SCOPE-01 | BLOCKING | Facility/department/unit scope authority | Resolve scopes through existing active Org Directory records; wrong-facility and ambiguous ancestry deny | Org Directory Owner + DON + IT Security | **PENDING** |
| GOV-ID-01 | BLOCKING | Production person identifier | HR employee number maps to immutable HNWMS staff/identity subject; no reusable login slot | HR Data Owner + IT Security | **PENDING** |
| GOV-ID-02 | BLOCKING | Production authentication | Hospital SSO preferred; MFA required for privileged/high-risk actions; local auth only by approved exception | CIO/IT Security | **PENDING** |
| GOV-CLIN-01 | BLOCKING | Shift and care-context windows | Clinical write during assigned shift plus configurable grace; read based on assignment/care/approved operational need | DON + Clinical Safety + Privacy/HIM | **PENDING** |
| GOV-CLIN-02 | BLOCKING | License-expiry behavior | Block clinical eligibility while preserving approved remediation/profile access | DON + HR Credentialing + Clinical Safety | **PENDING** |
| GOV-DEL-01 | HIGH | Delegable permissions | Explicit subset only; cannot exceed source grant; no redelegation by default | DON + Nursing Operations + IT Security | **PENDING** |
| GOV-DEL-02 | HIGH | Delegation duration/approval | Exact start/end; manager approval; additional approval for high-risk permissions | DON + HR + IT Security | **PENDING** |
| GOV-BG-01 | BLOCKING | Break-glass eligible identities and permission bundles | Qualified active users only; exclude identity/role/audit/policy/credential administration | DON + Risk/Quality + IT Security | **PENDING** |
| GOV-BG-02 | HIGH | Break-glass maximum duration | Shorter of four hours or declared incident window | DON + Risk/Quality | **PENDING** |
| GOV-BG-03 | HIGH | Break-glass review SLA | Independent review within 24 hours | DON + Quality/Internal Audit | **PENDING** |
| GOV-COMP-01 | BLOCKING | Staffing/acuity/skill-mix authority | Reuse signed HNWMS guardrail catalogue; ratio alone is insufficient | DON + Nursing Operations + Quality | **PENDING** |
| GOV-BCP-01 | BLOCKING | Authorization/eligibility engine degraded mode | Fail closed for high-risk writes; approved, visible, finite continuity route | DON + IT Operations + Risk + Security | **PENDING** |
| GOV-AUD-01 | HIGH | Audit retention/access/tamper evidence | Append-only least-access store with approved retention and legal hold | Legal/Privacy + Internal Audit + Security | **PENDING** |
| GOV-REV-01 | MEDIUM | Access recertification cadence | Privileged monthly; all grants quarterly; JML daily reconciliation | HR + IT Security + Internal Audit | **PENDING** |

## Approval entry template

Complete one entry per decision:

```text
Decision ID:
Decision: APPROVED / REJECTED / APPROVED WITH CONDITIONS
Approved policy/value:
Conditions and expiry (if any):
Accountable approver name and role:
Consulted reviewers:
Effective date:
Next review date:
Evidence/reference:
```

## Part 1 sign-off

| Role | Name | Decision | Date/evidence |
|---|---|---|---|
| Director of Nursing | `[APPROVER]` | `[PENDING]` | `[PENDING]` |
| Nursing Operations | `[APPROVER]` | `[PENDING]` | `[PENDING]` |
| Clinical Safety / Quality | `[APPROVER]` | `[PENDING]` | `[PENDING]` |
| HR / Credentialing | `[APPROVER]` | `[PENDING]` | `[PENDING]` |
| Information Security | `[APPROVER]` | `[PENDING]` | `[PENDING]` |
| IT / Application Owner | `[APPROVER]` | `[PENDING]` | `[PENDING]` |
| Risk / Internal Audit | `[APPROVER]` | `[PENDING]` | `[PENDING]` |

