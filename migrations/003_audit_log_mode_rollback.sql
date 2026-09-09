-- Rollback for Migration 003
-- SQLite does not support DROP COLUMN before 3.35.0.
-- For older SQLite: recreate table without the column.
-- For SQLite 3.35.0+:
ALTER TABLE rbac_decision_log DROP COLUMN mode;

DELETE FROM schema_version WHERE version = 3;
