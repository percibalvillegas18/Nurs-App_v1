#!/usr/bin/env python3
"""Load Wave P1 Org Directory from the classed seed + org chart. Also write the desk audit pack.

Physical floor counts are NOT invented — walk_status is always NOT_WALKED.
"""
from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from um import DEMO_PASSWORD, DOC_TYPES, hash_password, slug_username

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "implementation-plan" / "artifacts"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SCHEMA = HERE / "schema.sql"
SEED_CSV = ART / "normalized_department_unit.csv"
DB = DATA / "org_directory.db"
EFFECTIVE = "2026-09-09"

DEPT_CODES = {
    "EMERGENCY & ACUTE CARE": "EMRG",
    "SURGICAL & PERIOPERATIVE SERVICES": "SURG",
    "CRITICAL CARE & INTENSIVE SERVICES": "CRIT",
    "GENERAL & SPECIALTY SERVICES": "GENS",
}
GROUP_CARE = {
    "EMERGENCY": "EMERGENCY",
    "PERIOPERATIVE": "PERIOPERATIVE",
    "CRITICAL CARE": "CRITICAL_CARE",
    "ACUTE GENERAL CARE": "INPATIENT_WARD",
    "SPECIALIZED & DIAGNOSTIC": "AMBULATORY",
    "SECURE CARE": "INPATIENT_WARD",
    "SUPPORT & ADMINISTRATIVE SERVICES": "SUPPORT",
}

# Org chart → unit coverage (DQ-14 proposed, not signed)
LINE_UNITS = {
    "Emergency Nursing": ["ED-RESUS", "ED-FTOBS", "ED-MC", "ED-NAV", "ED-ADMIN", "UCC"],
    "Operating Room Nursing": ["OR", "PACU", "PLASTER", "OR-ADMIN"],
    "ICU / Critical Care": ["ICU-MAIN", "ICU-EXT", "HDU", "ICU-EXT-2"],
    "Inpatient Nursing": ["W3A", "W4A", "W4B", "W5B", "REHAB", "AKU", "JAIL"],
    "Pediatric Nursing": ["PEDS"],
    "Maternity / Obstetric Nursing": ["LND", "OBGYN"],
    "Specialty Nursing Units": [
        "NBS", "DAY-SURG", "DAY-CARE", "OPD", "RRT", "PLASTER-2", "EEG",
        "CLINICS", "ENDO", "BLOOD", "RAD", "DIAB", "DISCH", "ED-NAV-2",
        "NIL", "ORTHO-TECH", "ADMIN-SUP", "MCH-COORD", "GEN-SUP",
    ],
}

ORG_NODES = [
    # org_code, parent_code, name, node_type
    ("HOSP", None, "Hospital Director", "EXEC"),
    ("CMO", "HOSP", "Medical Director / Chief Medical Officer", "EXEC"),
    ("DON", "HOSP", "Director of Nursing", "NURSING_LINE"),
    ("OPS", "HOSP", "Administration / Operations Director", "EXEC"),
    ("QUAL", "HOSP", "Quality & Patient Safety", "EXEC"),
    ("PHARM", "HOSP", "Pharmacy & Diagnostic Services", "EXEC"),
    ("IT", "HOSP", "IT / Health Informatics", "EXEC"),
    ("PCS", "HOSP", "Patient & Corporate Services", "EXEC"),
    ("ADON", "DON", "Deputy / Assistant Director of Nursing", "NURSING_LINE"),
    ("NOPS", "ADON", "Nursing Operations", "FUNCTION"),
    ("NINPT", "NOPS", "Inpatient Nursing", "FUNCTION"),
    ("NICU", "NOPS", "ICU / Critical Care", "FUNCTION"),
    ("NED", "NOPS", "Emergency Nursing", "FUNCTION"),
    ("NOR", "NOPS", "Operating Room Nursing", "FUNCTION"),
    ("NPED", "NOPS", "Pediatric Nursing", "FUNCTION"),
    ("NMAT", "NOPS", "Maternity / Obstetric Nursing", "FUNCTION"),
    ("NSPC", "NOPS", "Specialty Nursing Units", "FUNCTION"),
    ("NEDU", "DON", "Nursing Education & Development", "FUNCTION"),
    ("NQLT", "DON", "Nursing Quality & Patient Safety", "FUNCTION"),
    ("NINF", "DON", "Nursing Informatics", "FUNCTION"),
    ("NWFM", "DON", "Nursing Administration / Workforce Management", "FUNCTION"),
    ("WMP", "NWFM", "Manpower Planning", "FUNCTION"),
    ("WREC", "NWFM", "Recruitment & Hiring", "FUNCTION"),
    ("WSMD", "NWFM", "Staff Nurse Master Data", "FUNCTION"),
    ("WLIC", "NWFM", "License & Credential Management", "FUNCTION"),
    ("WSCH", "NWFM", "Scheduling & Staff Allocation", "FUNCTION"),
    ("WATT", "NWFM", "Attendance Management", "FUNCTION"),
    ("WLV", "NWFM", "Leave Management", "FUNCTION"),
    ("WOT", "NWFM", "Overtime Management", "FUNCTION"),
    ("WCR", "NWFM", "Contract Renewal", "FUNCTION"),
    ("WAN", "NWFM", "Workforce Analytics", "FUNCTION"),
]

