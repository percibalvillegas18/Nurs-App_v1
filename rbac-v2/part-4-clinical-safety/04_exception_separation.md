# Part 4 — Guardrail Exception Separation

## 1. What an exception does

A guardrail exception permits one otherwise authorized transaction to proceed despite one explicitly exceptionable guardrail result. It is not a role, grant, delegation, break-glass event, license override, or blanket unit waiver.

## 2. Required controls

- exact evaluation and failed rule-result reference;
- exact transaction fingerprint, staff, and unit;
- rule marked exceptionable in the approved ruleset;
- meaningful reason, risk assessment, mitigation, and corrective action;
- finite start/end window no broader than the evaluated event;
- requester cannot approve;
- required number and type of independent approvals;
- approver authorization checked by Part 3 at decision time;
- automatic expiry and immediate revocation;
- new evaluation if any material candidate input changes;
- append-only request, approval, use, revocation, and audit evidence.

## 3. Prohibited uses

The ordinary exception workflow cannot bypass:

- invalid, expired, suspended, revoked, or unverified professional licensure;
- unknown staff identity or inactive employment;
- unavailable/stale eligibility authority;
- missing RBAC authorization;
- identity, audit, role, policy, or credential-verification controls;
- a rule explicitly classified as non-exceptionable.

## 4. Multi-rule behavior

Every blocking rule result requires its own permitted and effective exception. Excepting one staffing result does not erase a separate skill-mix, working-hours, or competency block. Remaining `BLOCK` results still block; remaining `WARN` results still produce `WARN`.

## 5. Approval gate

The repository demonstrates generic independent multi-approval mechanics only. Actual approver roles, required counts, maximum windows, corrective-action SLAs, notification recipients, and non-exceptionable rule classes must be approved by DON, Quality/Clinical Safety, HR/Legal, and Security as applicable.
