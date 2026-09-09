-- Migration 002: Add indexes on frequently queried columns
-- Apply:   sqlite3 org_directory.db < 002_indexes.sql
-- Rollback: see 002_indexes_rollback.sql

CREATE INDEX IF NOT EXISTS idx_role_grant_persona ON role_grant(persona_id);
CREATE INDEX IF NOT EXISTS idx_role_grant_status ON role_grant(status);
CREATE INDEX IF NOT EXISTS idx_role_grant_effective ON role_grant(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_app_session_expires ON app_session(expires_at);
CREATE INDEX IF NOT EXISTS idx_app_session_user ON app_session(user_id);
CREATE INDEX IF NOT EXISTS idx_staff_document_persona ON staff_document(persona_id);
CREATE INDEX IF NOT EXISTS idx_registry_event_time ON registry_event(event_time);
CREATE INDEX IF NOT EXISTS idx_rbac_decision_log_subject ON rbac_decision_log(subject);
CREATE INDEX IF NOT EXISTS idx_rbac_decision_log_time ON rbac_decision_log(decided_at);

INSERT INTO schema_version (version, description) VALUES
    (2, 'Indexes on foreign keys and filter columns');