POSITIONS = [
    ("HOSPITAL_DIR", "HOSP", "Hospital Director", "E1"),
    ("CMO", "CMO", "Medical Director / CMO", "E2"),
    ("DON", "DON", "Director of Nursing", "L1"),
    ("OPS_DIR", "OPS", "Administration / Operations Director", "E2"),
    ("QUALITY_LEAD", "QUAL", "Quality & Patient Safety Lead", "E2"),
    ("IT_DIR", "IT", "IT / Health Informatics Director", "E2"),
    ("PHARM_LEAD", "PHARM", "Pharmacy / Diagnostic Services Lead", "E2"),
    ("PCS_LEAD", "PCS", "Patient / Corporate Services Lead", "E2"),
    ("ADON", "ADON", "Deputy / Assistant Director of Nursing", "L2"),
    ("WORKFORCE_MGR", "NWFM", "Nursing Administration / Workforce Manager", "L2"),
    ("EDUC_MGR", "NEDU", "Nursing Education Manager", "L2"),
    ("QUALITY_MGR", "NQLT", "Nursing Quality Manager", "L2"),
    ("INFORMATICS_MGR", "NINF", "Nursing Informatics Manager", "L2"),
    ("NURSING_OPS", "NOPS", "Nursing Operations", "L2"),
    ("UNIT_MANAGER", "NOPS", "Nursing Manager / Unit Manager", "L3"),
    ("CHARGE_NURSE", "NOPS", "Charge Nurse", "L4"),
    ("TEAM_LEADER", "NOPS", "Team Leader / Senior Nurse", "L5"),
    ("STAFF_NURSE", "NOPS", "Staff Nurse", "L6"),
    ("NURSING_ASSISTANT", "NOPS", "Nursing Assistant", "L7"),
]

ROLES = [
    ("SYS_ADMIN", "System / Integration Admin", "—", "FACILITY"),
    ("ORG_ADMIN", "Org Directory Admin", "—", "FACILITY"),
    ("HOUSE_VIEW", "Census / house-board viewer", "—", "FACILITY"),
    ("ADT_CLERK", "ADT / Registration Clerk", "frontline", "DEPARTMENT"),
    ("BED_COORD", "Bed Coordinator / Patient Placement", "P3", "FACILITY"),
    ("HOUSE_SUP", "House Supervisor / Nursing Operations", "L2/L3", "FACILITY"),
    ("CHARGE", "Charge Nurse", "L4", "UNIT"),
    ("UNIT_MGR", "Unit / Nursing Manager", "L3", "DEPARTMENT"),
    ("ADON", "Deputy / Assistant DON", "L2", "FACILITY"),
    ("DON", "Director of Nursing", "L1", "FACILITY"),
    ("SCHEDULER", "Workforce Mgmt / Scheduler", "—", "DEPARTMENT"),
    ("WORKFORCE_MGR", "Nursing Administration / Workforce Manager", "L2", "FACILITY"),
    ("EDUC_MGR", "Nursing Education Manager", "L2", "FACILITY"),
    ("INFORMATICS", "Nursing Informatics Manager", "L2", "FACILITY"),
    ("HR", "HR / Payroll", "—", "DEPARTMENT"),
    ("AUDIT", "Regulatory / Audit / Nursing Quality", "—", "FACILITY"),
    ("TEAM_LEAD", "Team Leader / Senior Nurse", "L5", "UNIT"),
    ("STAFF", "Staff Nurse (self-service)", "L6", "UNIT"),
    ("NURSE_ASSIST", "Nursing Assistant (self-service)", "L7", "UNIT"),
]

PERMS = [
    ("ORG_READ", "Org Directory", "Read facility/dept/unit"),
    ("ORG_WRITE", "Org Directory", "CRUD taxonomy"),
    ("BED_READ", "Bed Mgmt", "View bed board / census (not assign)"),
    ("BED_REQUEST", "Bed Mgmt", "Request a bed (cannot assign/release)"),
    ("BED_BLOCK", "Bed Mgmt", "Block / out-of-service / isolation hold"),
    ("BED_CONTROL", "Bed Mgmt", "Assign / release / place a patient in a bed"),
    ("ADT_WRITE", "ADT", "Admit/transfer/discharge"),
    ("SCHED_WRITE", "Scheduling", "Publish roster"),
    ("APPROVE", "Governance", "Escalation / sign-off"),
    ("ANALYTICS_READ", "Analytics", "Dashboards"),
    ("AUDIT_READ", "Audit", "Read audit log"),
]

