#!/usr/bin/env python3
"""Schema migration runner for HNWMS.

Usage:
    python migrate.py                    # Apply all pending migrations
    python migrate.py --rollback 4       # Rollback migration 4
    python migrate.py --status           # Show applied migrations
    python migrate.py --backup           # Create a timestamped backup before migrating
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "org-directory" / "data" / "org_directory.db"

MIGRATIONS = sorted(HERE.glob("[0-9][0-9][0-9]_*.sql"))
ROLLBACKS = {
    int(p.name[:3]): p
    for p in HERE.glob("[0-9][0-9][0-9]_*_rollback.sql")
}


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_version_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()


def applied_versions(conn) -> set[int]:
    ensure_version_table(conn)
    return {r["version"] for r in conn.execute("SELECT version FROM schema_version")}


def backup_db():
    if not DB.exists():
        print("Database not found, nothing to backup.")
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = DB.parent / f"org_directory_backup_{ts}.db"
    shutil.copy2(DB, dest)
    print(f"Backup created: {dest}")
    return dest


def apply_all(conn):
    done = applied_versions(conn)
    pending = [
        m for m in MIGRATIONS
        if not m.name.endswith("_rollback.sql") and int(m.name[:3]) not in done
    ]
    if not pending:
        print("All migrations already applied.")
        return
    for mig in pending:
        ver = int(mig.name[:3])
        print(f"Applying migration {ver}: {mig.name} ... ", end="")
        sql = mig.read_text()
        conn.executescript(sql)
        print("OK")
    print(f"Applied {len(pending)} migration(s).")


def rollback(conn, version: int):
    done = applied_versions(conn)
    if version not in done:
        print(f"Migration {version} is not applied.")
        return
    rb = ROLLBACKS.get(version)
    if not rb or not rb.exists():
        print(f"No rollback script found for migration {version}.")
        return
    print(f"Rolling back migration {version}: {rb.name} ... ", end="")
    sql = rb.read_text()
    conn.executescript(sql)
    print("OK")


def status(conn):
    done = applied_versions(conn)
    rows = conn.execute("SELECT * FROM schema_version ORDER BY version").fetchall()
    if not rows:
        print("No migrations applied.")
        return
    print(f"{'Ver':>4}  {'Applied':26}  Description")
    print("-" * 70)
    for r in rows:
        print(f"{r['version']:>4}  {r['applied_at']:26}  {r['description']}")


def main():
    parser = argparse.ArgumentParser(description="HNWMS Schema Migration Runner")
    parser.add_argument("--rollback", type=int, metavar="VERSION", help="Rollback a specific migration version")
    parser.add_argument("--status", action="store_true", help="Show applied migrations")
    parser.add_argument("--backup", action="store_true", help="Create a database backup before migrating")
    args = parser.parse_args()

    if not DB.exists():
        print(f"Database not found at {DB}. Run seed.py first.")
        sys.exit(1)

    if args.backup:
        backup_db()

    conn = get_conn()
    try:
        if args.status:
            status(conn)
        elif args.rollback is not None:
            rollback(conn, args.rollback)
        else:
            if args.backup is False:
                # Auto-backup on apply
                pass
            apply_all(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
