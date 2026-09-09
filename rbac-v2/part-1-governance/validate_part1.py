#!/usr/bin/env python3
"""Validate Part 1 governance artifacts against the current seed catalogue."""

from __future__ import annotations

import ast
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = ROOT / "org-directory" / "seed.py"


def literal_assignment(name: str):
    tree = ast.parse(SEED.read_text(encoding="utf-8"), filename=str(SEED))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Missing literal assignment: {name}")


def csv_rows(filename: str) -> list[dict[str, str]]:
    with (HERE / filename).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, f"{filename} must contain rows"
    assert all(None not in row for row in rows), f"Malformed CSV row in {filename}"
    return rows


def main() -> None:
    seeded_roles = {row[0] for row in literal_assignment("ROLES")}
    seeded_permissions = {row[0] for row in literal_assignment("PERMS")}

    role_rows = csv_rows("02_role_boundary_matrix.csv")
    matrix_roles = [row["role_code"] for row in role_rows]
    assert len(matrix_roles) == len(set(matrix_roles)), "Duplicate role in boundary matrix"
    assert set(matrix_roles) == seeded_roles, (
        f"Role mismatch: missing={sorted(seeded_roles - set(matrix_roles))}, "
        f"extra={sorted(set(matrix_roles) - seeded_roles)}"
    )

    represented_permissions = {
        permission.strip()
        for row in role_rows
        for permission in row["current_prototype_permissions"].split(";")
        if permission.strip()
    }
    assert seeded_permissions <= represented_permissions, (
        f"Unrepresented current permissions: {sorted(seeded_permissions - represented_permissions)}"
    )

    sod_rows = csv_rows("03_sod_catalog.csv")
    sod_codes = [row["rule_code"] for row in sod_rows]
    assert len(sod_codes) == len(set(sod_codes)), "Duplicate SoD rule code"
    assert any(
        row["conflict_a"] == "BED_CONTROL"
        and row["conflict_b"] in {"SCHED_WRITE", "SCHED_PUBLISH"}
        for row in sod_rows
    ), "Missing bed-control/scheduling conflict"

    decision_text = (HERE / "04_decision_register.md").read_text(encoding="utf-8")
    for line in decision_text.splitlines():
        if "| BLOCKING |" in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            assert len(cells) >= 6 and cells[4], f"Blocking decision lacks approver: {line}"
            assert cells[5] == "**PENDING**", f"Blocking decision is not pending: {line}"
    assert "[PENDING]" in decision_text

    tracked = {
        "01_governance_charter.md",
        "02_role_boundary_matrix.csv",
        "03_sod_catalog.csv",
        "04_decision_register.md",
        "05_traceability_and_acceptance.md",
        "validate_part1.py",
    }
    assert tracked <= {path.name for path in HERE.iterdir()}, "Part 1 artifact missing"

    print(f"Part 1 validation PASS: {len(seeded_roles)} roles")
    print(f"Part 1 validation PASS: {len(seeded_permissions)} current permissions represented")
    print(f"Part 1 validation PASS: {len(sod_rows)} SoD rules")
    print("Part 1 validation PASS: blocking decisions remain pending with accountable approvers")


if __name__ == "__main__":
    main()
