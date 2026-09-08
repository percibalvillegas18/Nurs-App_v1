# Hospital Nursing Workforce Management System (HNWMS)

[![HNWMS Version](https://img.shields.io/badge/HNWMS-v1.0-blue.svg)](HNWMS_Complete_Package.md)
[![Status](https://img.shields.io/badge/Specification-Complete-success.svg)](HNWMS_Complete_Package.md)
[![Accreditation](https://img.shields.io/badge/Compliance-CBAHI%20%7C%20JCI%20%7C%20SCFHS-emerald.svg)](HNWMS_Complete_Package.md)

**Organization:** AIGH — Hospital Nursing Department  
**Architecture:** 5-Phase Closed-Loop Lifecycle + Horizontal Analytics Control Tower  
**Foundation:** Staff Nurse Master Data — Single Source of Truth (SSOT)  
**Primary Specification:** [`HNWMS_Complete_Package.md`](HNWMS_Complete_Package.md)

---

## 🌟 Executive Overview

The **Hospital Nursing Workforce Management System (HNWMS)** is an enterprise healthcare platform that unifies the entire nursing workforce lifecycle—from strategic workforce planning and recruitment through scheduling, clinical deployment, biometric time management, clinical competency, retention, and separation—into a **continuous, self-correcting closed loop**.

```
PLAN ──► ACQUIRE ──► DEPLOY ──► DEVELOP & RETAIN ──► EXIT & REPLAN ──► PLAN (Cycle Restart)
                         ▲                                     │
                         └─────────────────────────────────────┘
                                  CONTINUOUS FEEDBACK

         ╔═════════════════════════════════════════════════════════════╗
         ║        MODULE 9: CROSS-CUTTING CONTROL TOWER                ║
         ║   Real-time event streaming & KPI telemetry across M1-M13   ║
         ╚═════════════════════════════════════════════════════════════╝
```

---

## 🔗 End-to-End Operational Continuum

HNWMS bridges clinical demand directly with financial execution via two mission-critical integration architectures:

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   THE COMPLETE OPERATIONAL CHAIN                                      │
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                       │
│   [ EMR Clinical Demand ]            (Real-time census, ADT events & patient acuity)                  │
│              │                                                                                        │
│              ▼                                                                                        │
│   [ Staffing Requirement ]           (Module 1: Dynamic nursing FTE & ratio calculations)             │
│              │                                                                                        │
│              ▼                                                                                        │
│   [ Nursing Schedule & Roster ]      (Modules 4 & 5: Deployment, shift assignment & float pool)       │
│              │                                                                                        │
│              ▼                                                                                        │
│   [ Attendance & Clocking ]          (Module 6: Biometric time tracking & exception detection)        │
│              │                                                                                        │
│              ▼                                                                                        │
│   [ Overtime & Leave Validation ]    (Modules 6 & 7: Manager approval, shift differentials & leave)   │
│              │                                                                                        │
│              ▼                                                                                        │
│   [ Payroll Execution ]              (Bidirectional Payroll API: Gross pay, deductions & WPS)         │
│              │                                                                                        │
│              ▼                                                                                        │
│   [ Financial Ledger & Reporting ]   (Hospital Finance ERP & Module 9 Control Tower analytics)        │
│                                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. EMR Interoperability — Clinical Demand Integration
* **Source:** Electronic Medical Record (EMR / HIS) via HL7 v2 ADT & FHIR R4.
* **Function:** Real-time patient census, admission/discharge/transfer (ADT) event streaming, 4-tier clinical acuity scoring, and automated nurse-to-patient ratio enforcement.
* **Value:** Replaces static scheduling with **live, demand-driven staffing** to safeguard patient outcomes and prevent nurse burnout.

### 2. Bidirectional Payroll APIs — Financial Execution
* **Source/Destination:** Integration API Gateway to Hospital Payroll / Finance & Wage Protection System (WPS).
* **Outbound:** Manager-validated regular hours, approved overtime tiers, shift differentials (night/weekend/on-call), and unpaid absence deductions.
* **Inbound:** Disbursement confirmations, batch status, rejection alerts, and reconciliation logs.
* **Value:** Eliminates duplicate data re-entry and payroll friction, creating an unbroken financial audit trail.

---

## 🏛️ Core Architectural Pillars

### 1. Staff Nurse Master Data (SSOT)
- **Principle:** `One Nurse → One Staff Master Record (Staff ID) → Multiple Workforce Processes`
- **21 Data Domains:** Identity, Employment, Organization, Job, Workforce, Professional, License, Credentials, Certification, Competency, Deployment, Contract, Scheduling, Attendance, Leave, Performance, Career, Retention, Separation, Access, and Audit.
- **Effective-Dated Records:** Temporal history tracking for ward transfers, promotions, and status changes without data loss.

### 2. 13-Module Functional Architecture

| Phase | Module | Name | Core Focus |
|---|---|---|---|
| **Phase A: PLAN** | **M1** | Workforce Planning | Demand forecasting, bed capacity, acuity ratios, position budgets |
| **Phase B: ACQUIRE** | **M2** | Recruitment & Hiring | Requisitions, applicant tracking, interview evaluation, contract offers |
| | **M3** | Credentialing & Onboarding | SCFHS verification, BLS/ACLS credentials, medical clearance, orientation |
| **Phase C: DEPLOY** | **M4** | Nursing Deployment | Ward/unit assignment, qualification gating, float pool management |
| | **M5** | Scheduling & Rostering | Monthly rosters, rotation rules, coverage matrix, gap fulfillment |
| | **M6** | Attendance & Time Mgmt | Biometric punch processing, tardiness/no-show exceptions, overtime |
| | **M7** | Leave Management | Annual/sick/maternity leave balances, coverage checks, return-to-work |
| **Phase D: DEVELOP & RETAIN** | **M8** | Performance & Competency | Role appraisals, clinical skill sign-offs, Individual Development Plans |
| | **M10** | Contract & Retention | 7-tier expiry alerts, weighted renewal scoring (100%), retention plans |
| | **M11** | Career Development | Clinical ladders, critical position succession matrix, LMS integrations |
| **CONTROL TOWER** | **M9** | Workforce Analytics | Horizontal telemetry, staffing gap alerts, turnover, CBAHI/MOH KPIs |
| **Phase E: EXIT & REPLAN** | **M12** | Separation / Exit Mgmt | Resignation/termination workflows, clearance checklist, EOSB settlements |
| | **M13** | Workforce Reconciliation | Plan-vs-actual variance analysis, closed-loop replanning feedback to M1 |

---

## ⚖️ Regulatory & Standards Compliance

The system is built ground-up to comply with:
- **SCFHS (Saudi Commission for Health Specialties):** Automated license verification and 180-day expiry alert pipeline.
- **CBAHI & JCI:** Unit-level nurse-to-patient ratios, mandatory clinical competencies, and patient safety indicators.
- **Saudi Labor Law:** Working hours limits, mandatory rest intervals, statutory leaves, overtime premium calculation, and End-of-Service Benefits (EOSB).
- **Nitaqat / GOSI:** Saudization tracking and social insurance reporting.

---

## 🗺️ Implementation Roadmap

```
Wave 1 (Foundation): SSOT Master Data + M4 (Deploy) + M5 (Schedule) + M6 (Attendance) + M7 (Leave)
Wave 2 (Planning):   M1 (Planning) + M9 (Control Tower MVP) + EMR Interoperability Gateway
Wave 3 (Acquisition):M2 (Recruitment) + M3 (Credentialing & SCFHS Portal)
Wave 4 (Capability): M8 (Competency) + M10 (Contract Renewal) + M11 (Career Ladder)
Wave 5 (Closed Loop):M12 (Exit & EOSB) + M13 (Reconciliation Loop) + Full M9 Analytics
```

---

## 📖 Complete Specification

For the full detailed specification including submodule breakdowns, mathematical formulas, data dictionary, workflow diagrams, and integration schemas, consult [`HNWMS_Complete_Package.md`](HNWMS_Complete_Package.md).
