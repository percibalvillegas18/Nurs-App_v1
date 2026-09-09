#!/usr/bin/env python3
"""Validate Part 4 completeness, additive safety, and executable controls."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    expected = {
        "01_safety_architecture.md", "02_eligibility_and_freshness.md",
        "03_guardrail_composition.md", "04_exception_separation.md",
        "05_break_glass_controls.md", "06_degraded_mode_and_rollout.md",
        "07_acceptance_and_gate.md", "clinical_safety_schema.sql",
        "safety_engine.py", "test_clinical_safety.py", "validate_part4.py",
    }
    present = {path.name for path in HERE.iterdir() if path.is_file()}
    assert expected <= present, f"Missing Part 4 artifacts: {sorted(expected - present)}"

    schema = (HERE / "clinical_safety_schema.sql").read_text(encoding="utf-8")
    upper = schema.upper()
    assert "ALTER TABLE" not in upper and "DROP TABLE" not in upper
    created = re.findall(r"CREATE TABLE IF NOT EXISTS\s+([A-Za-z0-9_]+)", schema, flags=re.I)
    assert len(created) == 16, created
    assert all(name.endswith("_v2") for name in created), created
    assert "unit_compliance_rules" not in schema.lower()
    assert "compliance_exceptions" not in schema.lower()
    for required in (
        "identity_staff_link_v2", "authorization_decision_v2",
        "authorization_permission_v2", "authorization_scope_v2",
    ):
        assert required in schema

    engine = (HERE / "safety_engine.py").read_text(encoding="utf-8")
    for required in (
        "ELIGIBILITY_BLOCK", "ELIGIBILITY_SOURCE_UNAVAILABLE_OR_STALE",
        "GUARDRAIL_BLOCK", "GUARDRAIL_VERDICT_MISMATCH",
        "AUTHORIZATION_REQUIRED", "validate_break_glass_activation",
        "BREAK_GLASS_ELIGIBILITY_BLOCK", "GUARDRAIL_EXCEPTION_APPROVE",
    ):
        assert required in engine

    gate = (HERE / "07_acceptance_and_gate.md").read_text(encoding="utf-8")
    assert "Runtime Part 4 cutover | **NOT AUTHORIZED**" in gate
    assert gate.count("[PENDING]") >= 6
    decisions = (ROOT / "rbac-v2" / "part-1-governance" / "04_decision_register.md").read_text(encoding="utf-8")
    for decision in ("GOV-CLIN-01", "GOV-CLIN-02", "GOV-COMP-01", "GOV-BG-01", "GOV-BG-02", "GOV-BG-03", "GOV-BCP-01", "GOV-AUD-01"):
        assert decision in decisions

    subprocess.run([sys.executable, str(HERE / "test_clinical_safety.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "rbac-v2" / "part-1-governance" / "validate_part1.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "rbac-v2" / "part-2-identity" / "validate_part2.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "rbac-v2" / "part-3-authorization" / "validate_part3.py")], check=True)

    print(f"Part 4 artifact completeness: PASS ({len(expected)} files)")
    print(f"Part 4 additive-table safety: PASS ({len(created)} shadow tables)")
    print("Part 4 reuse/no-simplified-rule-model check: PASS")
    print("Part 4 governance and cutover gate: PASS")
    print("Parts 1-3 regression validation: PASS")


if __name__ == "__main__":
    main()
