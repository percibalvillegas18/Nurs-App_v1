-- Migration 009: Enforce one active v2 policy at a time.
-- A request must name an immutable policy version; multiple ACTIVE versions
-- make cutover/readiness and rollback ambiguous.

CREATE UNIQUE INDEX IF NOT EXISTS uq_authorization_policy_one_active_v2
ON authorization_policy_v2(status) WHERE status='ACTIVE';

INSERT INTO schema_version (version, description) VALUES
    (9, 'One active authorization v2 policy invariant');
