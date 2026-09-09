# Hospital Nursing Workforce Management System (HNWMS)

## Complete System Package — Version 1.0

**Organization:** AIGH — Hospital Nursing Department  
**Date:** September 2026  
**Architecture:** 5-Phase Lifecycle + Cross-Cutting Analytics Control Tower  
**Foundation:** Staff Nurse Master Data — Single Source of Truth (SSOT)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Staff Nurse Master Data — Single Source of Truth](#2-staff-nurse-master-data--single-source-of-truth)
3. [5-Phase Architecture](#3-5-phase-architecture)
4. [Phase A — PLAN](#4-phase-a--plan)
5. [Phase B — ACQUIRE](#5-phase-b--acquire)
6. [Phase C — DEPLOY](#6-phase-c--deploy)
7. [Phase D — DEVELOP & RETAIN](#7-phase-d--develop--retain)
8. [Cross-Cutting — Analytics & Control Tower](#8-cross-cutting--analytics--control-tower)
9. [Phase E — EXIT & REPLAN](#9-phase-e--exit--replan)
10. [Data Flow & Integration Architecture](#10-data-flow--integration-architecture)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Glossary](#12-glossary)
13. [Appendix A — Automated Compliance Guardrail Layer (Saudi Labor Law & CBAHI)](#appendix-a--automated-compliance-guardrail-layer-saudi-labor-law--cbahi)

---

## 1. System Overview

The Hospital Nursing Workforce Management System (HNWMS) manages the complete nursing workforce lifecycle — from workforce planning and recruitment through scheduling, attendance, performance, retention, and separation — as a continuous, self-correcting cycle.

### Design Principles

- **Single Source of Truth:** Every module references one authoritative Staff Nurse Master Record — no duplicate employee records across modules
- **Lifecycle Continuity:** Exit data feeds back into workforce planning, ensuring the organization continuously adapts
- **Modular Independence:** Each of the 13 modules encapsulates a distinct domain with defined inputs/outputs
- **Cross-Cutting Analytics:** Module 9 (Control Tower) aggregates data from every module for hospital-wide visibility
- **Regulatory Alignment:** SCFHS credential verification, CBAHI/JCI accreditation KPIs, Saudi Labor Law compliance
- **Automated Compliance Guardrails:** Saudi Labor Law (HRSD), CBAHI, and Hospital Policy requirements are enforced by an automated guardrail layer (ALLOW / WARN / BLOCK) rather than manual HR/Nursing checking — see **Appendix B**
- **Integration-Ready:** Defined interface points for HR/ERP, biometrics, payroll, SCFHS portal, EMR/HIS

### Lifecycle Flow

```
PLAN → ACQUIRE → DEPLOY → DEVELOP & RETAIN → EXIT & REPLAN → PLAN
                              ↑                                  │
                              └──────────── CONTINUOUS CYCLE ────┘

         ╔══════════════════════════════════════════════════╗
         ║   MODULE 9 — ANALYTICS & CONTROL TOWER          ║
         ║   Monitors all phases continuously               ║
         ╚══════════════════════════════════════════════════╝
```

---

## 2. Staff Nurse Master Data — Single Source of Truth

### 2.1 Purpose

The Staff Nurse Master Data serves as the **Single Source of Truth (SSOT)** for nurse identity, employment, organizational, professional, and workforce information. Every nursing workforce module references the same master staff record rather than creating independent duplicate staff records.

### 2.2 Core Principle

```
One Nurse → One Staff Master Record → Multiple Workforce Processes
```

```
                    STAFF NURSE MASTER DATA
                    SINGLE SOURCE OF TRUTH
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
   Recruitment          Credentialing          Deployment
        ↓                     ↓                     ↓
   Scheduling            Attendance              Leave
        ↓                     ↓                     ↓
  Performance          Contract/Retention    Career Development
        ↓                     ↓                     ↓
   Separation       Workforce Analytics    Reconciliation
```

### 2.3 Master Staff Record

Each nurse has one unique Staff Master Record. The **Staff ID** remains consistent throughout the employee's entire lifecycle.

| Field | Example |
|---|---|
| Staff ID | NUR-000125 |
| Employee Number | EMP-00125 |
| Full Name | Staff Nurse |
| Employment Status | Active |
| Job Title | Staff Nurse |
| Department | Medical Ward |
| Nursing Unit | Medical Ward A |
| Position | Approved Position ID |
| Grade | Nursing Grade |
| Specialty | Medical-Surgical |
| Employment Type | Full-Time |
| FTE | 1.00 |
| Hire Date | Effective Date |
| Contract Status | Active |
| License Status | Valid |
| Deployment Status | Deployed |

### 2.4 Master Data Domains

| Domain | Master Information |
|---|---|
| Identity | Staff ID, employee number, name |
| Employment | Hire date, employment status, employment type |
| Organization | Department, nursing unit, position |
| Job | Job title, grade, classification |
| Workforce | Headcount, FTE, work pattern |
| Professional | Qualification, professional classification, experience |
| License | Registration/license reference and status |
| Credentials | Professional credentials and verification |
| Certification | Certification records and validity |
| Competency | Clinical competency profile |
| Deployment | Current assignment and deployment status |
| Contract | Contract dates and status |
| Scheduling | Roster eligibility and shift assignment |
| Attendance | Time and attendance reference |
| Leave | Leave balance and history reference |
| Performance | Appraisal and performance records |
| Career | Career pathway and progression |
| Retention | Retention assessment and actions |
| Separation | Exit status and effective dates |
| System Access | User/account/access status |
| Audit | Created, modified and change history |

### 2.5 System-of-Record Ownership

The Staff Nurse Master maintains the master identity and key attributes, while specialized modules own their respective transactions.

```
Staff Nurse Master
      │
      ├── Identity / Employment
      ├── Position / Organization
      ├── Professional Profile
      │
      └── References
             ├── License → Credentialing Module (M3)
             ├── Competency → Performance & Competency Module (M8)
             ├── Roster → Scheduling Module (M5)
             ├── Attendance → Time Management Module (M6)
             ├── Leave → Leave Module (M7)
             ├── Performance → Performance Module (M8)
             ├── Contract → Contract Module (M10)
             ├── Career → Career Module (M11)
             └── Separation → Exit Module (M12)
```

### 2.6 Data Ownership Model

| Information | Primary Owner |
|---|---|
| Staff Identity | Staff Master / HR |
| Employment Status | HR / Staff Master |
| Position | Workforce / Organizational Master |
| License | Credentialing (M3) |
| Professional Credentials | Credentialing (M3) |
| Competency | Nursing Competency (M8) |
| Roster | Scheduling (M5) |
| Actual Attendance | Time & Attendance (M6) |
| Leave Transactions | Leave Management (M7) |
| Performance | Performance Management (M8) |
| Contract | Contract Management (M10) |
| Career Development | Career Management (M11) |
| Separation | Exit Management (M12) |
| Payroll Transactions | Payroll / Finance (External) |
| Patient Clinical Data | EMR (External) |

### 2.7 Staff Lifecycle Through the Master Record

```
Candidate → Hired → Staff Master Created → Credentialing → Onboarding
    → Competency Validation → Deployment → Active Employment
    → Scheduling / Attendance / Leave → Performance / Career / Retention
    → Separation → Historical Staff Record
```

The Staff ID remains traceable across all stages.

### 2.8 Data Quality Controls

The Staff Master enforces:

- Unique Staff ID — no duplicate active employee records
- Mandatory fields for identity, employment, and organization
- Valid organizational assignment and position reference
- Valid employment status and FTE
- Effective-dated changes preserving history
- Referential integrity across all modules
- Duplicate detection and resolution
- Full audit trail on all changes
- Controlled update workflows

### 2.9 Effective-Dated Master Data

Organizational changes preserve historical information:

```
01-Jan-2026               01-Jul-2026
Medical Ward              ICU
Staff Nurse        →      Staff Nurse
FTE 1.00                  FTE 1.00
```

The system preserves both assignments with their effective dates.

### 2.10 SSOT Integration Architecture

```
                         ┌──────────────────────────┐
                         │   STAFF NURSE MASTER     │
                         │  SINGLE SOURCE OF TRUTH  │
                         └────────────┬─────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ↓                           ↓                           ↓
   WORKFORCE MODULES            CLINICAL SYSTEMS            ENTERPRISE SYSTEMS
          │                           │                           │
          ├─ M1  Workforce Planning   ├─ EMR                      ├─ HR
          ├─ M2  Recruitment          ├─ Clinical Systems          ├─ Payroll
          ├─ M3  Credentialing        │                           ├─ Finance
          ├─ M4  Deployment           │                           ├─ Time & Attendance
          ├─ M5  Scheduling           │                           ├─ LMS
          ├─ M6  Attendance           │                           └─ Access Control
          ├─ M7  Leave                │
          ├─ M8  Performance          │
          ├─ M9  Analytics            │
          ├─ M10 Contract             │
          ├─ M11 Career               │
          ├─ M12 Separation           │
          └─ M13 Reconciliation       │
```

### 2.11 Key Business Rules

1. Every nurse must have one unique Staff Master Record
2. Staff ID must be the common identifier across all workforce modules
3. Modules must reference the Staff Master instead of creating duplicate employee records
4. Changes to master attributes must be controlled and auditable
5. Historical information must be retained using effective dates
6. Transaction modules remain responsible for their own detailed transactions
7. Inactive/separated staff records must not be deleted when historical records are required
8. Integration systems must use controlled Staff ID mapping
9. Duplicate staff records must be detected and resolved through controlled data governance
10. Staff Master data must distinguish master data from transactional data
11. No nurse may be deployed, scheduled, or approved for overtime/leave unless the Compliance Guardrail Layer (Appendix B) evaluates the transaction as compliant (license, credential, competency, working hours/rest, staffing, and coverage checks)

---

## 3. 5-Phase Architecture

| Phase | Name | Scope | Modules |
|---|---|---|---|
| **A** | **PLAN** | Workforce planning, manpower budget, staffing ratios, vacancy analysis, demand forecasting | M1: Workforce Planning |
| **B** | **ACQUIRE** | Recruitment, hiring, license verification, credentialing, medical clearance, onboarding | M2: Recruitment & Hiring, M3: Credentialing & Onboarding |
| **C** | **DEPLOY** | Department assignment, scheduling, rostering, attendance tracking, overtime, leave management | M4: Nursing Deployment, M5: Scheduling & Rostering, M6: Attendance & Time Mgmt, M7: Leave Management |
| **D** | **DEVELOP & RETAIN** | Performance appraisal, competency, training, career development, contract renewal, retention | M8: Performance & Competency, M10: Contract & Retention, M11: Career Development |
| **E** | **EXIT & REPLAN** | Separation processing, clearance, exit interviews, workforce reconciliation, demand forecasting | M12: Separation / Exit, M13: Workforce Reconciliation |
| **X** | **CONTROL TOWER** | Cross-cutting analytics, KPI monitoring, dashboards, predictive analytics, regulatory compliance | M9: Workforce Analytics & Control Tower |

---

## 4. Phase A — PLAN

### Module 1: Workforce Planning

**Purpose:** Ensure the hospital has the right number of nurses, with the right qualifications and skills, in the right department, on the right shift, at the right time.

**SSOT Reference:** Module 1 reads headcount, FTE, position, department, and deployment status from the Staff Nurse Master to determine current workforce against plan.

#### 1.1 Determine Nursing Demand

Determine the required nursing workforce based on patient demand, bed capacity, patient acuity, approved nurse-to-patient ratios, department workload, shift coverage requirements, and expected future demand.

**Demand Factors:**

| Demand Factor | Description |
|---|---|
| Number of Beds | Licensed/approved, operational, staffed, and planned beds by department/unit |
| Patient Census | Actual number of patients receiving care |
| Occupancy Rate | Percentage of available beds occupied |
| Patient Acuity | Patient dependency/acuity level requiring different nursing intensity |
| Nurse-to-Patient Ratio | Approved or configured staffing ratio by unit, specialty, shift, or patient category |
| Department Workload | Nursing activities, procedures, admissions, discharges, transfers, treatments |
| 24-Hour Coverage | Nursing workforce required across morning, evening, night, weekend, holiday, and on-call periods |
| Seasonal Demand | Historical or expected increases/decreases in patient volume |
| Expected Future Demand | Planned expansion, new services, additional beds, projected patient growth |

#### 1.2 Bed Capacity Analysis

The system distinguishes between licensed beds, approved beds, operational beds, staffed beds, occupied beds, and planned future beds.

**Formula:** `Occupancy Rate = Occupied Beds ÷ Operational Beds × 100`

Bed information available by: Hospital → Division → Department → Unit → Specialty

#### 1.3 Patient Census & Occupancy Analysis

The system captures daily census, average daily census, peak census, minimum census, occupancy percentage, admissions, discharges, transfers, patient turnover, and historical census trends — analyzed by hospital, department, unit, shift, day, week, month, and year.

#### 1.4 Patient Acuity Analysis

| Acuity Level | Nursing Requirement |
|---|---|
| Level 1 — Low | Basic/general nursing care |
| Level 2 — Moderate | Increased monitoring and nursing intervention |
| Level 3 — High | Intensive nursing care and frequent intervention |
| Level 4 — Critical | Highly intensive/critical nursing care |

**Key formula:** `Nursing Demand = Patient Volume + Acuity + Workload + Coverage Requirements`

#### 1.5 Nurse-to-Patient Ratio

Configurable staffing ratios by department, unit, specialty, shift, patient category, acuity level, hospital policy, and regulatory requirements.

**Formula:** `Required Nurses = Patient Census ÷ Approved Nurse-to-Patient Ratio`

#### 1.6 Department Workload Analysis

Workload indicators: patient admissions, discharges, transfers, procedures, medication administration, treatments, assessments, documentation requirements, monitoring requirements, emergency activity, specialized procedures, patient dependency, nursing hours required.

Analysis by: Department → Unit → Shift → Date/Period

#### 1.7 24-Hour Coverage Requirement

```
Daily Nursing Requirement
│
├── Morning Requirement
├── Evening Requirement
├── Night Requirement
├── Weekend Requirement
└── Holiday / On-Call Requirement
```

The system identifies any shift where the required workforce or skill mix is not available.

#### 1.8 Seasonal & Expected Demand

Forecasting based on historical patient volume, seasonal patterns, previous occupancy, previous acuity, expected admissions increases, new clinical services, new departments, bed expansion, and temporary demand increases.

#### Module 1 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Hospital strategic plan, patient census/acuity data, regulatory staffing requirements (MOH, CBAHI), reconciliation data from M13, turnover analytics from M9 |
| **Outputs** | Approved manpower plan with position inventory, staffing ratio targets per department, vacancy list and recruitment requisitions to M2, budget allocation |
| **Dependencies** | Receives from: M13 (reconciliation), M9 (analytics). Feeds: M2 (recruitment requisitions) |

---

## 5. Phase B — ACQUIRE

### Module 2: Recruitment & Hiring

**Purpose:** Manage the complete process of converting an approved nursing workforce requirement into a hired nursing employee.

**SSOT Reference:** Upon hiring, Module 2 initiates creation of the Staff Nurse Master Record with identity, employment, and position data. The Staff ID is generated here and follows the nurse through every subsequent module.

#### Core Recruitment Workflow

```
Approved Workforce Requirement → Manpower Request → Approval
→ Candidate Sourcing → Screening → Interview → Selection
→ Offer → Offer Accepted → Employment Contract → Hired
→ Credentialing & Onboarding (M3)
```

#### Level 3 Submodules

| No. | Submodule | Main Function |
|---|---|---|
| 2.1 | Manpower Request | Create recruitment request based on approved workforce requirement |
| 2.2 | Candidate Sourcing | Source and register potential nursing candidates |
| 2.3 | Candidate Screening | Check qualifications, experience and minimum requirements |
| 2.4 | Interview Management | Schedule, conduct and evaluate candidate interviews |
| 2.5 | Candidate Selection | Select the most suitable qualified candidate |
| 2.6 | Offer Management | Prepare, issue and track employment offer |
| 2.7 | Employment Contract | Prepare, approve and execute employment contract |
| 2.8 | Recruitment Workflow & Approval | Manage recruitment approvals and authorization |
| 2.9 | Recruitment Pipeline Tracking | Monitor vacancies and candidate progress |
| 2.10 | Recruitment KPIs | Measure recruitment performance and effectiveness |

**Key Business Rule:** Recruitment must be linked to an approved position and workforce requirement.

#### Module 2 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Approved vacancy list and position requirements from M1, candidate applications |
| **Outputs** | Hired nurse records with signed contracts → M3 for credentialing. Staff Master Record initiated |
| **Dependencies** | Receives from: M1 (requisitions). Feeds: M3 (new hires), Staff Master (record creation) |

---

### Module 3: Credentialing & Onboarding

**Purpose:** Ensure every newly hired nurse is professionally qualified, appropriately licensed, medically cleared, properly oriented, and authorized to work before being independently assigned to patient care.

**SSOT Reference:** Module 3 enriches the Staff Nurse Master Record with license, credential, and certification data. Credential verification status is written back to the master record.

#### 3.1 License Verification

The system tracks: professional registration number, license/registration type, issuing authority, issue date, expiry date, verification status, verification date, restrictions, renewal requirements.

```
License Submitted → Verification → Verified?
    YES → Continue Credentialing
    NO  → Resolve Issue
```

#### 3.2 Professional Credentials

Verify qualifications against the approved position:

| Credential Type | Examples |
|---|---|
| Academic Qualification | Diploma, Bachelor's, Master's, Doctorate |
| Professional Qualification | Nursing qualification and professional classification |
| Clinical Experience | Medical, Surgical, ICU, Emergency, Pediatric |
| Specialty Qualification | Specialty-specific qualification |
| Professional Certification | BLS/CPR, ACLS, PALS, specialty certifications |
| Experience Verification | Previous employer/service verification |

**Credential categories:** Mandatory (must be valid before deployment), Required (for specific role/unit), Additional (desirable or developmental).

#### 3.3 Credential Verification Status

| Status | Description |
|---|---|
| Pending Verification | Credential submitted but not yet verified |
| Under Verification | Verification is in progress |
| Verified | Credential has been successfully verified |
| Conditionally Verified | Credential accepted subject to a defined condition |
| Missing | Required credential has not been provided |
| Invalid | Credential could not be validated |
| Expired | Credential has passed its validity period |
| Rejected | Credential does not meet the requirement |
| Exception | Requires management or credentialing review |

#### 3.4 Position Requirement Matching

```
Position Requirements → Nurse Credentials → Qualification Match
→ Experience Match → Specialty Match → Credential Verification
→ Credential Eligibility Result
```

#### 3.5 Credential Expiry Monitoring

`180 Days → 120 Days → 90 Days → 60 Days → 30 Days → Expired`

Configurable by credential type, hospital policy, and regulatory requirements.

#### 3.6 Medical Clearance

Pre-employment medical examination and fitness-for-duty screening.

#### 3.7 Orientation Program

Orientation enrollment and tracking, department-specific orientation, hospital orientation.

#### 3.8 System Access Provisioning

EMR access, scheduling system access, attendance system enrollment, department-specific system access.

#### Module 3 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | New hire records from M2, credential documents, SCFHS verification results |
| **Outputs** | Fully credentialed nurse profile → M4 for deployment. Staff Master updated with license, credential, and certification data |
| **Dependencies** | Receives from: M2 (new hires). Feeds: M4 (deployment-ready nurses), Staff Master (credential data). External: SCFHS portal |

---

## 6. Phase C — DEPLOY

### Module 4: Nursing Deployment

**Purpose:** Ensure nurses are assigned to the right department, position, shift, and clinical environment based on their qualifications, competencies, specialty, availability, staffing requirements, and the approved workforce plan.

**SSOT Reference:** Module 4 reads the nurse's credential status, competency profile, and position eligibility from the Staff Master. Deployment assignment is written back as the current deployment status.

#### 4.1 Deployment Requirement

Based on: approved manpower plan, current staffing levels, patient census, patient acuity, nurse-to-patient ratio, department requirements, shift requirements, planned leave, absences, vacancies, skill-mix requirements.

#### 4.2 Nurse Eligibility Check

Before assignment, verify: employment status, position, professional license, required credentials, clinical competencies, specialty, experience, orientation completion, medical clearance, department authorization, availability.

**Example:** ICU assignment → ICU competency + valid license + critical-care credentials + completed ICU orientation.

> **Automated enforcement:** These eligibility checks are applied by the **Compliance Guardrail Layer** (Appendix B) before any deployment/assignment/redeployment is published. A deployment is BLOCKED if employment/license/credential/competency/unit-authorization is invalid (CBA-LIC-001, CBA-CRED-001, CBA-COMP-001, HOS-POL-004) or if the move is an unauthorized transfer (LAB-CT-009) or creates an unsafe assignment (CBA-SAFE-001).

#### 4.3 Department Assignment

Assign to: Hospital → Nursing Division → Department → Nursing Unit/Ward → Position → Specialty → Reporting Manager → Head Nurse.

#### 4.4 Position Assignment

| Department | Position | Approved | Occupied | Available |
|---|---|---|---|---|
| ICU | Staff Nurse | 24 | 20 | 4 |
| ER | Staff Nurse | 30 | 27 | 3 |
| OR | OR Nurse | 18 | 16 | 2 |

Prevents unauthorized overstaffing and ensures deployment follows the approved manpower plan.

#### 4.5 Competency & Specialty Matching

| Nurse | Specialty | Competency | Suitable Department |
|---|---|---|---|
| Nurse A | Critical Care | ICU | ICU |
| Nurse B | Emergency | ER | Emergency |
| Nurse C | Operating Room | OR | Operating Room |
| Nurse D | General Nursing | Medical/Surgical | Medical Ward |

#### 4.6 Shift Deployment

Assignments: Morning, Evening, Night, Rotating, Weekend, On-call.

Considers: maximum working hours, rest periods, approved leave, existing roster, overtime, consecutive shifts, skill mix, department staffing minimums.

#### 4.7 Internal Transfer / Redeployment

```
Staffing Shortage → Identify Eligible Nurses → Check Competency
→ Check Availability → Manager Approval → Temporary Redeployment
→ Monitor Assignment → Return / Extend / Permanent Transfer
```

#### 4.8 Deployment Approval

```
Deployment Request → Head Nurse → Nurse Manager
→ Nursing Administration → HR / Workforce Control → Approved Assignment
```

#### Module 4 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Credentialed nurse profiles from M3, department staffing targets from M1, competency data from M8 |
| **Outputs** | Active deployment roster per department → M5 for scheduling. Staff Master updated with deployment status |
| **Dependencies** | Receives from: M1, M3, M8. Feeds: M5 (scheduling base), Staff Master |

---

### Module 5: Scheduling & Rostering

**Purpose:** Create a safe, balanced, and compliant nursing roster that ensures adequate staffing for every shift, while considering nurse availability, competencies, leave, working hours, rest periods, department requirements, and approved manpower levels.

**SSOT Reference:** Module 5 reads the nurse's deployment assignment, FTE, contract type, and leave status from the Staff Master to determine roster eligibility.

#### 5.1 Monthly Roster Planning

Based on: department staffing requirements, approved manpower plan, number of available nurses, patient census/acuity, required skill mix, nurse specialty, contracted working hours, previous month's roster, approved leave, training schedules, holidays/weekends, overtime requirements.

#### 5.2 Shift Assignment

| Shift | Example |
|---|---|
| Morning | 07:00–15:00 |
| Evening | 15:00–23:00 |
| Night | 23:00–07:00 |
| Extended | Hospital-defined |
| On Call | Hospital-defined |

Auto-identifies: uncovered shifts, excess staffing, understaffing, skill shortages, duplicate assignments, leave conflicts, excessive consecutive shifts.

#### 5.3 Day / Night Rotation

`Day → Evening → Night → Off`

Monitors: consecutive working days, consecutive night shifts, rest periods, shift rotation, weekend distribution, holiday distribution, maximum scheduled hours, overtime exposure.

#### 5.4 Leave Integration

```
Approved Leave → Employee Unavailable → Remove from Available Staffing
→ Recalculate Shift Coverage → Identify Staffing Gap → Find Replacement
```

#### 5.5 Replacement & Coverage

Matching considers: same department, same position, required competency, required specialty, availability, leave status, existing roster, working-hour limits, overtime exposure, rest-period requirements.

#### 5.6 Staffing Coverage Check

| Department | Shift | Required | Scheduled | Gap | Status |
|---|---|---|---|---|---|
| ICU | Morning | 8 | 8 | 0 | Covered |
| ICU | Evening | 8 | 7 | -1 | Gap |
| ICU | Night | 6 | 6 | 0 | Covered |
| ER | Morning | 10 | 11 | +1 | Over |
| ER | Night | 8 | 6 | -2 | Critical Gap |

#### 5.7 Roster Approval

```
Roster Created → Head Nurse Review → Staffing Coverage Check
→ Nurse Manager Review → Nursing Administration Approval
→ Roster Published → Staff Notification
```

> **Automated guardrail (critical):** Before a roster/shift is published, the **Compliance Guardrail Layer** (Appendix B) evaluates every shift candidate. It BLOCKS/WARNS on working-hours and rest violations (LAB-WH-*, LAB-RS-*), license/credential/competency/training invalidity (CBA-LIC/CRED/COMP, CBA-TRAIN-001), and **BLOCKs when the roster falls below minimum staffing or required skill-mix** (CBA-STAFF-001/002, CBA-SKILL-001) — even if every scheduled nurse is individually eligible. A schedule is never auto-approved on individual legal eligibility alone.

#### Module 5 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Department roster from M4, leave calendar from M7, staffing ratio targets from M1 |
| **Outputs** | Approved monthly schedule → M6 (attendance baseline). Staff Master updated with roster assignment |
| **Dependencies** | Receives from: M1, M4, M7. Feeds: M6 (attendance baseline) |

---

### Module 6: Attendance & Time Management

**Purpose:** Accurately capture and validate each nurse's actual working time against the approved roster, identify attendance exceptions, calculate overtime, and provide validated attendance data to payroll.

**SSOT Reference:** Module 6 reads the nurse's scheduled shift from the Staff Master/M5. Attendance summary status is referenced back to the master record for analytics and payroll.

#### 6.1 Clock-In / Clock-Out

Captures: Employee ID, employee name, department, date, scheduled shift, actual clock-in, actual clock-out, attendance device/source, location, shift status.

#### 6.2 Late / Early Departure Monitoring

| Nurse | Scheduled | Actual | Result |
|---|---|---|---|
| Nurse A | 07:00–15:00 | 06:58–15:02 | Normal |
| Nurse B | 07:00–15:00 | 07:18–15:00 | Late |
| Nurse C | 07:00–15:00 | No punch | Missing Punch |
| Nurse D | 07:00–15:00 | 07:00–13:30 | Early Departure |

#### 6.3 Absence Monitoring

Distinguishes: approved leave, approved absence, sick leave, unexcused absence, no-show, absent with missing documentation, absent pending validation.

#### 6.4 Overtime Management

```
Actual Hours Worked → Scheduled Hours → Excess Hours?
    YES → Overtime → Approval Required → Payroll Calculation
    NO  → Normal
```

Captures: normal scheduled hours, actual hours worked, approved overtime, unapproved overtime, overtime reason, overtime date, overtime hours, approving manager, payroll status.

> **Automated guardrail:** Overtime detection, eligibility (contracted hours first), approval chain (Department → Nursing Director), hour caps, and rate (hourly wage + 50% base) are enforced by the **Compliance Guardrail Layer** (LAB-OT-*). Only approved, compliant overtime is passed to payroll (LAB-OT-007). See Appendix B.

#### 6.5 Missed Punch Management

```
Missing Clock-Out → Exception Created → Employee Correction Request
→ Head Nurse / Manager Review → Approved? → Corrected / Exception Remains
```

Full audit trail: original record, correction requested, reason, supporting information, submitted by, approved/rejected by, date/time.

#### 6.6 Attendance Validation

```
Raw Attendance → Roster Matching → Exception Detection → Leave Matching
→ Overtime Calculation → Manager Validation → Payroll Validation
→ Validated Attendance
```

#### 6.7 Payroll Interface

Exports: regular working hours, overtime hours, approved overtime, absence days, unpaid absence, late/attendance deductions, approved leave, other time-based payroll inputs.

#### Module 6 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Scheduled shifts from M5, biometric punch data (external), leave records from M7 |
| **Outputs** | Validated attendance records, overtime reports, payroll interface file, absence data to M9 |
| **Dependencies** | Receives from: M5, M7. Feeds: M9 (analytics), Payroll (external). External: biometric system |

---

### Module 7: Leave Management

**Purpose:** Manage employee leave from request to return-to-work, ensuring that leave balances, approvals, staffing coverage, rostering, attendance, and payroll are properly coordinated.

**SSOT Reference:** Module 7 reads employment terms and entitlements from the Staff Master. Leave balance and history are maintained as transactional data owned by this module, with current balance status referenced from the master.

#### 7.1 Leave Types

Annual leave, sick leave, emergency leave, maternity leave, paternity/parental leave, bereavement leave, study or training leave, unpaid leave, special leave, other approved leave.

Each type has configurable rules for: eligibility, entitlement, accrual, maximum balance, carry-forward, expiry, required documents, approval workflow, payroll treatment.

#### 7.2 Leave Request

```
Leave Request → Check Leave Balance → Check Eligibility
→ Check Roster Conflict → Check Staffing Coverage → Submit for Approval
```

> **Automated guardrail:** Leave approval is **not based on balance alone**. The **Compliance Guardrail Layer** (Appendix B) validates entitlement/balance/carry-forward (LAB-LV-001..005) **and** checks whether approving the leave would create unsafe staffing coverage (LAB-LV-006) before ALLOW / WARN / BLOCK. Maternity/extended leave triggers replacement planning (LAB-LV-007).

#### 7.3 Leave Balance Calculation

**Formula:** `Available Leave = Opening Balance + Accrued Leave + Adjustments − Approved/Used Leave`

| Leave Type | Opening | Accrued | Used | Pending | Available |
|---|---|---|---|---|---|
| Annual Leave | 10 | 15 | 8 | 2 | 15 |
| Sick Leave | Policy Based | — | 3 | 0 | Remaining |
| Emergency Leave | Policy Based | — | 1 | 0 | Remaining |

#### 7.4 Leave and Roster Integration

```
Leave Request → Employee Availability Check → Roster Conflict Check
→ Department Staffing Analysis → Coverage Available?
    YES → Continue Approval
    NO  → Replacement / Staffing Review
```

Triggers: roster adjustment, replacement requirement, shift coverage review, redeployment consideration, overtime planning.

#### 7.5 Leave Approval Workflow

```
Employee Leave Request → Head Nurse Review → Staffing / Coverage Check
→ Nurse Manager Approval → HR Validation → Leave Approved
→ Roster Updated → Attendance Updated
```

#### 7.6 Sick Leave Management

Tracks: sick leave dates, supporting medical documentation, approval status, return-to-work requirement, repeated absence patterns, leave entitlement/balance.

#### 7.7 Emergency Leave

Faster workflow: Employee Notification → Immediate Manager Review → Temporary Attendance Update → Staffing Coverage → Formal Approval.

#### 7.8 Maternity and Other Extended Leave

Extended leave tracking: start date, expected end date, replacement planning, return-to-work, position hold.

#### 7.9 Return-to-Work

```
Leave End Date → Return to Work → Attendance Updated → Roster Reactivated
→ Medical Clearance (if required) → Full Duty / Modified Duty
```

#### Module 7 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Leave requests from nurses, employment contract terms, Saudi Labor Law leave entitlements |
| **Outputs** | Approved leave records, leave calendar to M5, leave utilization data to M9, final leave balance to M12 |
| **Dependencies** | Receives from: nurse requests, contract data. Feeds: M5, M6, M9, M12 |

---

## 7. Phase D — DEVELOP & RETAIN

### Module 8: Performance & Competency Management

**Purpose:** Ensure every nurse maintains the required clinical competency, professional performance, and patient-safety standards for their assigned role, while identifying development needs and continuously improving workforce capability.

**SSOT Reference:** Module 8 reads the nurse's position, department, grade, and deployment from the Staff Master. Performance appraisal scores and competency profile status are written back and become inputs for deployment eligibility (M4), contract renewal (M10), and career progression (M11).

#### 8.1 Performance Appraisal

Assessment areas: quality of patient care, patient safety, clinical performance, documentation, medication safety, infection prevention, communication, teamwork, attendance/reliability, professional behavior, leadership, policy compliance, patient experience, productivity.

```
Performance Period → Goals / Expectations → Self Assessment
→ Supervisor Assessment → Nurse Manager Review → Performance Rating
→ Feedback → Development Actions
```

#### 8.2 Competency Assessment

**Performance appraisal:** "How well is the nurse performing?"  
**Competency assessment:** "Can the nurse safely and effectively perform the required clinical skill?"

| Competency | Required | Result | Status |
|---|---|---|---|
| Medication Administration | Yes | Competent | Valid |
| IV Therapy | Yes | Competent | Valid |
| BLS | Yes | Competent | Valid |
| Ventilator Management | ICU | Needs Improvement | Training Required |
| Central Line Care | ICU | Competent | Valid |

#### 8.3 Clinical Skills Assessment

Role-specific by department:

- **General Nursing:** Vital signs, medication administration, patient assessment, IV therapy, wound care, infection control
- **ICU:** Ventilator management, critical patient assessment, hemodynamic monitoring, emergency response, advanced life support
- **Emergency:** Triage, emergency response, resuscitation, trauma care, rapid assessment
- **Operating Room:** Surgical asepsis, instrument handling, surgical counts, perioperative procedures

#### 8.4 Competency Gap Identification

```
Position Requirements → Required Competency Profile
→ Employee Competency Profile → Compare → Gap?
    YES → Training Required
    NO  → Competent / Valid
```

> **Automated guardrail:** Competency results (M8) and training completion (M11/LMS) feed the **Compliance Guardrail Layer** (Appendix B). Expired/absent competency or mandatory training BLOCKs scheduling/deployment for the affected skills (CBA-COMP-001, CBA-TRAIN-001/002, CBA-MED-001, CBA-IP-001, CBA-EM-001); clinical incidents trigger automated escalation (CBA-INCID-001).

#### 8.5 Training Needs Identification

Generated from: failed competency assessment, expired certification, performance appraisal, clinical incident trends, new equipment, new policies, department requirements, new role/promotion, regulatory requirements, individual development goals.

| Nurse | Gap | Training Required | Priority |
|---|---|---|---|
| Nurse A | IV Therapy | IV Therapy Training | High |
| Nurse B | BLS Expiring | BLS Renewal | High |
| Nurse C | Leadership | Charge Nurse Development | Medium |

#### 8.6 Individual Development Plan (IDP)

Contains: development objective, competency gap, required training, development activity, target completion date, responsible person, manager, progress, completion status, reassessment date.

#### Module 8 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Nurse profiles from Staff Master, attendance/conduct records from M5-M6, position competency requirements from M1 |
| **Outputs** | Appraisal scores, competency status per nurse, training recommendations to M11, performance data to M4, M9, M10. Staff Master updated with competency profile |
| **Dependencies** | Receives from: M1, M5, M6. Feeds: M4, M9, M10, M11, Staff Master |

---

### Module 10: Contract & Retention Management

**Purpose:** Manage nursing employment contracts from contract monitoring and expiry alerts through renewal, non-renewal, approval, and retention monitoring — ensuring continuity of employment, preventing avoidable staffing gaps, and identifying retention risks early.

**SSOT Reference:** Module 10 reads contract dates and employment terms from the Staff Master. Contract renewal status and retention risk score are written back to the master record.

#### Core Process

```
Contract Monitoring → Contract Expiry Alert → Renewal Assessment
→ Employee Decision → Management Recommendation → Approval Workflow
→ Renewal / Non-Renewal → Contract Update → Retention Monitoring
→ Workforce Planning
```

#### Level 3 Submodules

| No. | Submodule | Main Function |
|---|---|---|
| 10.1 | Contract Master Management | Centralized contract record for every nursing employee |
| 10.2 | Contract Expiry Monitoring | Continuous monitoring with configurable alerts (180/120/90/60/30 days) |
| 10.3 | Renewal Assessment | Structured assessment: performance, competency, workforce need, retention risk |
| 10.4 | Renewal Assessment Score | Configurable weighted scoring (Performance 25%, Competency 20%, Attendance 15%, Workforce 20%, Retention 10%, Conduct 10%) |
| 10.5 | Employee Renewal Decision | Capture employee intent: renew / not renew / negotiate |
| 10.6 | Management Recommendation | Renew / Renew with Conditions / Review / Do Not Renew |
| 10.7 | Renewal Approval Workflow | Department → HR → Administration approval chain |
| 10.8 | Contract Renewal | Execute renewal, update contract dates and terms |
| 10.9 | Non-Renewal Management | Process non-renewal → M12 for separation |
| 10.10 | Retention Monitoring | Ongoing retention risk tracking and scoring |
| 10.11 | Retention Action Plan | Targeted interventions for at-risk nurses |
| 10.12 | Contract & Retention Dashboard | Expiry pipeline, renewal status, retention metrics |
| 10.13 | Contract Status Structure | Active / Expiring / Renewed / Expired / Closed |
| 10.14 | System Alerts & Controls | Automated alerts and business rule enforcement |
| 10.15 | Integration With Other Modules | Data flows to/from M6, M8, M9, M12 |
| 10.16 | Complete Workflow | End-to-end contract lifecycle |
| 10.17 | Cycle Connection | Feeds non-renewals to M12, metrics to M9, gaps to M1 |

**Alert Levels:**

| Days to Expiry | Alert |
|---|---|
| >180 | Normal |
| 180–121 | Early Planning |
| 120–91 | Attention |
| 90–61 | High Priority |
| 60–31 | Critical |
| ≤30 | Urgent |
| Expired | Critical |

> **Automated guardrail:** The **Compliance Guardrail Layer** (Appendix B) enforces contract/probation/renewal monitoring (LAB-CT-001..003), position/title/salary mismatch guards (LAB-CT-004..006), employment-status validation (LAB-CT-007), wage-category-transfer requiring written agreement (LAB-CT-008), and unauthorized-transfer blocking (LAB-CT-009).

#### Module 10 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Contract dates/terms from Staff Master, performance data from M8, attendance from M6, turnover analytics from M9 |
| **Outputs** | Renewed/non-renewed contract status, non-renewal cases → M12 (separation), retention metrics → M9. Staff Master updated with contract and retention status |
| **Dependencies** | Receives from: M6, M8, M9, Staff Master. Feeds: M9, M12, Staff Master |

---

### Module 11: Career Development

**Purpose:** Support nursing career progression through structured training, certification, promotion pathways, and succession planning.

**SSOT Reference:** Module 11 reads the nurse's competency profile, performance history, and current position from the Staff Master. Career progression updates (promotions, certifications, training completions) are written back to the master record.

#### Level 3 Submodules

| No. | Submodule | Main Function |
|---|---|---|
| 11.1 | Career Profile | Career history, qualifications, aspirations, and development goals |
| 11.2 | Career Pathways | Defined progression ladders (Staff Nurse → Senior → Charge → Supervisor → Manager) |
| 11.3 | Training & Development Planning | Training programs aligned with competency gaps and career goals |
| 11.4 | Certification Management | BLS, ACLS, specialty certifications — tracking and renewal |
| 11.5 | Competency Progression | Track competency advancement over time |
| 11.6 | Individual Development Plan (IDP) | Structured plan linking gaps to training to completion |
| 11.7 | Career Readiness Assessment | Evaluate readiness for promotion or new role |
| 11.8 | Promotion Management | Eligibility assessment, recommendation, approval, execution |
| 11.9 | Internal Transfer & Career Mobility | Lateral moves, rotations, cross-training assignments |
| 11.10 | Leadership Development | Charge nurse, supervisor, and management development programs |
| 11.11 | Succession Planning | Identify and prepare successors for critical nursing positions |
| 11.12 | Critical Position Succession Matrix | Map key positions to ready/developing successors |
| 11.13 | Career Development Dashboard | Career metrics, training completion, promotion pipeline |
| 11.14 | Career Development Status | Active / In Progress / Completed / On Hold |
| 11.15 | System Controls | Promotion eligibility rules, training prerequisites |
| 11.16 | Integration With Other Modules | Data flows to/from M1, M4, M8, M9 |
| 11.17 | Complete Workflow | End-to-end career development lifecycle |
| 11.18 | Cycle Connection | Updated profiles to M4 (redeployment), succession data to M9 |

#### Module 11 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Development plans from M8, training records, certification expiry data, position vacancies from M1 |
| **Outputs** | Updated competency profiles → M4 (redeployment), promotion records, succession readiness → M9. Staff Master updated with career progression |
| **Dependencies** | Receives from: M1, M8. Feeds: M4, M9, Staff Master |

---

## 8. Cross-Cutting — Analytics & Control Tower

### Module 9: Workforce Analytics & Control Tower

**Purpose:** Provide nursing management with a real-time and historical view of workforce capacity, staffing performance, workforce risks, and operational trends — enabling evidence-based decisions about staffing, recruitment, scheduling, retention, and workforce costs.

**SSOT Reference:** Module 9 reads aggregated data from the Staff Nurse Master and all operational modules. It does not own transactional data — it consumes published events and snapshots from each module. The Staff Master is the common join key for all analytics.

#### KPI Domains

| No. | KPI Area | Key Metrics |
|---|---|---|
| 9.1 | Staffing Levels | Required vs. budgeted vs. employed vs. available vs. scheduled vs. actual |
| 9.2 | Nurse-to-Patient Ratio | Actual vs. target ratio by department, unit, shift, acuity |
| 9.3 | Overtime | Hours, cost, department, reason, approved/unapproved |
| 9.4 | Absenteeism | Absence rate, sick leave, unplanned absence, patterns |
| 9.5 | Turnover | Voluntary/involuntary, by department, position, tenure, cost |
| 9.6 | Vacancy Rate | Vacant positions ÷ total approved positions, vacancy aging |
| 9.7 | Productivity | Productive hours, nursing hours per patient day, utilization |
| 9.8 | Leave Utilization | Entitlement vs. taken, carry-forward, expiring balances |
| 9.9 | Contract Expiry | Pipeline of expiring contracts by timeline |
| 9.10 | Retention Risk | Risk score distribution, at-risk nurses by department |

#### Key Formulas

| Metric | Formula |
|---|---|
| Occupancy Rate | Occupied Beds ÷ Operational Beds × 100 |
| Absenteeism Rate | Total Absence Days ÷ Total Scheduled Working Days × 100 |
| Turnover Rate | Number of Separations ÷ Average Workforce × 100 |
| Vacancy Rate | Vacant Approved Positions ÷ Total Approved Positions × 100 |
| Productivity | Productive Nursing Hours ÷ Available Nursing Hours × 100 |
| Leave Utilization | Leave Taken ÷ Available Leave Entitlement × 100 |

#### Dashboard Outputs

- Executive dashboard (CNO, HR Director, Hospital Director)
- Department-level operational dashboards
- Alert engine (staffing shortfall, overtime threshold, contract expiry)
- Predictive analytics (turnover risk, demand forecasting)
- Regulatory compliance reports (CBAHI, MOH, Nitaqat)
- Ad-hoc reporting and data export

> **Automated guardrail:** Module 9 also consumes the **Compliance Guardrail Layer** (Appendix B) — employee & shift compliance status, labor-law/CBAHI compliance KPIs, blocked-transaction and exception registers — to report the Nursing Director compliance targets (valid licenses 100%, expired credentials 0, mandatory-training ≥ 95%, unsafe-staffing events 0, CBAHI workforce compliance ≥ 95%, etc.).

#### Staffing Levels Example

| Department | Required | Budgeted | Employed | Available | Scheduled | Gap |
|---|---|---|---|---|---|---|
| ICU | 30 | 30 | 28 | 26 | 25 | **-5** |
| ER | 35 | 35 | 34 | 32 | 33 | **-2** |
| Medical Ward | 45 | 45 | 43 | 41 | 42 | **-3** |

#### Module 9 — Architecture

Operates as a **horizontal service layer** across all five phases. Does not own transactional data — it consumes published events/snapshots from each module via a shared data bus or direct API calls. The Staff Nurse Master SSOT is the common identity key for all cross-module analytics.

| | Detail |
|---|---|
| **Data Sources** | All 12 operational modules (M1-M8, M10-M13) via Staff Master join key |
| **Outputs** | Dashboards, alerts, predictive analytics, regulatory compliance reports |
| **Dependencies** | Receives from: all modules. Feeds: M1 (planning data), M10 (retention risk), M13 (reconciliation analytics) |

---

## 9. Phase E — EXIT & REPLAN

### Module 12: Separation / Exit Management

**Purpose:** Manage the complete separation process from resignation or termination through final clearance, ensuring compliance and data integrity.

**SSOT Reference:** Module 12 reads the nurse's complete employment record from the Staff Master — attendance, leave balance, contract status, position — to process the separation. Upon completion, the Staff Master record is updated to historical/separated status while preserving the full lifecycle record.

#### Core Process

```
Resignation / Termination → Notice Period → Handover → Replacement Requirement
→ Clearance → Final Attendance Reconciliation → Final Leave Reconciliation
→ Final Payroll Reconciliation → Exit Interview → Access & System Closure
→ Final Separation Closure → M13 (Workforce Reconciliation)
```

#### Level 3 Submodules

| No. | Submodule | Main Function |
|---|---|---|
| 12.1 | Separation Initiation | Resignation submission, termination processing, non-renewal exit |
| 12.2 | Resignation Management | Submission, acceptance workflow, withdrawal handling |
| 12.3 | Termination Management | Disciplinary, redundancy, probation failure processing |
| 12.4 | Contract Non-Renewal Exit | Processing from M10 non-renewal decision |
| 12.5 | Notice Period Management | Notice tracking, garden leave, early release |
| 12.6 | Handover Management | Responsibilities, patients, documentation handover |
| 12.7 | Replacement Requirement | Vacancy notification to M13 and M1 |
| 12.8 | Clearance Management | IT access, ID badge, housing, equipment clearance checklist |
| 12.9 | Final Attendance Reconciliation | Reconcile actual attendance with M6 |
| 12.10 | Final Leave Reconciliation | Reconcile leave balance with M7 |
| 12.11 | Final Payroll Reconciliation | End-of-service benefits per Saudi Labor Law |
| 12.12 | Exit Interview | Structured exit interview and reason capture |
| 12.13 | Exit Reason Analytics | Analyze departure reasons for retention improvement |
| 12.14 | Knowledge & Responsibility Transfer | Ensure critical knowledge is transferred |
| 12.15 | Employee Access & System Closure | Deactivate all system access |
| 12.16 | Final Separation Closure | Complete separation record |
| 12.17 | Separation Dashboard | Separation metrics, pending clearances, exit trends |
| 12.18 | Separation Status Structure | Initiated / In Progress / Clearance / Final Settlement / Closed |
| 12.19 | System Alerts & Controls | Automated alerts and business rule enforcement |
| 12.20 | Integration With Other Modules | Data flows to M6, M7, M9, M13, Payroll |

#### Module 12 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Resignation letters, non-renewal decisions from M10, final attendance from M6, leave balances from M7 |
| **Outputs** | Completed separation record, exit interview data, vacancy notification → M13, final settlement → Payroll. Staff Master updated to separated/historical status |
| **Dependencies** | Receives from: M6, M7, M10. Feeds: M13, Payroll (external), Staff Master |

---

### Module 13: Workforce Reconciliation & Planning Feedback

**Purpose:** Analyze current workforce status against plan, reconcile vacancies and movements, generate demand forecasts, and feed actionable data back into workforce planning — completing the cycle.

**SSOT Reference:** Module 13 reads the entire workforce state from the Staff Master — all active, separated, and vacant positions — to perform plan-vs-actual reconciliation. Its output (planning recommendations and demand forecasts) feeds directly back into Module 1, closing the lifecycle loop.

#### Level 3 Submodules

| No. | Submodule | Main Function |
|---|---|---|
| 13.1 | Workforce Reconciliation | Compare planned vs. actual headcount across all dimensions |
| 13.2 | Vacancy Reconciliation | Approved positions vs. filled, vacancy aging, department gaps |
| 13.3 | Turnover Reconciliation | Turnover rate, reasons, cost, patterns by department |
| 13.4 | Workload Reconciliation | Actual nurse-to-patient ratios vs. target |
| 13.5 | Staffing Requirement Reconciliation | Current staffing adequacy by department and shift |
| 13.6 | Skill-Mix Reconciliation | Required vs. actual skill mix per department |
| 13.7 | Shift Coverage Reconciliation | Shift-level coverage analysis |
| 13.8 | Overtime Reconciliation | Overtime trends, root causes, cost impact |
| 13.9 | Absence & Availability Reconciliation | Absence patterns and their staffing impact |
| 13.10 | Recruitment Effectiveness Feedback | Time-to-fill, cost-per-hire, source effectiveness |
| 13.11 | Retention & Separation Feedback | Exit trends, retention intervention effectiveness |
| 13.12 | Contract & Renewal Feedback | Renewal rates, non-renewal impact |
| 13.13 | Career Development Feedback | Training ROI, promotion pipeline health |
| 13.14 | Future Demand Forecasting | Census-based, expansion, seasonal demand projections |
| 13.15 | Workforce Gap Forecast | Projected gaps by department, specialty, timeline |
| 13.16 | Planning Recommendations | Data-driven recommendations for the next planning cycle |
| 13.17 | Management Review & Planning Approval | Present reconciliation findings for leadership decision |
| 13.18 | Workforce Plan Revision | Feed approved changes back into M1 |
| 13.19 | Workforce Reconciliation Dashboard | Variance analysis, risk classification, trend visualization |
| 13.20 | Variance & Risk Classification | Classify variances by severity and required action |

#### Module 13 — Inputs & Outputs

| | Detail |
|---|---|
| **Inputs** | Separation data from M12, current headcount from M4/Staff Master, analytics from M9, original plan from M1 |
| **Outputs** | Reconciliation report, demand forecast, planning recommendations → M1 (Workforce Planning) — **closing the lifecycle loop** |
| **Dependencies** | Receives from: M1, M4, M9, M12, Staff Master. Feeds: M1 (cycle restart) |

---

## 10. Data Flow & Integration Architecture

### 10.1 Inter-Module Data Flows

| From | To | Data Flow |
|---|---|---|
| M1 (Plan) | M2 (Recruit) | Approved vacancy list, position requirements, budget allocation |
| M2 (Recruit) | M3 (Credential) | New hire records with signed employment contracts |
| M2 (Recruit) | Staff Master | **Staff Master Record creation** (Staff ID generated) |
| M3 (Credential) | M4 (Deploy) | Fully credentialed nurse profiles |
| M3 (Credential) | Staff Master | **License, credential, certification data** |
| M4 (Deploy) | M5 (Schedule) | Active department roster, nurse-to-department mapping |
| M4 (Deploy) | Staff Master | **Deployment status and assignment** |
| M5 (Schedule) | M6 (Attend) | Approved monthly schedule, shift attendance baseline |
| M7 (Leave) | M5 (Schedule) | Leave calendar for gap-fill scheduling |
| M8 (Perform) | M4, M11 | Competency assessments → deployment; training needs → career |
| M8 (Perform) | Staff Master | **Competency profile and performance status** |
| M10 (Contract) | M12 (Exit) | Non-renewal decisions triggering separation |
| M10 (Contract) | Staff Master | **Contract renewal status and retention risk** |
| M11 (Career) | Staff Master | **Career progression, certifications, promotions** |
| M12 (Exit) | M13 (Reconcile) | Separation records, vacancy notifications |
| M12 (Exit) | Staff Master | **Separated/historical status** |
| M13 (Reconcile) | M1 (Plan) | Reconciliation report, demand forecast — **CYCLE RESTART** |
| All Modules | M9 (Analytics) | Published KPI metrics via Staff Master join key |

### 10.2 External System Integrations

| External System | Interface Module(s) | Integration Description |
|---|---|---|
| HR / ERP System | M2, M10, M12, Staff Master | Employee master data sync, contract management, end-of-service |
| Biometric Attendance | M6 | Real-time clock-in/out data from fingerprint, facial recognition, or card terminals |
| Payroll System | M6, M7, M12 | Attendance summary, overtime, leave deductions, final settlement |
| SCFHS Portal | M3 | Professional license verification and credential validation |
| EMR / HIS | M4, M9 | Patient census and acuity data for ratio calculations |
| MOH / CBAHI Reporting | M9 | Regulatory compliance report submission |
| Nitaqat / GOSI | M1, M9 | Saudization ratio tracking and social insurance compliance |
| Learning Management System | M11 | Training enrollment, completion, certification tracking |
| Access Control | M3, M12 | System provisioning on hire, deactivation on separation |

### 10.3 Module Dependency Matrix

`X` = Row module provides data to column module

| | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 | M13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **M1** | | X | | X | X | | | | | | | | |
| **M2** | | | X | | | | | | | | | | |
| **M3** | | | | X | | | | | | | | | |
| **M4** | | | | | X | | | | X | | | | |
| **M5** | | | | | | X | | | X | | | | |
| **M6** | | | | | | | X | X | X | X | | X | |
| **M7** | | | | | X | X | | | X | | | X | |
| **M8** | | | | X | | | | | X | X | X | | |
| **M9** | X | | | | | | | | | X | | | X |
| **M10** | | | | | | | | | X | | | X | |
| **M11** | | | | X | | | | | X | | | | |
| **M12** | | | | | | | | | X | | | | X |
| **M13** | X | | | | | | | | | | | | |

> The grid above captures the numeric modules M1–M13. The **Compliance Guardrail Layer (CG)** (Appendix B) is a **horizontal control layer** (like Module 9) that evaluates rather than owns data — see **10.4** below rather than a row in this numeric matrix.

### 10.4 Automated Compliance Guardrail Layer (cross-cutting)

Operates as a horizontal **evaluator/controller** spanning all phases. It reads from the Staff Nurse Master and the modules and enforces decisions; it does not duplicate master/license/competency data.

```text
        Staff Master (SSOT) · M3 · M8 · M11/LMS · EMR census · M1 plan
                        │              (data feeds)
                        ▼
               COMPLIANCE RULES ENGINE   (CG)
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
     Labor Law      CBAHI Rules     Hospital Policy
      Rules           Rules            Rules
                        │
                        ▼
                COMPLIANCE DECISION → ALLOW / INFORM / WARN / BLOCK
                        │
        ┌───────────────┼──────────────────┐
        ▼               ▼                  ▼
     M4 Deploy      M5 Schedule        M6 Attendance · M7 Leave
     (assignment)   (roster/shift)     (OT/validation)
        │               │                  │
        └───────────────┼──────────────────┘
                        ▼
              Exception mgmt · Audit · Compliance status
                        ▼
                     M9 Dashboards · Payroll (validated export)
```

| Evaluation point | Guarded in | Typical gate |
|---|---|---|
| Shift/roster publish | M5 | hours/rest/OT caps; license/credential/competency; staffing & skill-mix |
| OT approval / payroll export | M6 / Payroll | eligibility, caps, rate, authorization, only compliant OT exported |
| Leave approval | M7 | balance AND staffing coverage |
| Deployment/assignment/transfer | M4 | eligibility, unit authorization, transfer authorization, unsafe assignment |
| Contract/position/pay change | Staff Master / M10 | mismatch & wage-category-transfer rules |
| License/credential/competency change | M3/M8 | re-evaluate affected schedules; alert/auto-replace |

Guardrail decisions, exceptions (reason/risk/mitigation/time-limited/multi-approval), and parameter changes are fully audited and feed Module 9. Full catalogue & DDL in `compliance-guardrails/` (see Appendix B).

---

## 11. Implementation Roadmap

| Wave | Phase | Modules | Rationale |
|---|---|---|---|
| **Wave 1** | C: DEPLOY (Core) | M4: Nursing Deployment, M5: Scheduling & Rostering, M6: Attendance & Time, M7: Leave Management | Highest daily operational impact. Addresses immediate scheduling and attendance pain points |
| **Wave 2** | A: PLAN | M1: Workforce Planning, M9: Analytics (Phase 1) | Establishes planning foundation. Analytics MVP provides early visibility dashboards |
| **Wave 3** | B: ACQUIRE | M2: Recruitment & Hiring, M3: Credentialing & Onboarding | Digitizes hiring pipeline. Requires M1 for requisition source |
| **Wave 4** | D: DEVELOP & RETAIN | M8: Performance & Competency, M10: Contract & Retention, M11: Career Development | Builds on deployed workforce data. Contract tracking is time-sensitive |
| **Wave 5** | E: EXIT & REPLAN | M12: Separation / Exit, M13: Reconciliation, M9: Analytics (Full) | Closes the cycle. Full analytics and predictive capabilities |

**Foundation (All Waves):** Staff Nurse Master Data (SSOT) must be established in Wave 1 as the foundational data layer that all modules reference.

---

## 12. Glossary

| Term | Definition |
|---|---|
| HNWMS | Hospital Nursing Workforce Management System |
| SSOT | Single Source of Truth — the Staff Nurse Master Data serving as the authoritative record |
| SCFHS | Saudi Commission for Health Specialties — regulatory body for licensing healthcare professionals |
| CBAHI | Central Board for Accreditation of Healthcare Institutions — Saudi national accreditation |
| JCI | Joint Commission International — international healthcare accreditation |
| MOH | Ministry of Health — Saudi Arabia |
| Nitaqat | Saudi Saudization program categorizing companies by Saudi/non-Saudi employee ratio |
| GOSI | General Organization for Social Insurance — Saudi social insurance authority |
| EMR / HIS | Electronic Medical Record / Hospital Information System |
| CNO | Chief Nursing Officer |
| FTE | Full-Time Equivalent |
| IDP | Individual Development Plan |
| TNA | Training Needs Analysis |
| Control Tower | Cross-cutting analytics layer (Module 9) monitoring all lifecycle phases |
| Float Pool | Nurses not permanently assigned to a department, deployed as needed |
| Staff ID | Primary unique identifier for each nurse, consistent across all modules |
| Compliance Guardrail Layer | Cross-cutting automated control layer enforcing Saudi Labor Law (HRSD), CBAHI, and Hospital Policy — see Appendix B |
| Guardrail | A rule evaluated before a transaction (schedule/OT/leave/deployment/contract) that ALLOWs, INFORMs, WARNS, or BLOCKs it |
| HRSD | Human Resources and Social Development (Saudi Arabia) — labor-law authority referenced for working-hours/OT/leave rules |
| ALLOW / INFORM / WARN / BLOCK | Guardrail decision outcomes: proceed; proceed with notice; proceed only with approval/escalation; prevent the transaction |

---

---

# Appendix A — Automated Compliance Guardrail Layer (Saudi Labor Law & CBAHI)

> **Full design reference:** This appendix is a concise, authoritative summary. The complete implementation-ready design lives in the **`compliance-guardrails/`** folder of this repository:
> `01_architecture_integration.md` · `02_rules_data_model.md` · `03_compliance_rule_catalog.md` · `04_guardrail_controls_by_module.md` · `05_severity_exceptions_approvals.md` · `06_dashboards_kpis_reports.md` · `07_test_acceptance_criteria.md` · `artifacts/ddl_compliance_engine.sql` · `artifacts/compliance_rule_catalog.csv`.

## A.1 Purpose
Prevent or flag transactions that could create labor-law, credentialing, staffing, or patient-safety risk — rather than relying on HR or Nursing Management to check compliance manually. Saudi Labor Law (HRSD) provides the **legal baseline**; CBAHI provides **healthcare quality & patient-safety** standards; both are operationalized as real-time rules.

## A.2 Rule catalogue (55 rules)
Machine-readable in `compliance_rule_catalog.csv`; full table in `03_compliance_rule_catalog.md`. Groups: **Working hours** (LAB-WH-*), **Rest/shift patterns** (LAB-RS-*), **Overtime** (LAB-OT-*), **Leave** (LAB-LV-*), **Contract/employment** (LAB-CT-*), **CBAHI license/credential/competency/training** (CBA-LIC/CRED/COMP/TRAIN), **CBAHI staffing/skill-mix/safety/quality** (CBA-STAFF/SKILL/SAFE/MED/IP/EM/INCID/DOC/QUAL), **Hospital policy** (HOS-POL-*).

Representative baselines (must be confirmed against current law/policy): 8 h/day & 48 h/week (6 h/day & 36 h/week in Ramadan for applicable workers); overtime = hourly wage + 50% (compensatory leave with consent possible); annual leave ≥ 21 days rising to ≥ 30 after five consecutive years.

## A.3 Engine data model
`compliance_rule` (master, with `compliance_rule_scope` + `compliance_rule_parameter`), `working_calendar_adjustment` (Ramadan/holiday), `eligibility_snapshot`, `shift_candidate`/`leave_request_candidate`, `evaluation_run` + `evaluation_rule_result`, `guardrail_exception_request` + approval, `compliance_audit_log`, `employee_compliance_status`/`shift_compliance_status`, `staffing_requirement`/`skill_mix_rule`. DDL: `artifacts/ddl_compliance_engine.sql`.

## A.4 Severity model & status
🟢 COMPLIANT (ALLOW) · 🔵 ADVISORY (INFORM) · 🟠 WARNING (approval/escalation) · 🔴 BLOCKED (prevent). Every employee and every shift carries an automated status (overall blocked/not-compliant shown per domain). Verdict = strictest applicable rule.

## A.5 Exception management (no silent override)
Exceptions require reason + risk assessment + mitigation, are **time-limited**, go through a severity-based **multi-level approval**, and are fully audited and surfaced on the compliance dashboard. Higher severity ⇒ fewer/higher approvers; license/credential/competency blocks are resolve-first (fix the record) rather than override-by-default.

## A.6 Key acceptance points
- Control point is **Staff Master + Engine before any schedule/OT/leave/deployment**.
- Leave approval checks **balance AND staffing coverage**; schedule approval checks **minimum staffing + skill-mix + shift patterns**, not just individual eligibility.
- Only approved, compliant overtime/hours reach payroll.
- Parameters are configurable & effective-dated (Ramadan auto-recalc); changes are audited.

---

*End of Document — HNWMS Complete System Package v1.0*