ROLE_PERMS = {
    "SYS_ADMIN": ["ORG_READ", "ORG_WRITE", "BED_READ", "BED_CONTROL", "BED_BLOCK", "ADT_WRITE", "SCHED_WRITE", "APPROVE", "AUDIT_READ", "ANALYTICS_READ"],
    "ORG_ADMIN": ["ORG_READ", "ORG_WRITE", "AUDIT_READ"],
    "HOUSE_VIEW": ["ORG_READ", "BED_READ", "ANALYTICS_READ"],
    "ADT_CLERK": ["ORG_READ", "ADT_WRITE", "BED_READ", "BED_REQUEST"],
    "BED_COORD": ["ORG_READ", "BED_READ", "BED_CONTROL", "BED_BLOCK", "ADT_WRITE"],
    "HOUSE_SUP": ["ORG_READ", "BED_READ", "BED_CONTROL", "BED_BLOCK", "ADT_WRITE", "APPROVE"],
    "CHARGE": ["ORG_READ", "BED_READ", "BED_CONTROL", "BED_BLOCK", "ADT_WRITE"],
    "UNIT_MGR": ["ORG_READ", "BED_READ", "BED_BLOCK", "APPROVE", "ANALYTICS_READ"],
    "ADON": ["ORG_READ", "BED_READ", "APPROVE", "AUDIT_READ", "ANALYTICS_READ"],
    "DON": ["ORG_READ", "BED_READ", "APPROVE", "AUDIT_READ", "ANALYTICS_READ"],
    "SCHEDULER": ["ORG_READ", "SCHED_WRITE", "BED_READ"],
    "WORKFORCE_MGR": ["ORG_READ", "SCHED_WRITE", "BED_READ", "ANALYTICS_READ"],
    "EDUC_MGR": ["ORG_READ", "ANALYTICS_READ"],
    "INFORMATICS": ["ORG_READ", "ANALYTICS_READ", "AUDIT_READ"],
    "HR": ["ORG_READ"],
    "AUDIT": ["ORG_READ", "AUDIT_READ", "ANALYTICS_READ"],
    "TEAM_LEAD": ["ORG_READ", "BED_READ", "BED_REQUEST"],
    "STAFF": ["ORG_READ", "BED_READ"],
    "NURSE_ASSIST": ["ORG_READ"],
}

HOUSE = [("HOUSE_VIEW", "FACILITY", "AIGH")]


def slot(code, name, title, category, notes, grants):
    """System-user slot. persona_code stays; display_name is swapped for a real person later."""
    return {
        "code": code,
        "name": name,
        "title": title,
        "category": category,
        "notes": notes,
        "grants": grants,
    }


