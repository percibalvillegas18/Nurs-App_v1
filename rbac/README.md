# HNWMS RBAC module

**Status:** APPROVED and applied 2026-09-09.

Live engine: `rbac/engine.py` via Org Directory `/api/rbac/evaluate`.  
People log in on Org Directory (password `Demo@2026`), complete **My profile**, and attach recommended files. That is user management, not this module.

## RBAC is not user management

| This module has | This module does **not** have |
|---|---|
| Roles, permissions, location-scoped grants | SSO / MFA / Active Directory |
| Demo **people slots** you can rename | Full Staff Master (all nurses) |
| Login / logout + My profile + recommended files (UM) | Invite workflow from HR |
| SoD (`BED_CONTROL` × `SCHED_WRITE`) | Delegation / auto-escalation ladder (not built) |
| Decision engine + audit of evaluates |  |

**People** = every *system user* HNWMS needs to log in.  
**Staff Master** = the full nurse roster (still empty on purpose).

`persona_code` is a **stable slot** (`demo.slot.charge.w3a`). Change `display_name` to the real employee later; grants stay on the slot.

## Applied rules (in the engine)

### 1. Unit Manager does not assign beds
UM **approves** and may **block** (isolation / OOS). Placement is Charge (own unit) or Bed Coordinator / House Supervisor (facility).

### 2. Scheduler never has `BED_CONTROL`
Roster and beds are SoD. Scheduler **may** read census. Only `SYS_ADMIN` may hold both, as break-glass, audited.

### 3. Charge is unit-scoped for control, house-wide for sight
Fatimah (W3A) sees ICU occupancy and **cannot** place an ICU bed.

```
allow = role has permission
      AND grant scope contains the resource
      AND no BED_CONTROL × SCHED_WRITE on the same person (unless SYS_ADMIN)
```

HNWMS / ADT / Scheduling **must** call `RbacEngine.evaluate` (or `GET /api/rbac/evaluate`) before bed control or roster publish. A 403 is the correct deny.

## Demo people (system-user slots)

Seeded in Org Directory → **People**. Groups:

- Leadership (Hospital Director, DON, ADON)
- Operations (House Supervisor, Bed Coordinator)
- Workforce (Workforce / Education / Quality / Informatics managers)
- System (Org Admin, Sys Admin, HR, Audit)
- Unit managers (4 departments + Pediatrics + Maternity)
- Schedulers (4 departments)
- ADT clerks (4 departments)
- Charge nurses (every operational bedded unit + OR; not `ICU-EXT-2`)
- Self-service **sample** only (one team lead, one staff nurse, one assistant on W3A)

Rename anyone on the People screen when the real person is known. Rename requires `ORG_WRITE`.
