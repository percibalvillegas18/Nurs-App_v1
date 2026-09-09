-- Rollback migration 007: Remove Clinical Safety v2 shadow schema
-- Apply:   sqlite3 org_directory.db < 007_clinical_safety_v2_rollback.sql

PRAGMA foreign_keys = ON;

-- Drop all triggers
DROP TRIGGER IF EXISTS safety_alert_no_delete_v2;
DROP TRIGGER IF EXISTS safety_alert_no_update_v2;
DROP TRIGGER IF EXISTS break_glass_review_no_delete_v2;
DROP TRIGGER IF EXISTS break_glass_review_no_update_v2;
DROP TRIGGER IF EXISTS break_glass_use_no_delete_v2;
DROP TRIGGER IF EXISTS break_glass_use_no_update_v2;
DROP TRIGGER IF EXISTS safety_decision_exception_no_delete_v2;
DROP TRIGGER IF EXISTS safety_decision_exception_no_update_v2;
DROP TRIGGER IF EXISTS safety_decision_no_delete_v2;
DROP TRIGGER IF EXISTS safety_decision_no_update_v2;
DROP TRIGGER IF EXISTS exception_approval_no_delete_v2;
DROP TRIGGER IF EXISTS exception_approval_no_update_v2;
DROP TRIGGER IF EXISTS guardrail_result_no_delete_v2;
DROP TRIGGER IF EXISTS guardrail_result_no_update_v2;
DROP TRIGGER IF EXISTS guardrail_evaluation_no_delete_v2;
DROP TRIGGER IF EXISTS guardrail_evaluation_no_update_v2;
DROP TRIGGER IF EXISTS eligibility_snapshot_no_delete_v2;
DROP TRIGGER IF EXISTS eligibility_snapshot_no_update_v2;
DROP TRIGGER IF EXISTS break_glass_activation_alert_update_v2;
DROP TRIGGER IF EXISTS break_glass_activation_alert_v2;
DROP TRIGGER IF EXISTS break_glass_review_authorized_v2;
DROP TRIGGER IF EXISTS break_glass_review_independent_v2;
DROP TRIGGER IF EXISTS break_glass_active_core_immutable_v2;
DROP TRIGGER IF EXISTS break_glass_permission_published_delete_v2;
DROP TRIGGER IF EXISTS break_glass_permission_published_update_v2;
DROP TRIGGER IF EXISTS break_glass_permission_allowed_insert_v2;
DROP TRIGGER IF EXISTS break_glass_bundle_active_transition_v2;
DROP TRIGGER IF EXISTS break_glass_bundle_approved_core_immutable_v2;
DROP TRIGGER IF EXISTS guardrail_exception_approve_state_v2;
DROP TRIGGER IF EXISTS guardrail_exception_approval_authorized_v2;
DROP TRIGGER IF EXISTS guardrail_exception_self_approval_v2;
DROP TRIGGER IF EXISTS guardrail_exception_core_immutable_v2;
DROP TRIGGER IF EXISTS guardrail_exception_result_match_insert_v2;
DROP TRIGGER IF EXISTS guardrail_result_match_insert_v2;
DROP TRIGGER IF EXISTS guardrail_evaluation_policy_match_v2;
DROP TRIGGER IF EXISTS guardrail_adapter_published_delete_v2;
DROP TRIGGER IF EXISTS guardrail_adapter_published_update_v2;
DROP TRIGGER IF EXISTS guardrail_adapter_draft_insert_v2;
DROP TRIGGER IF EXISTS eligibility_unit_active_insert_v2;
DROP TRIGGER IF EXISTS safety_permission_profile_published_delete_v2;
DROP TRIGGER IF EXISTS safety_permission_profile_published_update_v2;
DROP TRIGGER IF EXISTS safety_permission_policy_match_v2;
DROP TRIGGER IF EXISTS clinical_safety_policy_active_transition_v2;
DROP TRIGGER IF EXISTS clinical_safety_policy_published_core_immutable_v2;

-- Drop indexes
DROP INDEX IF EXISTS idx_safety_alert_type_time_v2;
DROP INDEX IF EXISTS idx_safety_decision_lookup_v2;
DROP INDEX IF EXISTS idx_break_glass_user_time_v2;
DROP INDEX IF EXISTS idx_exception_effective_v2;
DROP INDEX IF EXISTS idx_guardrail_candidate_time_v2;
DROP INDEX IF EXISTS idx_eligibility_staff_unit_time_v2;

-- Drop tables (reverse dependency order)
DROP TABLE IF EXISTS safety_alert_v2;
DROP TABLE IF EXISTS break_glass_review_v2;
DROP TABLE IF EXISTS break_glass_use_v2;
DROP TABLE IF EXISTS clinical_safety_decision_exception_v2;
DROP TABLE IF EXISTS clinical_safety_decision_v2;
DROP TABLE IF EXISTS break_glass_event_v2;
DROP TABLE IF EXISTS break_glass_bundle_permission_v2;
DROP TABLE IF EXISTS break_glass_bundle_v2;
DROP TABLE IF EXISTS guardrail_exception_approval_v2;
DROP TABLE IF EXISTS guardrail_exception_request_v2;
DROP TABLE IF EXISTS guardrail_rule_result_v2;
DROP TABLE IF EXISTS guardrail_evaluation_v2;
DROP TABLE IF EXISTS guardrail_rule_adapter_v2;
DROP TABLE IF EXISTS clinical_eligibility_snapshot_v2;
DROP TABLE IF EXISTS safety_permission_profile_v2;
DROP TABLE IF EXISTS clinical_safety_policy_v2;

DELETE FROM schema_version WHERE version = 7;
