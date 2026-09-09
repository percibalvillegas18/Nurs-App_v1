# Compliance Guardrail Layer — Rules Data Model & ERD

Entity/attribute spec for the guardrail engine. Runnable DDL in `artifacts/ddl_compliance_engine.sql`. This is a **decision/evaluation** model layered on top of the HNWMS transactional modules — it does not duplicate Staff Master, license, credential, competency, schedule, or leave data.

---

## 1. ERD (Mermaid)

```mermaid
erDiagram
    compliance_rule ||--o{ compliance_rule_scope : applies_to
    compliance_rule ||--o{ compliance_rule_parameter : tuned_by
    compliance_rule ||--o{ evaluation_rule_result : evaluated_in
    compliance_rule ||--o{ guardrail_exception_request : bypass_request
    evaluation_run ||--o{ evaluation_rule_result : produces
    evaluation_run ||--o{ guardrail_exception_request : may_trigger
    guardrail_exception_request ||--o{ guardrail_exception_approval : approvals
    compliance_rule_parameter ||--o{ working_calendar_adjustment : seasonal

    compliance_rule { bigint rule_id PK; varchar rule_code UK; varchar rule_category; varchar rule_subcategory; varchar rule_name; text rule_description; varchar legal_reference; date effective_date; date expiry_date; varchar severity_default; varchar default_action; boolean exception_allowed; boolean audit_required; boolean active; varchar owner_role }
    compliance_rule_scope { bigint id PK; bigint rule_id FK; varchar scope_type; varchar scope_value }
    compliance_rule_parameter { bigint id PK; bigint rule_id FK; varchar param_key; numeric param_value; varchar param_unit; numeric warn_value; date effective_from; date effective_to }
    working_calendar_adjustment { bigint id PK; varchar adj_type; date start_date; date end_date; numeric daily_hour_limit; numeric weekly_hour_limit; varchar apply_group; boolean active }

    eligibility_snapshot { bigint id PK; bigint staff_id; boolean employment_active; boolean license_valid; date license_expiry; boolean credentials_valid; boolean competency_valid; boolean mandatory_training_ok; boolean dept_authorized }
    shift_candidate { bigint id PK; bigint staff_id; varchar unit_code; varchar shift_type; date shift_date; time start_time; time end_time; boolean is_overtime; varchar status }
    leave_request_candidate { bigint id PK; bigint staff_id; varchar leave_type; date start_date; date end_date; varchar status }

    evaluation_run { bigint run_id PK; varchar eval_target_type; varchar target_ref; bigint staff_id; varchar overall_verdict; timestamp ran_at }
    evaluation_rule_result { bigint id PK; bigint run_id FK; bigint rule_id FK; varchar rule_code; varchar severity; numeric computed_value; numeric threshold_value; varchar result; text message }
    guardrail_exception_request { bigint exception_id PK; bigint run_id FK; bigint rule_id FK; text reason_required; text risk_assessment; text mitigation; timestamp start_time; timestamp end_time; varchar status }
    guardrail_exception_approval { bigint id PK; bigint exception_id FK; varchar approver; varchar approver_role; int step; varchar decision; text note }

    compliance_audit_log { bigint id PK; timestamp event_time; varchar event_type; varchar actor; varchar rule_code; varchar target_type; bigint staff_id; jsonb before_json; jsonb after_json; text reason }
    employee_compliance_status { bigint id PK; bigint staff_id; date as_of; varchar labor_law; varchar contract; varchar license; varchar competency; varchar overall_status; numeric overall_score }
    shift_compliance_status { bigint id PK; varchar shift_ref; varchar unit_code; date shift_date; varchar staffing_level; varchar overall_status }
    staffing_requirement { bigint id PK; varchar unit_code; varchar shift; date date; int census; numeric acuity; int required_rn; int required_senior_rn; int required_charge; int required_total }
    skill_mix_rule { bigint id PK; varchar unit_code; varchar position_level; int min_required; varchar required_qualification }
```

---

## 2. Entity specs

### 2.1 Master rule catalogue (the spec's `Compliance_Rule_Master`)
**`compliance_rule`** — one row per guardrail. Every field from the spec is covered: Rule_ID, Rule_Code, Rule_Category (LABOR/CBAHI/HOSPITAL), Rule_Name, Description, Legal_Reference, Effective/Expiry date, Employee_Group → via **`compliance_rule_scope`**, Trigger → `trigger` semantics described in the rule (and driven by the evaluation point), Condition/Threshold → via **`compliance_rule_parameter`** + scope, Severity, Action, Approval_Level, Exception_Allowed, Exception_Approver (→ approval matrix, `05`), Audit_Required, Active.

### 2.2 Applicability, parameters, seasonality
- **`compliance_rule_scope`** — which employee groups / departments / units / positions / nationalities a rule covers (e.g. Ramadan rules scoped to Muslim workers per policy; ICU staffing rules scoped to ICU).
- **`compliance_rule_parameter`** — numeric thresholds + separate `warn_value` + effective window. Supports auto-recalculation (Ramadan), policy updates, and tuning **without code**.
- **`working_calendar_adjustment`** — facility/dept-level seasonal windows (Ramadan, public holidays, weekend) that shift daily/weekly hour limits automatically.

### 2.3 Evaluation & decision
- **`eligibility_snapshot`** — a cached read of Staff Master + M3 + M8 state so the engine evaluates fast and consistently at pre-write time.
- **`shift_candidate` / `leave_request_candidate`** — the proposed transaction (draft) being guarded, prior to publish/approval.
- **`evaluation_run`** — one run for a proposed transaction; holds `overall_verdict` (ALLOW/WARN/BLOCK).
- **`evaluation_rule_result`** — per-rule outcome (PASS/WARN/FAIL) with computed vs threshold value and message.

### 2.4 Exceptions ("no bypass by clicking override")
- **`guardrail_exception_request`** — mandatory reason + risk assessment + mitigation, **time-limited** (start/end), status lifecycle PENDING→APPROVED/REJECTED/EXPIRED.
- **`guardrail_exception_approval`** — multi-level approval trail (level of approver depends on rule severity).

### 2.5 Audit & status
- **`compliance_audit_log`** — immutable trail: rule eval, allow/warn/block, exception request/approve/reject, parameter or rule toggles, with before/after JSON and actor/role/source.
- **`employee_compliance_status`** — per-employee, per-domain status + overall score (drives the Employee Compliance indicators in `06`).
- **`shift_compliance_status`** — per-shift domain statuses + overall (drives the Shift Compliance / BLOCKED indicator).

### 2.6 Staffing & skill-mix reference (demand side)
- **`staffing_requirement`** — required RN/Senior RN/Charge/specialty per unit-shift computed from census+acuity+unit type (source: EMR census + M1 plan).
- **`skill_mix_rule`** — minimum count/qualification per position level per unit (feeds CBA-SKILL-001).

---

## 3. Key rules/constraints
- No duplicate staff/license/competency data — engine references module-owned sources via `eligibility_snapshot`.
- Rule thresholds are parameterised & effective-dated; changes are audited.
- Exceptions are time-limited, reason/risk/mitigation-gated, multi-level approved, fully logged.
- Blocking decisions never silently approve; WARN routes to the escalation ladder; everything lands in `compliance_audit_log`.
- Verdict = the strictest applicable result: any BLOCK → BLOCK; else any WARN → WARN; else ALLOW/INFORM.
