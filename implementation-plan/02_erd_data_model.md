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
    NURSING_UNIT { bigint unit_id PK; varchar unit_code UK; bigint department_id FK; bigint unit_group_id FK; varchar unit_name; varchar unit_type; varchar care_setting; varchar capacity_class; int source_bed_count; int resource_capacity; int licensed_capacity; boolean is_bedded; varchar dq_flag; date effective_from; date effective_to; varchar status }
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

**unit_group** *(care-setting/service-line grouping — every unit has one)*
| Attribute | Type | Notes |
|---|---|---|
| unit_group_id | PK | |
| department_id | FK | |
| name | varchar | `EMERGENCY`, `PERIOPERATIVE`, `CRITICAL CARE`, `ACUTE GENERAL CARE`, `SPECIALIZED & DIAGNOSTIC`, `SECURE CARE`, `SUPPORT & ADMINISTRATIVE SERVICES` |
| care_setting | enum | INPATIENT_WARD / CRITICAL_CARE / EMERGENCY / PERIOPERATIVE / AMBULATORY / DIAGNOSTIC / SUPPORT |

**nursing_unit** *(43 care areas. Patient-placeable = 19; inpatient-licensed = 14 incl. DQ-1a pending. See `06` DQ-10/12.)*
| Attribute | Type | Notes |
|---|---|---|
| unit_id | PK | |
| unit_code | UK | stable identity (`W3A`, `ICU-MAIN`, `ED-RESUS`, `UCC`, …) |
| department_id | FK | owning department (UCC re-parented to Emergency) |
| unit_group_id | FK | required |
| unit_name | varchar | clean display name (prefixes stripped) |
| unit_type | enum | WARD / SECURE_WARD / ICU / HDU / LDR / ED / UCC / OR / PACU / CLINIC / DIAGNOSTIC / PROCEDURE / THERAPY / SUPPORT |
| care_setting | enum | mirrors unit_group domain |
| **capacity_class** | enum | INPATIENT_LICENSED / ED_STRETCHER / PACU_BAY / OR_TABLE / PROCEDURE_ROOM / AMBULATORY_CHAIR / SUPPORT |
| source_bed_count | int | raw CSV `Bed` (nullable if blank) |
| resource_capacity | int | count for that class; 0 for SUPPORT |
| **licensed_capacity** | int | = resource_capacity only when `INPATIENT_LICENSED`; else 0. Facility **281** (or **267** excl. DQ-1a). Never 515/524. |
| is_bedded | boolean | true for inpatient + ED stretcher + PACU |
| dq_flag | varchar | e.g. DQ1A_PENDING, DQ12_REPARENT |
| effective_from / effective_to | date | version the row |

**room**, **bed**
| Attribute | Type | Notes |
|---|---|---|
| room_id / bed_id | PK | auto-provisioned in Wave P2 |
| room_number / bed_number | varchar | generated; see numbering assumption below |
| bed_class | enum | PRIVATE/SHARED/ISOLATION |
| care_features | set | TELEMETRY / VENTILATED / NEG_PRESSURE / BARIATRIC |
| is_licensed | boolean | counts toward licensed capacity |
| is_operative / bed_status | enum | operational + lifecycle: READY/RESERVED/OCCUPIED/CLEANING/OUT_OF_SERVICE/BLOCKED |

> **Numbering assumption:** CSV has unit-level counts only, and they are mixed-class (DQ-10). In Bed-registry mode provision `bed` rows **only** for `INPATIENT_LICENSED` (optional ED/PACU pools). Numbering is synthetic until the physical audit (Wave P2).

### Workforce / accountability domain (consumed from HR + HNWMS, mirrored here for RBAC)

**person** (master = HR/HNWMS Staff Nurse Master Data) · **org_node** (reporting tree, self-referencing) · **workforce_position** (DON, ADON, NURSING_OPS, WORKFORCE_MGR, EDUC, QUALITY, INFORMATICS, UNIT_MANAGER, CHARGE_NURSE, TEAM_LEADER, STAFF_NURSE, NURSING_ASSISTANT; `position_level` L1–L7) · **assignment** (bridge: person+position scoped to FACILITY/DEPARTMENT/UNIT with effective dates).

### Encounter / ADT domain (owned by EMR, mirrored/consumed)
**encounter** (links to current `nursing_unit`) · **bed_occupancy** (bed+encounter+time window) · **bed_state_log** (immutable audit of bed lifecycle).

---

## 3. Cross-cutting rules
- Natural keys (`facility_code`, `department_code`, `unit_code`, `position_code`, `room/bed composite`) are UNIQUE and never reused after soft-delete.
- All changes effective-dated; history preserved; no destructive deletes.
- FK integrity enforced; assignment scope_id must reference a real location node.
- `licensed_capacity` ≥ 0, **only** for `capacity_class=INPATIENT_LICENSED`, and consistent with the inpatient rollup (281/267 — not mixed-class 515).
- Full schema DDL: `artifacts/ddl_schema.sql`.
