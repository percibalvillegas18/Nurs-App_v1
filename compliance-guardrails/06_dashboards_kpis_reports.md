# Compliance Dashboards, KPIs & Reports

Consumes `employee_compliance_status`, `shift_compliance_status`, staffing/skill-mix results, and the compliance audit — surfaced in **Module 9 (Analytics & Control Tower)** and routed per role.

## 1. Nursing Director Compliance Dashboard (targets from the spec)
| KPI | Target |
|---|---|
| Labor-law compliance | ≥ 98% |
| Valid nursing licenses | 100% |
| Expired credentials | 0 |
| Mandatory-training compliance | ≥ 95% |
| Unsafe-staffing events | 0 |
| Unauthorized assignments | 0 |
| Excessive-OT cases | Minimize |
| Schedule exceptions | Minimize |
| Contract-expiry alerts | 100% actioned |
| CBAHI workforce compliance | ≥ 95% |
| Critical staffing gaps | 0 |

## 2. Dashboard layers
| Layer | Audience | Content |
|---|---|---|
| Compliance Control Tower | Compliance/quality/audit | Exception backlog & aging, override ratio, blocked counts by rule & unit, risk heat-map |
| Nursing Director / CNO | DON/CNO | KPI table above, workforce compliance %, staffing gaps, license/credential/competency expiry pipelines, OT & exceptions |
| Nursing Manager / Unit | Unit Manager | Unit compliance status, staffing level (GREEN/AMBER/RED), skill-mix gaps, open-shift risk, upcoming leave/competency/training expiries |
| House Supervisor | Shift operations | Live staffing shortfall, blocked shifts, surge/exception queue |
| Employee self-view | Nurses | Personal compliance status (license, credential, competency, training, leave) |
| HR / Admin | HR | Contract & employment exceptions, labor-law exposure, termination/end-of-service queue |

## 3. Alert engine (reactive triggers)
- Blocked shift / schedule attempt (with reason) → requester + manager.
- License / credential / competency expiry pipeline crossing configurable thresholds.
- Staffing below minimum or skill-mix gap (RED/AMBER) per unit-shift.
- Excessive-OT accumulation; weekly-hour cap breach; rest-period violation attempts.
- Leave request that would breach staffing coverage → routing to coverage review.
- Exception requests awaiting approval past SLA → auto-escalate.
- Reconciliation/parameter drift notifications for compliance admins.

## 4. Reports
- **Automated compliance status** per employee & per shift (spec §11).
- **Labor-law exposure report** (hours, rest, OT, leave, contracts) with audit references.
- **CBAHI workforce compliance report** (license, credential, competency, training, staffing, skill-mix, safety) → feeds M9's existing regulatory submission to MOH/CBAHI.
- **Exception & override register** (who, why, which rule, risk, mitigation, approver, window, corrective action).
- **Blocked-transaction log** (attempts prevented, by rule and unit).

## 5. KPI formulas
| Metric | Formula |
|---|---|
| Labor-law compliance % | Compliant person-shifts ÷ evaluated person-shifts × 100 |
| License validity % | Active nurses with valid license ÷ active nurses × 100 |
| Mandatory-training compliance % | Nurses meeting mandatory training ÷ active nurses × 100 |
| Unsafe-staffing events | Count of shifts with staffing < minimum (RED/BLOCK) |
| Exception/override rate | Approved exceptions ÷ total evaluations × 100 |
| Excessive-OT cases | Nurses exceeding OT cap (rolling) |
| Contract-expiry actioned % | Contracts actioned by deadline ÷ contracts expiring × 100 |

Reports and dashboards respect RBAC **scoping** (facility/department/unit) and data segregation: patient-identifiable data is never shown on workforce screens beyond census/occupancy aggregates.
