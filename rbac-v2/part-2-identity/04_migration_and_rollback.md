# Part 2 — Migration, Shadow Operation, and Rollback

## 1. Migration rule

Part 2 is additive. The schema creates only `_v2` identity tables and append-only evidence tables. It does not alter or drop `persona`, `app_user`, `app_session`, `staff_profile`, `staff_document`, role/grant tables, or runtime endpoints.

## 2. Pre-migration inventory

Run `migration_inventory.sql` against a controlled copy of the current database and record:

- persona and app-user counts;
- user/persona linkage gaps;
- shared or duplicate credential indicators;
- demo-slot count;
- profile license completeness and expiry quality;
- active/expired session count;
- staff documents by type/status;
- identities with privileged grants;
- duplicate normalized candidate identifiers when real source data is available.

The repository demo seed intentionally lacks authoritative employee numbers, verified work emails, and SSO subjects. The migration must not fabricate these fields.

## 3. Shadow mapping sequence

1. Back up and restore-test the source database.
2. Apply `identity_schema.sql` to a non-production copy.
3. Load authoritative HR staff IDs and employment assignments into staging.
4. Load authoritative identity-provider subjects and verified emails into staging.
5. Match by approved immutable keys; place ambiguous/unmatched records in `identity_reconciliation_issue_v2`.
6. Create v2 identity/staff links only for deterministic or independently approved matches.
7. Import credential evidence from its authoritative source; profile text alone remains unverified.
8. Compare account, employment, unit, position, license, and status results.
9. Obtain HR/Security reconciliation sign-off.
10. Run in shadow mode before changing authentication or authorization consumers.

## 4. Cutover prerequisites

- all privileged users have verified immutable identity mapping;
- all required production accounts have verified provider binding and MFA status;
- zero unresolved critical duplicates or orphan privileged accounts;
- session issuance and revocation tests pass;
- joiner/mover/leaver events reconcile with HR;
- credential status behavior is accepted by HR Credentialing and DON;
- rollback and emergency administrator recovery are demonstrated;
- Part 1 blocking decisions are signed.

## 5. Cutover outline

1. Freeze identity/grant administration for the agreed window.
2. Reconcile source deltas since the final shadow load.
3. Activate v2 authentication behind a controlled feature flag for a pilot group.
4. Revoke legacy sessions for migrated pilot identities.
5. Observe authentication, lifecycle, and access metrics.
6. Expand only after the pilot acceptance gate.
7. Disable legacy production login after full reconciliation; retain read-only historical linkage.

## 6. Rollback

Rollback disables the v2 feature flag and restores the last approved authentication path for accounts explicitly included in the rollback plan. It does not delete v2 evidence or reuse identities. Sessions created under the failed mode are revoked. Any identity, email, or provider-binding changes made during the window are reconciled before retry.

Rollback is not permitted to re-enable shared demo credentials in production. If the legacy path is not production-safe, the safe response is controlled outage/recovery access—not silent reintroduction of insecure login.

## 7. Production data migration deliverables

The following cannot be completed from the repository alone and require accountable source owners:

- signed HR employee export and field dictionary;
- identity-provider tenant, issuer, client, and immutable-subject mapping;
- verified work-email status;
- credentialing source and evidence-verification procedure;
- privacy/retention classification;
- production environment classification and secret-management method;
- named pilot users and business continuity contacts.

