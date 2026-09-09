-- Read-only Part 2 inventory. Run against a controlled copy of org_directory.db.
SELECT 'persona_count' AS metric, COUNT(*) AS value FROM persona;
SELECT 'app_user_count' AS metric, COUNT(*) AS value FROM app_user;
SELECT 'persona_without_user' AS metric, COUNT(*) AS value
FROM persona p LEFT JOIN app_user u ON u.persona_id = p.persona_id
WHERE u.user_id IS NULL;
SELECT 'user_without_persona' AS metric, COUNT(*) AS value
FROM app_user u LEFT JOIN persona p ON p.persona_id = u.persona_id
WHERE p.persona_id IS NULL;
SELECT 'demo_persona_count' AS metric, COUNT(*) AS value FROM persona WHERE is_demo = 1;
SELECT 'active_user_count' AS metric, COUNT(*) AS value FROM app_user WHERE status = 'ACTIVE';
SELECT 'privileged_active_user_count' AS metric, COUNT(DISTINCT u.user_id) AS value
FROM app_user u
JOIN role_grant g ON g.persona_id = u.persona_id AND g.status = 'ACTIVE'
JOIN role r ON r.role_id = g.role_id
WHERE r.role_code IN ('SYS_ADMIN','ORG_ADMIN','DON','ADON','HOUSE_SUP','BED_COORD','WORKFORCE_MGR');
SELECT 'profile_count' AS metric, COUNT(*) AS value FROM staff_profile;
SELECT 'profile_missing_license_number' AS metric, COUNT(*) AS value
FROM staff_profile WHERE trim(COALESCE(license_no, '')) = '';
SELECT 'profile_missing_license_expiry' AS metric, COUNT(*) AS value
FROM staff_profile WHERE trim(COALESCE(license_expiry, '')) = '';
SELECT 'active_session_count' AS metric, COUNT(*) AS value
FROM app_session WHERE expires_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now');
SELECT 'expired_session_count' AS metric, COUNT(*) AS value
FROM app_session WHERE expires_at < strftime('%Y-%m-%dT%H:%M:%SZ', 'now');
SELECT 'document_count' AS metric, COUNT(*) AS value FROM staff_document;

