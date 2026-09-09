-- Rollback migration 006: Remove Authorization v2 shadow schema
-- Apply:   sqlite3 org_directory.db < 006_authorization_v2_rollback.sql

PRAGMA foreign_keys = ON;

-- Drop triggers
DROP TRIGGER IF EXISTS authorization_lifecycle_no_delete_v2;
DROP TRIGGER IF EXISTS authorization_lifecycle_no_update_v2;
DROP TRIGGER IF EXISTS authorization_decision_sod_no_delete_v2;
DROP TRIGGER IF EXISTS authorization_decision_sod_no_update_v2;
DROP TRIGGER IF EXISTS authorization_decision_no_delete_v2;
DROP TRIGGER IF EXISTS authorization_decision_no_update_v2;
DROP TRIGGER IF EXISTS delegation_permission_active_delete_v2;
DROP TRIGGER IF EXISTS delegation_permission_subset_update_v2;
DROP TRIGGER IF EXISTS delegation_permission_subset_insert_v2;
DROP TRIGGER IF EXISTS delegation_decision_immutable_v2;
DROP TRIGGER IF EXISTS delegation_core_immutable_v2;
DROP TRIGGER IF EXISTS delegation_source_bounds_insert_v2;
DROP TRIGGER IF EXISTS sod_rule_draft_delete_v2;
DROP TRIGGER IF EXISTS sod_rule_draft_update_v2;
DROP TRIGGER IF EXISTS sod_rule_draft_insert_v2;
DROP TRIGGER IF EXISTS access_grant_request_match_insert_v2;
DROP TRIGGER IF EXISTS access_grant_core_immutable_v2;
DROP TRIGGER IF EXISTS access_grant_request_decision_immutable_v2;
DROP TRIGGER IF EXISTS access_grant_request_decided_core_immutable_v2;
DROP TRIGGER IF EXISTS authorization_scope_active_update_v2;
DROP TRIGGER IF EXISTS authorization_scope_active_insert_v2;
DROP TRIGGER IF EXISTS authorization_role_permission_draft_delete_v2;
DROP TRIGGER IF EXISTS authorization_role_permission_draft_update_v2;
DROP TRIGGER IF EXISTS authorization_role_permission_draft_insert_v2;
DROP TRIGGER IF EXISTS authorization_permission_draft_delete_v2;
DROP TRIGGER IF EXISTS authorization_permission_draft_update_v2;
DROP TRIGGER IF EXISTS authorization_permission_draft_insert_v2;
DROP TRIGGER IF EXISTS authorization_role_draft_delete_v2;
DROP TRIGGER IF EXISTS authorization_role_draft_update_v2;
DROP TRIGGER IF EXISTS authorization_role_draft_insert_v2;
DROP TRIGGER IF EXISTS authorization_policy_retired_immutable_v2;
DROP TRIGGER IF EXISTS authorization_policy_active_transition_v2;
DROP TRIGGER IF EXISTS authorization_policy_published_core_immutable_v2;

-- Drop indexes
DROP INDEX IF EXISTS idx_authorization_lifecycle_time_v2;
DROP INDEX IF EXISTS idx_authorization_decision_lookup_v2;
DROP INDEX IF EXISTS idx_sod_policy_status_v2;
DROP INDEX IF EXISTS idx_delegation_source_v2;
DROP INDEX IF EXISTS idx_delegation_delegate_time_v2;
DROP INDEX IF EXISTS idx_access_grant_scope_v2;
DROP INDEX IF EXISTS idx_access_grant_user_time_v2;
DROP INDEX IF EXISTS uq_authorization_scope_unit_v2;
DROP INDEX IF EXISTS uq_authorization_scope_department_v2;
DROP INDEX IF EXISTS uq_authorization_scope_facility_v2;

-- Drop tables (reverse dependency order)
DROP TABLE IF EXISTS authorization_lifecycle_event_v2;
DROP TABLE IF EXISTS authorization_decision_sod_v2;
DROP TABLE IF EXISTS authorization_decision_v2;
DROP TABLE IF EXISTS delegation_permission_v2;
DROP TABLE IF EXISTS delegation_v2;
DROP TABLE IF EXISTS sod_rule_v2;
DROP TABLE IF EXISTS access_grant_v2;
DROP TABLE IF EXISTS access_grant_request_v2;
DROP TABLE IF EXISTS authorization_scope_v2;
DROP TABLE IF EXISTS authorization_role_permission_v2;
DROP TABLE IF EXISTS authorization_permission_v2;
DROP TABLE IF EXISTS authorization_role_v2;
DROP TABLE IF EXISTS authorization_policy_v2;

DELETE FROM schema_version WHERE version = 6;
