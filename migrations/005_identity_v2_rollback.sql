-- Rollback migration 005: Remove Identity v2 shadow schema
-- Apply:   sqlite3 org_directory.db < 005_identity_v2_rollback.sql

PRAGMA foreign_keys = ON;

-- Drop triggers first (reverse order of creation)
DROP TRIGGER IF EXISTS identity_lifecycle_event_no_delete_v2;
DROP TRIGGER IF EXISTS identity_lifecycle_event_no_update_v2;
DROP TRIGGER IF EXISTS authentication_event_no_delete_v2;
DROP TRIGGER IF EXISTS authentication_event_no_update_v2;
DROP TRIGGER IF EXISTS identity_session_account_update_v2;
DROP TRIGGER IF EXISTS identity_session_account_insert_v2;
DROP TRIGGER IF EXISTS credential_independent_verifier_update_v2;
DROP TRIGGER IF EXISTS credential_independent_verifier_insert_v2;
DROP TRIGGER IF EXISTS employment_primary_overlap_update_v2;
DROP TRIGGER IF EXISTS employment_primary_overlap_insert_v2;
DROP TRIGGER IF EXISTS employment_unit_department_update_v2;
DROP TRIGGER IF EXISTS employment_unit_department_insert_v2;
DROP TRIGGER IF EXISTS local_credential_provider_update_v2;
DROP TRIGGER IF EXISTS local_credential_provider_insert_v2;

-- Drop indexes
DROP INDEX IF EXISTS idx_reconciliation_open_v2;
DROP INDEX IF EXISTS idx_lifecycle_staff_time_v2;
DROP INDEX IF EXISTS idx_auth_event_user_time_v2;
DROP INDEX IF EXISTS idx_session_user_expiry_v2;
DROP INDEX IF EXISTS idx_credential_staff_expiry_v2;
DROP INDEX IF EXISTS idx_employment_staff_effective_v2;
DROP INDEX IF EXISTS idx_identity_account_status_v2;

-- Drop tables (reverse dependency order)
DROP TABLE IF EXISTS identity_reconciliation_issue_v2;
DROP TABLE IF EXISTS identity_lifecycle_event_v2;
DROP TABLE IF EXISTS authentication_event_v2;
DROP TABLE IF EXISTS identity_session_v2;
DROP TABLE IF EXISTS professional_credential_v2;
DROP TABLE IF EXISTS employment_assignment_v2;
DROP TABLE IF EXISTS local_auth_credential_v2;
DROP TABLE IF EXISTS identity_staff_link_v2;
DROP TABLE IF EXISTS staff_member_v2;
DROP TABLE IF EXISTS identity_account_v2;

DELETE FROM schema_version WHERE version = 5;
