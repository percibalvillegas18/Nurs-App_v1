# Wave P1 — Org Directory

Location + workforce registry for AIGH. Loads the classed seed (`normalized_department_unit.csv`) and the nursing/hospital org chart. **P0 is unsigned; the physical audit has not been walked.** The live RBAC is a v1 prototype; v2 remains shadow-only pending governance approval.

```bash
# Isolated demo only — explicitly opt in to the shared demo credential.
DEMO_MODE=true python3 seed.py

# Local bootstrap — supply the initial secret out of band; it is not printed.
SEED_PASSWORD='replace-me' python3 seed.py

python3 ../migrations/migrate.py  # applies SQL migrations and v2 seed 008
BIND_HOST=0.0.0.0 python3 app.py  # http://0.0.0.0:8080 (preview/container)
```

Without `DEMO_MODE=true` or `SEED_PASSWORD`, the loader refuses to create a
shared-password database. Stdlib only (no pip). APIs under `/api/*` are the
consumer contract (ADT / Scheduling / HNWMS).

**User management:** the demo loader is not production authentication. Do not
use demo slots, local bootstrap passwords, or the account picker in production;
use the hospital SSO/IdP with MFA and immutable HR-linked identities. The
current v1 runtime is still not SSO/MFA.

Beds are **not** provisioned here (Wave P2). `licensed_capacity` is stored on the unit; ADT `bed` rows wait for a signed walk.
