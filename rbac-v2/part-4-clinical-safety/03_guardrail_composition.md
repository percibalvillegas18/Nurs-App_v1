# Part 4 — Compliance Guardrail Composition

## 1. Authoritative rule model

Part 4 reuses the rule domains, parameters, effective dates, staffing requirements, skill-mix requirements, evaluations, exceptions, and audits defined in `compliance-guardrails/`. The shadow adapter records only stable rule references and immutable result evidence for the safety decision.

No threshold in the test fixtures is hospital policy. Labor-law references, CBAHI edition, staffing ratios, acuity method, mandatory posts, warning bands, and exceptionability must be legally/clinically validated and signed before activation.

## 2. Transaction binding

Each guardrail evaluation binds to:

- evaluation target type and stable target reference;
- canonical transaction fingerprint;
- staff and validated unit;
- exact ruleset version;
- input/source capture time and validity deadline;
- one result for every applicable rule;
- strictest overall verdict.

Changing staff, shift, unit, census, acuity, attendance state, roster membership, or another material input produces a new fingerprint and requires reevaluation.

## 3. Strictest result

| Rule result | Composite treatment |
|---|---|
| `PASS` / `INFORM` | Continue |
| `WARN` | Final `WARN`; route to approved escalation/review |
| `FAIL` with `BLOCK` | Block unless that exact result has an effective, permitted, fully approved guardrail exception |
| Missing/stale/error | `ERROR` and fail according to approved BCP; never silent allow |

Staffing evaluation must combine census, approved acuity, required nursing hours/posts, skill mix, competencies, scheduled availability, attendance state, working hours/rest, and source freshness. A patients-per-nurse ratio alone is insufficient.

## 4. Commit coupling

The caller performs the safety evaluation server-side immediately before commit and stores the safety decision ID on the protected write in the same consistency boundary. If the candidate fingerprint changes or the decision expires, the write is rejected and reevaluated.

## 5. Monitoring

Alert on blocks, repeated warnings, stale feeds, rule-engine errors, exceptions, break-glass activation/use, prohibited elevation attempts, expiry, and overdue review. Dashboards must preserve least privilege and avoid patient-identifiable workforce views.
