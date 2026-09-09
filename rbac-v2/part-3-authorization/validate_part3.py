#!/usr/bin/env python3
"""Validate Part 3 completeness, additive safety, and executable behavior."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    expected = {
        "01_authorization_architecture.md",
        "02_permission_and_scope_model.md",
        "03_grant_and_sod_governance.md",
        "04_delegation_model.md",
        "05_migration_and_shadow_rollout.md",
        "06_acceptance_and_gate.md",
        "authorization_schema.sql",
        "engine_v2.py",
        "test_authorization_v2.py",
        "validate_part3.py",
    }
    present = {path.name for path in HERE.iterdir() if path.is_file()}
    assert expected <= present, f"Missing Part 3 artifacts: {sorted(expected - present)}"

    schema = (HERE / "authorization_schema.sql").read_text(encoding="utf-8")
    upper = schema.upper()
    assert "ALTER TABLE" not in upper and "DROP TABLE" not in upper
    created = re.findall(r"CREATE TABLE IF NOT EXISTS\s+([A-Za-z0-9_]+)", schema, flags=re.I)
    assert len(created) == 13, created
    assert all(name.endswith("_v2") for name in created), created
    protected = {
        "role", "permission", "role_permission", "persona", "role_grant",
        "sod_rule", "rbac_decision_log", "app_user", "app_session",
    }
    assert not protected.intersection(created)

    engine = (HERE / "engine_v2.py").read_text(encoding="utf-8")
    for required in (
        "POLICY_NOT_ACTIVE", "ACCOUNT_NOT_ACTIVE", "PERMISSION_UNKNOWN",
        "RESOURCE_NOT_ACTIVE", "NO_EFFECTIVE_ENTITLEMENT", "SOD_CONFLICT",
        "validate_grant_activation", "_delegated_entitlements",
    ):
        assert required in engine
    assert "waive_roles" not in engine

    gate = (HERE / "06_acceptance_and_gate.md").read_text(encoding="utf-8")
    assert "Runtime RBAC v2 cutover | **NOT AUTHORIZED**" in gate
    assert gate.count("[PENDING]") >= 4
    decisions = (ROOT / "rbac-v2" / "part-1-governance" / "04_decision_register.md").read_text(encoding="utf-8")
    for decision in ("GOV-RBAC-01", "GOV-RBAC-02", "GOV-RBAC-03", "GOV-SCOPE-01", "GOV-DEL-01", "GOV-DEL-02"):
        assert decision in decisions
    assert "**PENDING**" in decisions

    subprocess.run([sys.executable, str(HERE / "test_authorization_v2.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "rbac-v2" / "part-1-governance" / "validate_part1.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "rbac-v2" / "part-2-identity" / "validate_part2.py")], check=True)

    print(f"Part 3 artifact completeness: PASS ({len(expected)} files)")
    print(f"Part 3 additive-table safety: PASS ({len(created)} shadow tables)")
    print("Part 3 engine contract and no standing waiver: PASS")
    print("Part 3 governance and cutover gate: PASS")
    print("Part 1 and Part 2 regression validation: PASS")


if __name__ == "__main__":
    main()