# Every HNWMS *system user* slot (not Staff Master — no 200 staff nurses).
# Rename display_name on People when the real employee is known.
PERSONAS = [
    slot("demo.slot.hospdir", "Faisal Al-Saud", "Hospital Director", "Leadership",
         "Analytics / house census only.", [("HOUSE_VIEW", "FACILITY", "AIGH")]),
    slot("demo.slot.don", "Layla Al-Saud", "Director of Nursing", "Leadership",
         "Governance and approvals. Does not place patients.", [("DON", "FACILITY", "AIGH")]),
    slot("demo.slot.adon", "Reem Al-Faisal", "Deputy / Assistant DON", "Leadership",
         "Operations oversight. Does not place patients.", [("ADON", "FACILITY", "AIGH")]),
    slot("demo.slot.housesup", "Mona Al-Ghamdi", "House Supervisor", "Operations",
         "Night/surge bed control, facility-wide. No roster publish.", [("HOUSE_SUP", "FACILITY", "AIGH")]),
    slot("demo.slot.bedcoord", "Khalid Al-Otaibi", "Bed Coordinator", "Operations",
         "Hospital-wide patient placement.", [("BED_COORD", "FACILITY", "AIGH")]),
    slot("demo.slot.wfmanager", "Hessa Al-Rashid", "Workforce Manager", "Workforce",
         "Facility roster oversight. No BED_CONTROL (SoD).", [("WORKFORCE_MGR", "FACILITY", "AIGH")]),
    slot("demo.slot.educ", "Aisha Al-Anzi", "Nursing Education Manager", "Workforce",
         "Education / competency. Read-only locations.", [("EDUC_MGR", "FACILITY", "AIGH")] + HOUSE),
    slot("demo.slot.quality", "Nada Al-Shehri", "Nursing Quality Manager", "Workforce",
         "Nursing quality, safety, audit read.", [("AUDIT", "FACILITY", "AIGH")]),
    slot("demo.slot.informatics", "Tariq Al-Malki", "Nursing Informatics Manager", "Workforce",
         "Systems and dashboards. Not Org Admin write.", [("INFORMATICS", "FACILITY", "AIGH")]),
    slot("demo.slot.orgadmin", "Majed Al-Qahtani", "Org Directory Admin", "System",
         "Taxonomy CRUD. No bed control.", [("ORG_ADMIN", "FACILITY", "AIGH")]),
    slot("demo.slot.sysadmin", "Ibrahim Al-Nemer", "System Admin (break-glass)", "System",
         "SoD waived; every use must be audited.", [("SYS_ADMIN", "FACILITY", "AIGH")]),
    slot("demo.slot.hr", "Omar Al-Harthi", "HR / Payroll", "System",
         "Location read-only.", [("HR", "FACILITY", "AIGH")]),
    slot("demo.slot.audit", "Sami Al-Dossari", "Regulatory / Audit", "System",
         "External/regulatory audit read.", [("AUDIT", "FACILITY", "AIGH")]),
    slot("demo.slot.um.emrg", "Bandar Al-Harbi", "Unit Manager, Emergency", "Unit managers",
         "Approves / blocks in EMRG. Does not place.",
         [("UNIT_MGR", "DEPARTMENT", "EMRG")] + HOUSE),
    slot("demo.slot.um.surg", "Maha Al-Otaibi", "Unit Manager, Perioperative", "Unit managers",
         "Approves / blocks in SURG. Does not place.",
         [("UNIT_MGR", "DEPARTMENT", "SURG")] + HOUSE),
    slot("demo.slot.um.crit", "Waleed Al-Mutairi", "Unit Manager, Critical Care", "Unit managers",
         "Approves / blocks in CRIT. Does not place.",
         [("UNIT_MGR", "DEPARTMENT", "CRIT")] + HOUSE),
    slot("demo.slot.um.gens", "Ahmed Al-Mutairi", "Unit Manager, General & Specialty", "Unit managers",
         "Approves / blocks in GENS. Does not place.",
         [("UNIT_MGR", "DEPARTMENT", "GENS")] + HOUSE),
    slot("demo.slot.um.peds", "Lina Al-Zahrani", "Unit Manager, Pediatrics", "Unit managers",
         "Unit-scoped to PEDS (GENS is shared).",
         [("UNIT_MGR", "UNIT", "PEDS")] + HOUSE),
    slot("demo.slot.um.mat", "Hana Al-Ghamdi", "Unit Manager, Maternity", "Unit managers",
         "LND + Obgyne. Does not place.",
         [("UNIT_MGR", "UNIT", "LND"), ("UNIT_MGR", "UNIT", "OBGYN")] + HOUSE),
    slot("demo.slot.sched.emrg", "Sara Al-Dosari", "Scheduler, Emergency", "Schedulers",
         "Publishes ED roster. Cannot move beds (SoD).",
         [("SCHEDULER", "DEPARTMENT", "EMRG")] + HOUSE),
    slot("demo.slot.sched.surg", "Nouf Al-Shammari", "Scheduler, Perioperative", "Schedulers",
         "Publishes OR/PACU roster. Cannot move beds.",
         [("SCHEDULER", "DEPARTMENT", "SURG")] + HOUSE),
    slot("demo.slot.sched.crit", "Faisal Al-Harbi", "Scheduler, Critical Care", "Schedulers",
         "Publishes ICU/HDU roster. Cannot move beds.",
         [("SCHEDULER", "DEPARTMENT", "CRIT")] + HOUSE),
    slot("demo.slot.sched.gens", "Dana Al-Qahtani", "Scheduler, General & Specialty", "Schedulers",
         "Publishes GENS roster. Cannot move beds.",
         [("SCHEDULER", "DEPARTMENT", "GENS")] + HOUSE),
    slot("demo.slot.clerk.emrg", "Yousef Al-Shammari", "ADT Clerk, Emergency", "ADT clerks",
         "May request a bed; Bed Coordinator assigns.",
         [("ADT_CLERK", "DEPARTMENT", "EMRG")] + HOUSE),
    slot("demo.slot.clerk.surg", "Salman Al-Harthi", "ADT Clerk, Perioperative", "ADT clerks",
         "PACU/OR registration. Cannot assign beds.",
         [("ADT_CLERK", "DEPARTMENT", "SURG")] + HOUSE),
    slot("demo.slot.clerk.gens", "Bader Al-Dossary", "ADT Clerk, Inpatient", "ADT clerks",
         "Ward ADT. Cannot assign beds.",
         [("ADT_CLERK", "DEPARTMENT", "GENS")] + HOUSE),
    slot("demo.slot.clerk.crit", "Nasser Al-Anzi", "ADT Clerk, Critical Care", "ADT clerks",
         "ICU ADT. Cannot assign beds.",
         [("ADT_CLERK", "DEPARTMENT", "CRIT")] + HOUSE),
]

