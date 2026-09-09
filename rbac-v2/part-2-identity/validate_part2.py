#!/usr/bin/env python3
"""Validate Part 2 completeness, safety boundaries, and executable schema tests."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    expected = {
        "01_identity_architecture.md",
        "02_authentication_security_requirements.md",
        "03_identity_lifecycle_workflows.md",
        "04_migration_and_rollback.md",
        "05_acceptance_and_gate.md",
        "identity_schema.sql",
        "migration_inventory.sql",
        "test_identity_schema.py",
        "validate_part2.py",
    }
    present = {path.name for path in HERE.iterdir() if path.is_file()}
    assert expected <= present, f"Missing Part 2 artifacts: {sorted(expected - present)}"

    schema = (HERE / "identity_schema.sql").read_text(encoding="utf-8")
    upper = schema.upper()
    assert "ALTER TABLE" not in upper and "DROP TABLE" not in upper
    created = re.findall(r"CREATE TABLE IF NOT EXISTS\s+([A-Za-z0-9_]+)", schema, flags=re.I)
    assert created and all(name.endswith("_v2") for name in created), created
    for protected in ("persona", "app_user", "app_session", "staff_profile", "staff_document"):
        assert not re.search(rf"CREATE TABLE IF NOT EXISTS\s+{protected}\b", schema, flags=re.I)

    inventory = (HERE / "migration_inventory.sql").read_text(encoding="utf-8").upper()
    assert all(keyword not in inventory for keyword in ("INSERT ", "UPDATE ", "DELETE ", "ALTER ", "DROP ", "CREATE "))

    gate = (HERE / "05_acceptance_and_gate.md").read_text(encoding="utf-8")
    assert "Runtime authentication cutover | **NOT AUTHORIZED**" in gate
    assert "[PENDING]" in gate
    part1 = (ROOT / "rbac-v2" / "part-1-governance" / "04_decision_register.md").read_text(encoding="utf-8")
    assert "GOV-ID-01" in part1 and "GOV-ID-02" in part1
    assert "GOV-ID-01 | BLOCKING" in part1 and "GOV-ID-02 | BLOCKING" in part1

    subprocess.run([sys.executable, str(HERE / "test_identity_schema.py")], check=True)
    print(f"Part 2 artifact completeness: PASS ({len(expected)} files)")
    print(f"Part 2 additive-table safety: PASS ({len(created)} shadow tables)")
    print("Part 2 migration inventory read-only check: PASS")
    print("Part 2 governance gate check: PASS")


if __name__ == "__main__":
    main()
