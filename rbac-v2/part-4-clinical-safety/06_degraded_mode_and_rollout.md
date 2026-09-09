# Part 4 — Degraded Mode, Migration, and Rollout

## 1. Degraded mode

When authorization, eligibility, credentialing, census/acuity, staffing, attendance, or the guardrail engine is unavailable or stale, the system declares the affected dependency and returns `ERROR`/block for protected writes. It queues the candidate for reevaluation and alerts operators. It never converts missing evidence into compliance.

The continuity route must be visible, finite, attributable, separately authorized, and approved under `GOV-BCP-01`. Break-glass alone does not cure a missing eligibility or guardrail source.

## 2. Additive migration

`clinical_safety_schema.sql` creates only `_v2` shadow tables. It does not modify current compliance, identity, authorization, staffing, scheduling, ADT, or clinical transaction tables.

Migration inventory must reconcile:

- all permissions requiring Part 4 checks;
- HR employment and assignment coverage;
- verified license/credential source and freshness;
- competency/training sources by unit and action;
- agency staff ownership and verification;
- signed staffing, acuity, skill-mix, mandatory-post, and attendance mappings;
- current compliance ruleset versions and legal/clinical approvals;
- existing exception/override records;
- eligible break-glass users, bundles, incident reasons, and notification routes;
- every protected transaction's commit-coupling method.

## 3. Shadow validation

Run Part 4 beside current workflows without changing outcomes. Compare eligibility, rule results, strictest verdict, exception use, and proposed emergency behavior. Every unexplained high-risk difference is blocking. Test real operational scenarios with de-identified controlled data and named clinical owners.

## 4. Rollout prerequisites

- Parts 1–3 gates and identity/authorization mappings approved;
- every BLOCK-capable rule and parameter clinically/legal validated;
- no invented staffing ratio, acuity threshold, or mandatory post;
- source freshness and degraded-mode limits approved and monitored;
- exception matrices and non-exceptionable controls signed;
- break-glass tabletop and technical drills passed;
- alerts, on-call ownership, independent reviews, and audit retention operational;
- zero unresolved critical/high safety defects and unexplained shadow differences.

## 5. Rollback

Rollback disables Part 4 enforcement through a controlled feature flag and returns to the last approved safe workflow. It revokes active test elevations/exceptions as required and preserves all evidence. Rollback cannot enable shared credentials, standing SoD waivers, invalid licensure, or silent compliance bypass.