# Charge on every operational bedded unit + OR. Skip ICU-EXT-2 (DQ-1a pending merge).
CHARGE_SLOTS = [
    ("ED-RESUS", "Maryam Al-Harbi", "Charge Nurse, ED Resuscitation"),
    ("ED-FTOBS", "Jawaher Al-Mutairi", "Charge Nurse, ED Fast-track / Observation"),
    ("ED-MC", "Amal Al-Qahtani", "Charge Nurse, ED Maternal & Child"),
    ("UCC", "Turki Al-Dosari", "Charge Nurse, Urgent Care"),
    ("OR", "Abdullah Al-Otaibi", "Charge Nurse, Operating Room"),
    ("PACU", "Munira Al-Shehri", "Charge Nurse, PACU"),
    ("ICU-MAIN", "Noura Al-Qahtani", "Charge Nurse, ICU Main"),
    ("ICU-EXT", "Khaled Al-Ghamdi", "Charge Nurse, ICU Extension"),
    ("HDU", "Reem Al-Harthi", "Charge Nurse, HDU"),
    ("W3A", "Fatimah Al-Harbi", "Charge Nurse, Ward 3A"),
    ("W4A", "Sara Al-Mutairi", "Charge Nurse, Ward 4A"),
    ("W4B", "Nouf Al-Anzi", "Charge Nurse, Ward 4B"),
    ("W5B", "Ali Al-Shammari", "Charge Nurse, Ward 5B"),
    ("REHAB", "Hind Al-Rashid", "Charge Nurse, Rehabilitation"),
    ("PEDS", "Lama Al-Saud", "Charge Nurse, Pediatrics"),
    ("LND", "Amani Al-Dosari", "Charge Nurse, Labor & Delivery"),
    ("OBGYN", "Ghada Al-Otaibi", "Charge Nurse, Obgyne"),
    ("AKU", "Yusuf Al-Malki", "Charge Nurse, AKU"),
    ("JAIL", "Majid Al-Harbi", "Charge Nurse, Jail Ward"),
]
for unit, name, title in CHARGE_SLOTS:
    PERSONAS.append(slot(
        f"demo.slot.charge.{unit.lower()}",
        name, title, "Charge nurses",
        f"Places patients on {unit} only. House census via HOUSE_VIEW.",
        [("CHARGE", "UNIT", unit)] + HOUSE,
    ))

PERSONAS += [
    slot("demo.slot.teamlead.w3a", "Sultana Al-Qahtani", "Team Leader, Ward 3A", "Self-service sample",
         "Placeholder for L5 self-service. Not Staff Master.",
         [("TEAM_LEAD", "UNIT", "W3A")] + HOUSE),
    slot("demo.slot.staff.w3a", "Hassan Al-Ghamdi", "Staff Nurse, Ward 3A", "Self-service sample",
         "One sample L6 login — not the full nurse roster.",
         [("STAFF", "UNIT", "W3A")]),
    slot("demo.slot.assist.w3a", "Fawzia Al-Harthi", "Nursing Assistant, Ward 3A", "Self-service sample",
         "One sample L7 login — not the full assistant roster.",
         [("NURSE_ASSIST", "UNIT", "W3A")]),
]

VOCAB = [
    ("care_setting", "INPATIENT_WARD", "Inpatient ward"),
    ("care_setting", "CRITICAL_CARE", "Critical care"),
    ("care_setting", "EMERGENCY", "Emergency"),
    ("care_setting", "PERIOPERATIVE", "Perioperative"),
    ("care_setting", "AMBULATORY", "Ambulatory"),
    ("care_setting", "DIAGNOSTIC", "Diagnostic"),
    ("care_setting", "SUPPORT", "Support"),
    ("capacity_class", "INPATIENT_LICENSED", "Licensed inpatient bed"),
    ("capacity_class", "ED_STRETCHER", "ED stretcher / observation"),
    ("capacity_class", "PACU_BAY", "PACU recovery bay"),
    ("capacity_class", "OR_TABLE", "Operating table"),
    ("capacity_class", "PROCEDURE_ROOM", "Procedure room"),
    ("capacity_class", "AMBULATORY_CHAIR", "Clinic chair / slot"),
    ("capacity_class", "SUPPORT", "Non-clinical support"),
    ("unit_type", "WARD", "Ward"),
    ("unit_type", "SECURE_WARD", "Secure / jail ward"),
    ("unit_type", "ICU", "ICU"),
    ("unit_type", "HDU", "High dependency"),
    ("unit_type", "LDR", "Labor & delivery"),
    ("unit_type", "ED", "Emergency department"),
    ("unit_type", "UCC", "Urgent care"),
    ("unit_type", "OR", "Operating room"),
    ("unit_type", "PACU", "PACU"),
    ("unit_type", "CLINIC", "Clinic"),
    ("unit_type", "DIAGNOSTIC", "Diagnostic"),
    ("unit_type", "PROCEDURE", "Procedure"),
    ("unit_type", "THERAPY", "Therapy"),
    ("unit_type", "SUPPORT", "Support"),
    ("bed_status", "READY", "Ready"),
    ("bed_status", "RESERVED", "Reserved"),
    ("bed_status", "OCCUPIED", "Occupied"),
    ("bed_status", "CLEANING", "Cleaning"),
    ("bed_status", "OUT_OF_SERVICE", "Out of service"),
    ("bed_status", "BLOCKED", "Blocked"),
    ("bed_class", "PRIVATE", "Private"),
    ("bed_class", "SHARED", "Shared"),
    ("bed_class", "ISOLATION", "Isolation"),
]


