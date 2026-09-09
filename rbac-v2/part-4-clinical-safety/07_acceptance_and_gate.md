# Part 4 — Acceptance Catalogue and Gate

## 1. Automated acceptance

- schema is idempotent, additive, and foreign-key valid;
- unknown, failed, or stale eligibility blocks protected clinical action;
- expired/suspended/revoked license blocks while remediation permission can remain available;
- agency staff receive identical eligibility enforcement;
- guardrail result uses strictest applicable outcome;
- changed transaction fingerprint invalidates prior evaluation/exception;
- every blocking rule requires its own permitted effective exception;
- non-exceptionable results and self-approval are rejected;
- guardrail exception never creates authorization;
- break-glass requires active human identity, linked staff, step-up authentication, approved bundle, exact scope, and bounded duration;
- prohibited administrative/security permissions cannot enter a break-glass bundle;
- break-glass expiry/revocation is enforced at decision time;
- break-glass cannot bypass eligibility or guardrails;
- activator cannot review their own event;
- decisions, rule results, exception approvals, uses, reviews, and alerts are append-only;
- Parts 1–3 regression validators pass.

## 2. Required operational acceptance

- signed clinical scenarios cover license, competency, training, unit authorization, hours/rest, staffing, skill mix, census/acuity, attendance state, agency worker, and source failure;
- all compliance `RG/WH/OT/LV/CT/LC/ST/EX/DS` scenarios applicable to deployed modules pass;
- high-risk writes fail safely when any dependency is stale/unavailable;
- no partial write occurs after `WARN`, `BLOCK`, or `ERROR` without the exact approved workflow;
- decision ID and transaction fingerprint are coupled to the committed write;
- break-glass activation, notification, use, expiry, revocation, review, overdue escalation, and investigation drill passes;
- monitoring, latency, availability, privacy, retention, and legal-hold requirements pass.

## 3. Gate status

| Gate | Result |
|---|---|
| Part 4 technical package | **PASS when `validate_part4.py` succeeds** |
| Runtime impact | NONE |
| Clinical/licensure policy | `[PENDING]` |
| Compliance rule/parameter approval | `[PENDING]` |
| Staffing/acuity/skill-mix approval | `[PENDING]` |
| Exception approval matrix | `[PENDING]` |
| Break-glass policy and drill | `[PENDING]` |
| Degraded-mode/BCP drill | `[PENDING]` |
| Production shadow comparison | `[NOT RUN]` |
| Runtime Part 4 cutover | **NOT AUTHORIZED** |

## 4. Accountable acceptance

DON, Nursing Operations, Clinical Safety/Quality, HR/Credentialing, Nursing Education, Legal/Privacy, Risk/Internal Audit, IT Security, IT Operations, and each source-system owner must sign their respective controls. No placeholder is approval evidence.
