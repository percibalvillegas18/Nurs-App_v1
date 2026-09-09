# ERD & Data Model — Org Structure, Departments & Bed Capacity

Companion to `01_implementation_plan.md`. Contains the entity/attribute specification, a Mermaid ERD, and the SQL DDL (full runnable schema in `artifacts/ddl_schema.sql`).

---

## 1. ERD (Mermaid)

```mermaid
erDiagram
    FACILITY ||--o{ DEPARTMENT : contains
    DEPARTMENT ||--o{ UNIT_GROUP : organizes
    UNIT_GROUP ||--o{ NURSING_UNIT : contains
    NURSING_UNIT ||--o{ ROOM : contains
    ROOM ||--o{ BED : contains
    NURSING_UNIT ||--o{ BED : owns
    BED ||--o{ BED_STATE_LOG : tracks
    BED ||--o{ BED_OCCUPANCY : occupies
    PERSON ||--o{ ASSIGNMENT : holds
    WORKFORCE_POSITION ||--o{ ASSIGNMENT : grants
    ORG_NODE ||--o{ WORKFORCE_POSITION : defines
    ORG_NODE ||--o{ ORG_NODE : reports_to
    ASSIGNMENT }o--o{ NURSING_UNIT : scoped_to
    ENCOUNTER ||--o{ BED_OCCUPANCY : placed
    ENCOUNTER }o--o{ NURSING_UNIT : located_in

    FACILITY { bigint facility_id PK; varchar facility_code UK; varchar name; varchar region; varchar mrn_prefix; varchar licensor; varchar status }
    DEPARTMENT { bigint department_id PK; varchar department_code UK; bigint facility_id FK; varchar name; varchar department_type; varchar status }
    UNIT_GROUP { bigint unit_group_id PK; bigint department_id FK; varchar name; varchar care_setting; varchar status }
    NURSING_UNIT { bigint unit_id PK; varchar unit_code UK; bigint department_id FK; bigint unit_group_id FK; varchar unit_name; varchar unit_type; varchar care_setting; int licensed_capacity; boolean is_bedded; varchar status }
    ROOM { bigint room_id PK; bigint unit_id FK; varchar room_number; varchar room_type; boolean isolation_capable }
    BED { bigint bed_id PK; bigint unit_id FK; bigint room_id FK; varchar bed_number; varchar bed_class; varchar care_features; boolean is_licensed; boolean is_operative; varchar bed_status }
    BED_STATE_LOG { bigint id PK; bigint bed_id FK; varchar from_state; varchar to_state; timestamp changed_at; bigint changed_by; varchar reason; varchar source }
    PERSON { bigint person_id PK; varchar staff_code UK; varchar name; varchar license_no; varchar status }
    ORG_NODE { bigint org_node_id PK; bigint parent_org_node_id FK; varchar org_code; varchar name; varchar node_type; varchar status }
    WORKFORCE_POSITION { bigint position_id PK; varchar position_code UK; bigint org_node_id FK; varchar title; varchar position_level }
    ASSIGNMENT { bigint assignment_id PK; bigint person_id FK; bigint position_id FK; varchar scope_type; bigint scope_id; date effective_from; date effective_to; varchar status }
    ENCOUNTER { bigint encounter_id PK; bigint patient_id FK; varchar encounter_number UK; bigint current_unit_id FK; datetime admitted_at; datetime discharged_at; varchar status }
    BED_OCCUPANCY { bigint id PK; bigint bed_id FK; bigint encounter_id FK; datetime occupied_from; datetime occupied_until; varchar status }
```

---

## 2. Entity & Attribute Specifications

### Location / operational domain (our system of record)

**facility**
| Attribute | Type | Notes |
|---|---|---|
| facility_id | PK | surrogate |
| facility_code | UK natural | e.g. `HOSP01` |
| name | varchar | Hospital name |
| region / city | varchar | e.g. Riyadh |
| mrn_prefix | varchar | MPI scoping |
| licensor | varchar | licensing authority |
| status | enum | ACTIVE/INACTIVE |

