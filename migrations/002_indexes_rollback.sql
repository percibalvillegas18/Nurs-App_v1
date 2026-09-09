-- Rollback for Migration 002
DROP INDEX IF EXISTS idx_role_grant_persona;
DROP INDEX IF EXISTS idx_role_grant_status;
DROP INDEX IF EXISTS idx_role_grant_effective;
DROP INDEX IF EXISTS idx_app_session_expires;
DROP INDEX IF EXISTS idx_app_session_user;
DROP INDEX IF EXISTS idx_staff_document_persona;
DROP INDEX IF EXISTS idx_registry_event_time;
DROP INDEX IF EXISTS idx_rbac_decision_log_subject;
DROP INDEX IF EXISTS idx_rbac_decision_log_time;

DELETE FROM schema_version WHERE version = 2;