def nint(v):
    s = (v or "").strip()
    return int(s) if s else None


def desk_recommendation(row: dict) -> tuple[str, str]:
    code, flag, cls = row["unit_code"], row.get("dq_flag") or "", row["capacity_class"]
    if flag == "DQ1A_PENDING":
        return "PROPOSE_MERGE", "Identical 14-bed twin of ICU-EXT; default merge unless floor walk finds a second site."
    if flag == "DQ1B_PENDING":
        return "PROPOSE_MERGE", "Identical 9-count twin of PLASTER; default merge unless a second plaster suite exists."
    if flag in ("DQ2_PENDING", "DQ2_NON_BEDDED"):
        return "KEEP_NON_BEDDED", "Navigation is not licensed beds. Confirm one vs two desks on the walk."
    if flag == "DQ9_APPLIED":
        return "KEEP_SUPPORT", "Admin/support numeric Bed already removed from assignable."
    if flag == "DQ12_RECLASS":
        return "KEEP_SECURE_INPATIENT", "Jail Ward treated as secure inpatient — confirm lock-ward footprint."
    if flag == "DQ12_REPARENT":
        return "KEEP_ED_STRETCHER", "UCC re-parented to Emergency — confirm it sits in the ED family on the floor."
    if cls == "INPATIENT_LICENSED":
        return "COUNT_LICENSED_BEDS", "Walk and count licensed vs operational beds."
    if cls == "ED_STRETCHER":
        return "COUNT_STRETCHERS", "Count stretchers/bays; do not add to MOH licensed inpatient."
    if cls in ("OR_TABLE", "PACU_BAY", "PROCEDURE_ROOM", "AMBULATORY_CHAIR"):
        return "COUNT_RESOURCES_NOT_BEDS", f"Verify {cls} count; not ADT licensed beds."
    return "CONFIRM_NO_BEDS", "Confirm no assignable patient beds."


