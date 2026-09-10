# Repo Health Check & Analysis — Nurs-App_v1

**Date:** 2026-09-10
**Scope:** whole repo at `20736b3` (Phase 6: RBAC v2 shadow-mode integration)
**Method:** full test/validator run, live smoke test of the org-directory app, static review
of Python/SQL/JS, cross-check of RBAC v1 ↔ v2 ↔ Part 1 governance catalogue.

---

## Verdict

The **application works** and the **security posture is genuinely good** (parameterized SQL
everywhere, CSRF-safe POST auth, PBKDF2-120k, rate limiting, hardened cookies + security
headers). All 4 RBAC v2 governance-gate validators and all 3 acceptance scripts **PASS**.

But there are **three functional blockers** that would stop the next phase:

| # | Severity | Finding |
|---|---|---|
| 1 | **Blocker** | Shadow-mode cutover is in a **circular deadlock** — divergence can never reach 0 because the only code that fixes the divergences is the cutover script, which refuses to run until divergence is 0. |
| 2 | **Blocker** | `python3 seed.py` (the documented quickstart) **crashes** unless `DEMO_MODE` is set. |
| 3 | **Blocker** | `tests/test_shadow_integration.py` — **6/6 tests fail** on pytest ≥ 8 (nose-style `setup`), giving a false red on the Phase 6 gate. |
| 4 | High | v2 permission catalogue can express only **1 of 10** approved SoD rules (17 of 18 required permissions missing). |
| 5 | Medium | `/api/auth/accounts` is unauthenticated and, in demo mode, **publishes the shared password** + full staff roster. |
| 6 | Low | No CI (`.github` absent); `pytest rbac-v2/` collects **0 tests** (script-style `main()` files) — a green-looking no-op. |
| 7 | Low | Two already-applied patch files (~208 KB) committed at repo root; `rbac/engine_v2.py` duplicated byte-for-byte. |

---

## 1. BLOCKER — Shadow cutover deadlock

**Evidence (live, against a freshly seeded + migrated DB):**

```
GET /api/rbac/evaluate?permission=BED_REQUEST&resource_type=UNIT&resource_code=W3A
→ {"allow": true, ..., "shadow_mode": true}

GET /api/rbac/shadow/status
→ {"total_decisions": 1, "total_divergences": 1, "divergence_rate": 0.0}
```

Running the 16 canonical scenarios through `ShadowRbacAdapter`:

```
10 of 16 diverge (62.5%) — every one: v2_decision=DENY, v2_reason_code=ACCOUNT_NOT_ACTIVE
  v1_allow=1 | demo.slot.charge.w3a  BED_CONTROL W3A      → ACCOUNT_NOT_ACTIVE
  v1_allow=1 | demo.slot.um.gens     APPROVE     W3A      → ACCOUNT_NOT_ACTIVE
  ... (all 10 ALLOW cases; the 6 DENY cases agree)
```

**Root cause chain:**

1. `migrations/008_seed_v2.py` creates the 49 persona accounts as `PENDING_VERIFICATION`
   (deliberate — the `identity_account_v2` CHECK requires `email` + `email_verified_at` for
   an ACTIVE HUMAN account, and legacy demo personas have no email). A comment in the seed
   says: *"The cutover script adds placeholder emails and promotes to ACTIVE."*
2. `rbac/engine_v2.py:66` denies any evaluation whose account is not `ACTIVE` →
   `ACCOUNT_NOT_ACTIVE`.
3. `rbac/cutover_v2.py` has `MAX_DIVERGENCE_RATE = 0.0` and **aborts before** the
   account-activation step if the rate is above it.

So: accounts can only be activated by cutover → cutover requires 0 divergences → divergences
are 100% caused by inactive accounts. **The gate is unreachable without `--force`**, and
`--force` skips the safety check entirely — which is the one thing the gate exists to enforce.

