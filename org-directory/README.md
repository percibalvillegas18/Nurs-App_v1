# Wave P1 — Org Directory

Location + workforce registry for AIGH. Loads the classed seed (`normalized_department_unit.csv`) and the nursing/hospital org chart. **P0 is unsigned; the physical audit has not been walked.** **RBAC is APPROVED and applied** (`../rbac/`).

```bash
python3 seed.py    # sqlite + desk-audit sheets
python3 app.py     # http://0.0.0.0:8080
```

Stdlib only (no pip). APIs under `/api/*` are the consumer contract (ADT / Scheduling / HNWMS).

**User management:** every demo person can log in (password `Demo@2026`), complete profile data, and attach recommended files. This is not SSO/MFA.

Beds are **not** provisioned here (Wave P2). `licensed_capacity` is stored on the unit; ADT `bed` rows wait for a signed walk.