def load_units():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    DATA.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text())
    cur = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cur.execute(
        """INSERT INTO facility (facility_code, name, region, city, mrn_prefix, licensor, status)
           VALUES ('AIGH','AIGH Hospital','Riyadh Region','Riyadh','AIGH','MOH / CBAHI (confirm)', 'ACTIVE')"""
    )
    facility_id = cur.lastrowid

    units = load_units()
    dept_ids = {}
    for name, code in DEPT_CODES.items():
        dtype = "BEDDED"
        cur.execute(
            "INSERT INTO department (department_code, facility_id, name, department_type) VALUES (?,?,?,?)",
            (code, facility_id, name, dtype),
        )
        dept_ids[name] = cur.lastrowid

    group_ids = {}
    for r in units:
        key = (r["department"], r["unit_group"])
        if key in group_ids:
            continue
        cur.execute(
            "INSERT INTO unit_group (department_id, name, care_setting) VALUES (?,?,?)",
            (dept_ids[r["department"]], r["unit_group"], GROUP_CARE.get(r["unit_group"], r["care_setting"])),
        )
        group_ids[key] = cur.lastrowid

    for r in units:
        src = nint(r["source_bed_count"])
        cap = nint(r["bed_capacity"]) or 0
        licensed = cap if r["capacity_class"] == "INPATIENT_LICENSED" else 0
        cur.execute(
            """INSERT INTO nursing_unit
               (unit_code, department_id, unit_group_id, unit_name, unit_type, care_setting,
                capacity_class, source_bed_count, resource_capacity, licensed_capacity,
                is_bedded, dq_flag, effective_from, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                r["unit_code"], dept_ids[r["department"]], group_ids[(r["department"], r["unit_group"])],
                r["unit_name"], r["unit_type"], r["care_setting"], r["capacity_class"],
                src, cap, licensed, 1 if r["is_bedded"] == "yes" else 0,
                r.get("dq_flag") or None, EFFECTIVE, "ACTIVE",
            ),
        )
        rec, notes = desk_recommendation(r)
        cur.execute(
            """INSERT INTO desk_audit
               (unit_code, walk_status, physical_exists, separate_footprint, physical_beds,
                licensed_from_register, operational_today, clinical_or_support, second_site,
                desk_recommendation, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                r["unit_code"], "NOT_WALKED", "UNKNOWN", "UNKNOWN", None, None, None,
                "BEDDED" if r["is_bedded"] == "yes" else "SUPPORT",
                "PENDING" if r["unit_code"] in ("ICU-EXT-2", "PLASTER-2", "ED-NAV-2") else "N/A",
                rec, notes,
            ),
        )

    code_to_id = {}
    for code, parent, name, ntype in ORG_NODES:
        pid = code_to_id[parent] if parent else None
        cur.execute(
            "INSERT INTO org_node (parent_org_node_id, org_code, name, node_type) VALUES (?,?,?,?)",
            (pid, code, name, ntype),
        )
        code_to_id[code] = cur.lastrowid

    for pcode, ncode, title, level in POSITIONS:
        cur.execute(
            "INSERT INTO workforce_position (position_code, org_node_id, title, position_level) VALUES (?,?,?,?)",
            (pcode, code_to_id[ncode], title, level),
        )

    unit_set = {r["unit_code"] for r in units}
    for line, codes in LINE_UNITS.items():
        for uc in codes:
            if uc not in unit_set:
                raise SystemExit(f"coverage references missing unit {uc}")
            cur.execute(
                """INSERT INTO coverage_template
                   (clinical_line, position_code, scope_type, unit_code, status, notes)
                   VALUES (?,?,?,?,?,?)""",
                (line, "UNIT_MANAGER", "UNIT", uc, "PROPOSED", "DQ-14 proposed from org-chart clinical line"),
            )

    for code, title, level, scope in ROLES:
        cur.execute(
            "INSERT INTO role (role_code, title, level, data_scope) VALUES (?,?,?,?)",
            (code, title, level, scope),
        )
    for code, module, desc in PERMS:
        cur.execute(
            "INSERT INTO permission (perm_code, module, description) VALUES (?,?,?)",
            (code, module, desc),
        )
    role_ids = {r[0]: r[1] for r in cur.execute("SELECT role_code, role_id FROM role")}
    perm_ids = {r[0]: r[1] for r in cur.execute("SELECT perm_code, permission_id FROM permission")}
    for rc, plist in ROLE_PERMS.items():
        for pc in plist:
            cur.execute(
                "INSERT INTO role_permission (role_id, permission_id) VALUES (?,?)",
                (role_ids[rc], perm_ids[pc]),
            )
    cur.executemany(
        "INSERT INTO vocabulary (domain, code, label) VALUES (?,?,?)", VOCAB
    )
    rbac_sql = (ROOT / "rbac" / "schema.sql").read_text()
    conn.executescript(rbac_sql)
    cur.execute(
        """INSERT INTO sod_rule (perm_a, perm_b, message, waive_roles)
           VALUES ('BED_CONTROL','SCHED_WRITE','Bed control and scheduling must not be held by the same person','SYS_ADMIN')"""
    )
    for p in PERSONAS:
        cur.execute(
            """INSERT INTO persona (persona_code, display_name, job_title, category, is_demo, notes)
               VALUES (?,?,?,?,1,?)""",
            (p["code"], p["name"], p["title"], p["category"], p["notes"]),
        )
        pid = cur.lastrowid
        for role, stype, scode in p["grants"]:
            cur.execute(
                """INSERT INTO role_grant (persona_id, role_id, scope_type, scope_code, effective_from, status)
                   VALUES (?,?,?,?,?, 'ACTIVE')""",
                (pid, role_ids[role], stype, scode, EFFECTIVE),
            )
    conn.executescript((HERE / "um_schema.sql").read_text())
    cur.executemany(
        "INSERT INTO doc_type (doc_code, label, category, notes) VALUES (?,?,?,?)", DOC_TYPES
    )
    used_names: set[str] = set()
    people_rows = list(cur.execute("SELECT persona_id, persona_code, display_name FROM persona"))
    for pid, code, name in people_rows:
        uname = slug_username(name, code, used_names)
        salt, hashed = hash_password(DEMO_PASSWORD)
        cur.execute(
            """INSERT INTO app_user (persona_id, username, password_salt, password_hash, status)
               VALUES (?,?,?,?, 'ACTIVE')""",
            (pid, uname, salt, hashed),
        )
    cur.execute(
        "INSERT INTO registry_event (event_time, event_type, actor, detail) VALUES (?,?,?,?)",
        (now, "SEED_LOAD", "org-directory/seed.py", "P1 load of classed seed; physical audit NOT walked; P0 unsigned"),
    )
    cur.execute(
        "INSERT INTO registry_event (event_time, event_type, actor, detail) VALUES (?,?,?,?)",
        (now, "RBAC_APPROVED", "org-directory", "RBAC contract APPROVED and applied 2026-09-09; engine is live"),
    )
    conn.commit()

    # Reconcile
    cur.execute("SELECT COUNT(*), SUM(licensed_capacity) FROM nursing_unit")
    n_units, lic = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM nursing_unit WHERE capacity_class='ED_STRETCHER'")
    n_ed = cur.fetchone()[0]
    cur.execute("SELECT SUM(resource_capacity) FROM nursing_unit WHERE capacity_class='ED_STRETCHER'")
    ed_cap = cur.fetchone()[0]
    cur.execute("SELECT SUM(source_bed_count) FROM nursing_unit")
    src = cur.fetchone()[0]
    assert n_units == 43, n_units
    assert lic == 281, lic
    assert src == 524, src
    assert ed_cap == 118, ed_cap

    n_users = cur.execute("SELECT COUNT(*) FROM app_user").fetchone()[0]
    write_desk_audit(units, lic, ed_cap, src)
    conn.close()
    print(f"Loaded {n_units} units, licensed inpatient {lic}, ED {ed_cap}, source {src}, users {n_users} → {DB}")
    print(f"Demo login password for every account: {DEMO_PASSWORD}")


