# Part 4 — Clinical Eligibility and Source Freshness

## 1. Evidence sources

Eligibility snapshots are derived read-side evidence, not a second Staff Master. Their authoritative inputs are:

| Factor | Authority |
|---|---|
| Active employment and effective assignment | HR Staff Master / Part 2 employment assignment |
| Professional license | HR Credentialing and authoritative licensing evidence |
| Required credentials | Credentialing |
| Unit/specialty competency | Nursing Education / approved competency source |
| Mandatory training | LMS / Nursing Education |
| Department or unit authorization | Nursing Administration with HR assignment |
| Occupational restriction | Occupational Health under approved privacy controls |
| Agency-worker sponsorship and verification | Approved agency governance plus hospital Credentialing |

Agency staff follow the same eligibility gates. `worker_type` distinguishes employees and agency workers, but it never weakens verification.

## 2. Snapshot contract

A snapshot identifies one staff member, target unit, evidence version, source collection time, validity deadline, and each factor as `PASS`, `FAIL`, or `UNKNOWN`. It also records source availability and evidence references without copying sensitive source documents.

For a permission configured to require clinical eligibility:

- any required `FAIL` returns `ELIGIBILITY_BLOCK`;
- any required `UNKNOWN`, unavailable source, or expired snapshot returns `ELIGIBILITY_SOURCE_UNAVAILABLE_OR_STALE`;
- only all required `PASS` values can continue to guardrail evaluation.

The evaluator checks freshness at transaction time. A scheduled background refresh improves readiness but is never the sole enforcement mechanism.

## 3. License behavior

Expired, suspended, revoked, unverified, or source-stale licensure blocks clinical scheduling, deployment, care assignment, and other configured clinical actions. It does not disable the account or prevent approved remediation functions such as profile correction, document submission, HR communication, or education access.

`LICENSE_REMEDIATION` is a distinct non-clinical permission profile and must not include clinical writes.

## 4. Context and assignment

Eligibility is unit-specific and effective-dated. Part 2 employment assignment supplies the authoritative organizational relationship; Part 4 additionally validates required unit authorization, shift/care context when approved, and competency/training evidence for the target. Cross-unit use requires an effective assignment, delegation/elevation where applicable, and new target-unit eligibility.

## 5. Pending policy values

Freshness limits, shift/grace windows, occupational-health handling, credential requirements by unit, agency verification, and remediation permissions require named approval. The repository does not invent those values.
