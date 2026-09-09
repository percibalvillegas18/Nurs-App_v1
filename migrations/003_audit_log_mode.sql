-- Migration 003: Add 'mode' column to rbac_decision_log (ENFORCED vs SIMULATED)
-- Apply:   sqlite3 org_directory.db < 003_audit_log_mode.sql
-- Rollback: see 003_audit_log_mode_rollback.sql

ALTER TABLE rbac_decision_log ADD COLUMN mode TEXT NOT NULL DEFAULT 'ENFORCED';

INSERT INTO schema_version (version, description) VALUES
    (3, 'RBAC decision log: ENFORCED vs SIMULATED mode');