**department** *(4, from CSV column 1)*
| Attribute | Type | Notes |
|---|---|---|
| department_id | PK | |
| department_code | UK | e.g. `EMRG`, `SURG`, `CRIT`, `GENS` |
| facility_id | FK | |
| name | varchar | exact CSV: EMERGENCY & ACUTE CARE, SURGICAL & PERIOPERATIVE SERVICES, CRITICAL CARE & INTENSIVE SERVICES, GENERAL & SPECIALTY SERVICES |
| department_type | enum | BEDDED / NON_BEDDED |

**unit_group** *(care-setting/service-line grouping; normalized from CSV parenthetical prefixes)*
| Attribute | Type | Notes |
|---|---|---|
| unit_group_id | PK | |
| department_id | FK | |
| name | varchar | `ACUTE GENERAL CARE`, `SPECIALIZED & DIAGNOSTIC`, `SUPPORT & ADMINISTRATIVE`; the 3 top service lines act as their own group |
| care_setting | enum | INPATIENT_WARD / AMBULATORY_DIAGNOSTIC / BEDDED_SERVICE_LINE / NON_BEDDED_SUPPORT |

**nursing_unit** *(the 38 bedded + 5 support areas, CSV column 2)*
| Attribute | Type | Notes |
|---|---|---|
| unit_id | PK | |
| unit_code | UK | generated during normalization (`EDRE`,`WARD`,… unique across registry) |
| department_id | FK | owning department |
| unit_group_id | FK | nullable for top-level service-line areas |
| unit_name | varchar | clean display name (prefixes stripped) |
| unit_type | enum | WARD / ICU / ED / OR / PACU / CLINIC / DIAGNOSTIC / SUPPORT / OTHER |
| care_setting | enum | mirrors unit_group |
| **licensed_capacity** | int | = CSV "Bed" (nil for the 5 support rows) |
| is_bedded | boolean | false for support/admin areas |

**room**, **bed**
| Attribute | Type | Notes |
|---|---|---|
| room_id / bed_id | PK | auto-provisioned in Wave P2 |
| room_number / bed_number | varchar | generated; see numbering assumption below |
| bed_class | enum | PRIVATE/SHARED/ISOLATION |
| care_features | set | TELEMETRY / VENTILATED / NEG_PRESSURE / BARIATRIC |
| is_licensed | boolean | counts toward licensed capacity |
| is_operative / bed_status | enum | operational + lifecycle: READY/RESERVED/OCCUPIED/CLEANING/OUT_OF_SERVICE/BLOCKED |

> **Numbering assumption:** CSV has unit-level counts only. In Bed-registry mode beds are provisioned per unit using a configurable bay/room sizing; numbering is synthetic and **must be validated** by physical audit before going live (Wave P2). If the facility already has a room/bed number list, that list supersedes provisioning.

### Workforce / accountability domain (consumed from HR + HNWMS, mirrored here for RBAC)

**person** (master = HR/HNWMS Staff Nurse Master Data) · **org_node** (reporting tree, self-referencing) · **workforce_position** (DON, ADON, NURSING_OPS, WORKFORCE_MGR, EDUC, QUALITY, INFORMATICS, UNIT_MANAGER, CHARGE_NURSE, TEAM_LEADER, STAFF_NURSE, NURSING_ASSISTANT; `position_level` L1–L7) · **assignment** (bridge: person+position scoped to FACILITY/DEPARTMENT/UNIT with effective dates).

### Encounter / ADT domain (owned by EMR, mirrored/consumed)
**encounter** (links to current `nursing_unit`) · **bed_occupancy** (bed+encounter+time window) · **bed_state_log** (immutable audit of bed lifecycle).

---

## 3. Cross-cutting rules
- Natural keys (`facility_code`, `department_code`, `unit_code`, `position_code`, `room/bed composite`) are UNIQUE and never reused after soft-delete.
- All changes effective-dated; history preserved; no destructive deletes.
- FK integrity enforced; assignment scope_id must reference a real location node.
- `licensed_capacity` ≥ 0 and consistent across department/facility rollup for the reconciliation report.
- Full schema DDL: `artifacts/ddl_schema.sql`.
