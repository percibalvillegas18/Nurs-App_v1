# Part 2 — Authentication and Session Security Requirements

## 1. Production authentication profile

Hospital SSO is the recommended production identity provider. The application should accept an authenticated provider assertion only after validating issuer, audience, signature, lifetime, replay controls, and the immutable provider subject. Authorization remains an HNWMS decision and must not be inferred only from identity-provider group names.

Privileged and high-risk operations require MFA or step-up authentication according to approved policy. A static emergency PIN, shared password, or email-only possession check is not acceptable step-up authentication.

## 2. Local authentication exception

Local authentication may remain for development and an explicitly approved recovery account. It must not be the undocumented production default.

Where local authentication is approved:

- use an approved password hashing scheme and centrally governed parameters;
- store a versioned encoded credential, never reversible plaintext;
- require password screening, secure recovery, rate limiting, and lockout controls;
- rotate the session identifier after authentication and privilege elevation;
- revoke sessions after password reset, provider rebind, account disable, or critical security event;
- protect recovery accounts with MFA, restricted network/source policy, alerts, and regular testing;
- never return a demo password or public list of valid production identities.

The existing `Demo@2026` flow remains a development fixture only. Part 5 must prevent it from starting in production configuration.

## 3. Authentication assurance

| Assurance | Meaning | Example allowed use |
|---|---|---|
| `AAL1` | Single-factor authenticated session | Low-risk self-service if policy permits |
| `AAL2` | MFA-authenticated session | Privileged administration and high-risk clinical operations |
| `STEP_UP` | Recent reauthentication/MFA for a specific operation | Break-glass, credential verification, high-risk grant approval |

Exact assurance terminology must match the selected identity provider. HNWMS records the achieved assurance and authentication time; it does not claim an assurance level the provider did not assert.

## 4. Session contract

- Store only `token_hash`; compare hashes in constant time at the application boundary.
- Bind session to `user_id`, `auth_version`, assurance, issued time, last-seen time, and expiry.
- Reject a session when the account is not `ACTIVE`, the session is revoked/expired, or its `auth_version` differs from the current account version.
- Use secure, `HttpOnly`, `Secure`, appropriate `SameSite` cookies in production.
- Never accept tokens in URL query strings.
- Set idle and absolute timeouts by risk class; exact values require Security approval.
- Log creation, failure, step-up, revocation, logout, recovery, and provider-binding changes without storing secrets.

## 5. Required authentication events

`LOGIN_SUCCESS`, `LOGIN_FAILURE`, `MFA_SUCCESS`, `MFA_FAILURE`, `STEP_UP_SUCCESS`, `STEP_UP_FAILURE`, `LOGOUT`, `SESSION_REVOKED`, `ACCOUNT_LOCKED`, `ACCOUNT_UNLOCKED`, `PASSWORD_CHANGED`, `RECOVERY_STARTED`, `RECOVERY_COMPLETED`, `EMAIL_VERIFIED`, `PROVIDER_LINKED`, `PROVIDER_UNLINKED`.

Events include stable account ID, time, outcome, reason code, provider, assurance, correlation ID, and privacy-minimized client context. They exclude passwords, assertions, raw tokens, and document contents.

## 6. Service identities

Non-human service identities must be distinguishable from staff accounts, have named owners, restricted purpose and scope, non-interactive authentication, credential rotation, expiry/review, and no ability to use clinical break-glass. Shared human accounts are prohibited.

