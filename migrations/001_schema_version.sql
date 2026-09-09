-- Migration 001: Schema version tracking
-- Apply:   sqlite3 org_directory.db < 001_schema_version.sql
-- Rollback: DROP TABLE IF EXISTS schema_version;

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

INSERT OR IGNORE INTO schema_version (version, description) VALUES
    (1, 'Schema version tracking table');