def write_desk_audit(units, lic, ed_cap, src):
    sheets = ART / "physical_bed_audit_unit_sheets.csv"
    with sheets.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "unit_code", "unit_name", "department", "capacity_class", "is_bedded",
            "source_bed_count", "registry_licensed_capacity", "registry_resource_capacity",
            "dq_flag", "walk_status", "physical_exists", "separate_footprint",
            "physical_beds_counted", "licensed_from_register", "operational_today",
            "desk_recommendation", "notes",
        ])
        for r in units:
            rec, notes = desk_recommendation(r)
            cap = nint(r["bed_capacity"]) or 0
            lic_u = cap if r["capacity_class"] == "INPATIENT_LICENSED" else 0
            w.writerow([
                r["unit_code"], r["unit_name"], r["department"], r["capacity_class"], r["is_bedded"],
                r["source_bed_count"], lic_u, cap, r.get("dq_flag") or "",
                "NOT_WALKED", "UNKNOWN", "UNKNOWN", "", "", "", rec, notes,
            ])

    pending = [r for r in units if (r.get("dq_flag") or "").endswith("PENDING") or r.get("dq_flag") in ("DQ1A_PENDING", "DQ1B_PENDING", "DQ2_PENDING")]
    md = ART / "physical_bed_audit_desk_run.md"
    md.write_text(
        f"""# Physical bed audit — desk run (not a floor walk)

**When:** {EFFECTIVE} · **Who:** Org Directory loader (IT)  
**What this is:** Pre-fill of `physical_bed_audit_form.md` from the classed registry.  
**What this is not:** A physical count. Every unit is `walk_status = NOT_WALKED`. Floor-plan / license-register fields are blank on purpose.

Take `physical_bed_audit_unit_sheets.csv` onto the floor (one row = one sheet). Sign `08_signoff_don_licensing.md` before treating counts as authoritative.

## Desk reconciliation (registry only)

| Check | Result |
|---|---|
| Units loaded | **43** |
| `source_bed_count` sum | **{src}** (matches raw CSV) |
| INPATIENT_LICENSED | **{lic}** (includes `ICU-EXT-2` 14, DQ-1a pending) |
| If DQ-1a merged | 267 |
| ED_STRETCHER | **{ed_cap}** (UCC under Emergency) |
| Physical beds counted | **0 — not walked** |
| MOH/CBAHI license total | **blank (DQ-18)** |

## Blocking until the walk + sign-off

1. `ICU-EXT-2` / `PLASTER-2` / `ED-NAV-2` — real second site vs duplicate (`07`).
2. License register total vs 267 or 281.
3. Confirm Jail (secure inpatient) and UCC (ED family) on the floor.
4. Do **not** provision P2 `bed` rows from 515/524.

## Desk recommendations (not applied as merges)

| Unit | Recommendation |
|---|---|
| ICU-EXT-2 | PROPOSE_MERGE (keep in seed until signed) |
| PLASTER-2 | PROPOSE_MERGE |
| ED-NAV / ED-NAV-2 | KEEP_NON_BEDDED |
| All others | Count per `capacity_class` on the walk |

Instrument: `physical_bed_audit_form.md`. Sheets: `physical_bed_audit_unit_sheets.csv`.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