**Recommended fix** (any one of these; #1 is cleanest):

1. **Split cutover into two phases.** Phase A = idempotent *identity activation*
   (placeholder `{persona_code}@migrated.local` + `email_verified_at`), runnable any time,
   independent of the divergence gate. Phase B = the divergence gate + policy flip. This
   matches the seed's own documented intent.
2. Seed the accounts ACTIVE at migration time with placeholder emails, and treat email
   verification as a separate Part 2 identity-lifecycle task.
3. Have the shadow adapter evaluate v2 against a *projected* post-activation state so the
   comparison measures policy equivalence, not migration plumbing.

Also worth fixing while in there: `divergence_rate` uses `rbac_decision_log` as denominator,
which mixes **SIMULATED** dry-run evaluations (`GET /api/rbac/evaluate`) with **ENFORCED**
ones — the gate should count only ENFORCED decisions.

## 2. BLOCKER — `seed.py` crashes without `DEMO_MODE`

```
$ python3 seed.py
  File "org-directory/seed.py", line 519, in main
    salt, hashed = hash_password(DEMO_PASSWORD)
AttributeError: 'NoneType' object has no attribute 'encode'
```

`um.DEMO_PASSWORD` is `None` unless `DEMO_MODE` is truthy; `seed.py` hashes it
unconditionally. `org-directory/README.md` and the root `README.md` both document
`python3 seed.py` with no env var. **Every fresh clone fails at step 1.**

Fix: either gate the seeding on `DEMO_MODE` (create accounts with random passwords and print
them, or skip account creation with a warning), or `sys.exit` with a clear message telling the
operator to set `DEMO_MODE=1`. Update both READMEs either way.

## 3. BLOCKER — `tests/test_shadow_integration.py` fails on pytest ≥ 8

```
6 failed, 24 passed   (pytest 9.1.1)
AttributeError: 'TestShadowAdapter' object has no attribute 'db_path'
```

The class defines `def setup(cls)` — the **nose-style** setup method, which pytest removed in
8.0. It is never called, so `db_path` is never assigned. **The logic is fine**: invoking the
setup manually makes all 6 tests pass:

```
PASS: v1 result unchanged through shadow adapter
PASS: shadow disabled skips v2 correctly
PASS: identity mapping resolved → 5ddff0c6-03bd-4de4-8f72-103adcab02ef
PASS: All 16 scenarios passed through shadow adapter
PASS: divergence report structure valid (rate=0.0, divergences=10)
PASS: grants passthrough (2 grants, 6 permissions)
```

Fix: rename `setup` → `setup_class` (or use a pytest fixture). Two secondary fragilities in
the same file:

- It **copies the live** `org-directory/data/org_directory.db` (gitignored). On a clean clone
  it raises `RuntimeError: Live database not found … Run seed.py first.` Tests should build
  their own DB from `schema.sql` + migrations, like `rbac-v2/part-2-identity` does.
- Unused imports `os`, `subprocess` (also flagged by ruff).

`tests/test_security_fixes.py` — **24/24 pass**. Note it reloads `um` and mutates `DEMO_MODE`
in `os.environ`, so it is order-dependent; it passes today but is fragile under `pytest -p xdist`.

## 4. HIGH — v2 can express 1 of 10 approved SoD rules

`rbac-v2/part-1-governance/03_sod_catalog.csv` is the approved catalogue: **10 SoD rules**.
`migrations/008_seed_v2.py` copies only the single v1 rule (`BED_CONTROL` / `SCHED_WRITE`),
so `sod_rule_v2` contains exactly one row: `SOD-MIG-1`.

The other 9 need 17 permissions that **do not exist** in the v2 catalogue:

```
v2 permissions today (11):
  ADT_WRITE ANALYTICS_READ APPROVE AUDIT_READ BED_BLOCK BED_CONTROL BED_READ
  BED_REQUEST ORG_READ ORG_WRITE SCHED_WRITE

required by the Part 1 catalogue but missing (17):
  AUDIT_ADMIN BREAK_GLASS_ACTIVATE BREAK_GLASS_REVIEW CREDENTIAL_SUBMIT
  CREDENTIAL_VERIFY DELEGATION_APPROVE DELEGATION_REQUEST EXCEPTION_APPROVE
  EXCEPTION_REQUEST GRANT_ACTIVATE GRANT_APPROVE GRANT_REQUEST
  LICENSE_EXCEPTION_APPROVE OPERATIONAL_WRITE SCHED_APPROVE SCHED_PREPARE
  SCHED_PUBLISH
```

This is a **gate blocker for Part 3/4 sign-off and for cutover**: you cannot claim v2 parity
while 90% of the approved SoD catalogue is inexpressible. Note also that
`SOD-BED-SCHED-001` is marked *"PENDING CHANGE — BLOCKING"* and is specified against
`SCHED_PUBLISH`, not the v1 `SCHED_WRITE` that got migrated — the migrated rule is not the
approved rule.

## 5. MEDIUM — public endpoint leaks roster + demo password

`PUBLIC_API = {"/api/health", "/api/auth/login", "/api/auth/accounts"}` — `/api/auth/accounts`
needs no session, and when `DEMO_MODE` is on the response contains:

```json
{"accounts": [{"username": "bader.al.dossary", "display_name": "Bader Al-Dossary",
               "job_title": "ADT Clerk, Inpatient", "category": "ADT clerks"}, …],
 "demo_password": "Demo@2026"}
```

Verified live. That is the full 49-person staff roster (usernames, real-looking names, job
titles) **and** the credential to log in as any of them, handed to any anonymous caller.
Even in demo mode this is the kind of thing that gets copied into production.

Fix: drop `/api/auth/accounts` from `PUBLIC_API` (require a session), and expose
`demo_password` only on the authenticated `/api/auth/me`.

## 6. LOW — CI absent; `pytest rbac-v2/` is a silent no-op

- No `.github/`, no CI config, no test-runner config file, no pinned requirements. Nothing runs
  the suite automatically.
- `rbac-v2/part-{2,3,4}` tests are **script-style `main()` functions**, not pytest-collectable,
  despite being named `test_*.py`. `pytest rbac-v2/` → `no tests ran` (exit code 5) — a CI step
  would look green while asserting nothing. They must be run as
  `cd rbac-v2/part-N-* && python3 test_*.py` (all 3 pass when run that way).

Suggested minimum CI job:

```bash
DEMO_MODE=1 python3 org-directory/seed.py
python3 migrations/migrate.py
python3 migrations/008_seed_v2.py org-directory/data/org_directory.db
python3 -m pytest tests/ -v
for d in rbac-v2/part-1-governance rbac-v2/part-2-identity \
         rbac-v2/part-3-authorization rbac-v2/part-4-clinical-safety; do
  (cd $d && for f in *.py; do python3 $f || exit 1; done)
done
```

## 7. LOW — repo hygiene

- **`0001-Fix-16-security-review-findings-…patch` (49 KB)** and
  **`phase6-integrate-rbac-v2.patch` (158 KB)** are committed at the repo root.
  `git apply --check --reverse phase6-integrate-rbac-v2.patch` succeeds → **its content is
  already applied** and is now just 208 KB of duplicated history. Move to `docs/archive/` or
  delete; git history is the record.
- **`rbac/engine_v2.py` is byte-identical to `rbac-v2/part-3-authorization/engine_v2.py`.**
  Pick one source of truth (suggest: `rbac-v2/` is the spec-owned copy, `rbac/` is the deployed
  copy, and add a CI check that they match) or they will drift.
- `ruff check .` → 85 findings (26 unsorted imports, 14 non-executable shebangs, 9 blind
  `except Exception`, 7 unused imports, 3 `try/except: pass`). No correctness issues; worth a
  cleanup pass and a `ruff` config before the code grows.
- No `requirements.txt` / `pyproject.toml`. Everything is stdlib (`pytest` is not even
  installed in a clean environment), which is nice, but CI needs to know that.

---

## What is working well (no action)

- **SQL injection:** zero. Every `execute()` in `org-directory/`, `rbac/`, `rbac-v2/` uses bound
  parameters — no f-string, `%`, `.format`, or concatenated SQL anywhere.
- **CSRF:** `um.request_token(headers, require_header=True)` rejects cookie-only auth for every
  state-changing request (POST/DELETE); correct pattern.
- **Passwords/sessions:** PBKDF2-SHA256 @ 120 000 rounds, `secrets.compare_digest`, per-user
  salt, `secrets.token_urlsafe` session tokens, 12 h expiry, `HttpOnly` + `SameSite` (+ `Secure`
  when `X-Forwarded-Proto: https`).
- **Headers:** `nosniff`, `X-Frame-Options: DENY`, CSP, HSTS, `Cache-Control: no-store`.
- **Uploads:** extension allowlist, 8 MB cap, SHA-256 checksum, path confined to `data/uploads`,
  Content-Disposition sanitized.
- **RBAC v2 governance gates:** `validate_part1/2/3/4.py` and
  `test_identity_schema.py` / `test_authorization_v2.py` / `test_clinical_safety.py` all PASS,
  including append-only evidence, idempotent decisions, break-glass controls, and the
  authorization/exception separation.
- **Data-safety guardrails are honoured in code:** `/api/summary` reports
  `signoff: UNSIGNED`, `walk_status: NOT_WALKED`, and carries the warning
  *"Do not report 515/524 as licensed beds"*; `licensed_inpatient` is **281** (267 if
  `ICU-EXT-2` merged), with `pending_dq: [PLASTER-2, ICU-EXT-2, ED-NAV-2]`.
- **App boots and serves correctly**: health, login, `/api/auth/me`, `/api/rbac/me`,
  `/api/rbac/evaluate`, `/api/summary`, `/api/rbac/shadow/status` all verified live on 8080.
- **Rollbacks exist** for migrations 002–008, and `migrate.py` has `--status`, `--rollback`,
  `--backup`.

---

## Suggested order of work

1. **#2** seed.py / README (5 min, unblocks every new clone).
2. **#3** rename `setup` → `setup_class` and make the tests self-seeding (unblocks the honest
   signal on the Phase 6 gate).
3. **#1** split cutover into activation + gate phases (unblocks the v2 rollout path).
4. **#5** un-public `/api/auth/accounts`.
5. **#4** extend the v2 permission catalogue to cover the 10-rule SoD catalogue
   (governance-owned — needs a Part 1/3 decision, not just code).
6. **#6** add CI; **#7** clean up patches + duplicated engine.
