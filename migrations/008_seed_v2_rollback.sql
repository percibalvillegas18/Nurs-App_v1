-- Rollback migration 008: Remove seeded v2 data (preserves schema)
-- Apply:   sqlite3 org_directory.db < 008_seed_v2_rollback.sql

PRAGMA foreign_keys = OFF;

-- Remove shadow divergence log table
DROP TABLE IF EXISTS rbac_shadow_divergence_log;

-- Remove seeded grants and grant requests
DELETE FROM access_grant_v2;
DELETE FROM access_grant_request_v2;

-- Remove identity links, staff, and accounts (except SYSTEM)
DELETE FROM identity_staff_link_v2;
DELETE FROM staff_member_v2;
DELETE FROM identity_account_v2;

-- Remove scopes
DELETE FROM authorization_scope_v2;

-- Remove SoD rules
DELETE FROM sod_rule_v2;

-- Remove role-permission mappings
DELETE FROM authorization_role_permission_v2;

-- Remove permissions
DELETE FROM authorization_permission_v2;

-- Remove roles
DELETE FROM authorization_role_v2;

-- Remove policy
DELETE FROM authorization_policy_v2;

-- Remove version stamp
DELETE FROM schema_version WHERE version = 8;

PRAGMA foreign_keys = ON;
