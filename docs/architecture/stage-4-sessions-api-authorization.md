# Stage 4 — Sessions and API Authorization

## Status

```text
Status: PROPOSED — PENDING USER APPROVAL
Implementation: NOT STARTED
Feature branch: NOT CREATED
Pull Request: NOT CREATED
```

This document records recommendations and questions for Stage 4. It is not an approved API, security, data, or frontend contract. No proposal below authorizes implementation.

## Context

Stage 3 added persistence for Telegram users after server-side Telegram Mini App `initData` validation. Its current temporary profile endpoint is:

```http
POST /api/v1/users/me
Content-Type: application/json

{"init_data":"..."}
```

It revalidates `init_data` in the request body and returns the persisted profile. Sessions and JWT are absent. Raw `initData` is not stored. Stage 4 is intended to separate a Telegram login exchange from subsequent authenticated requests, but the mechanism and migration behavior remain pending approval.

## Goals

Subject to approval, Stage 4 should:

- create a server authorization session after verified Telegram `initData`;
- stop sending raw `initData` on each protected API request;
- add authenticated `GET /api/v1/users/me`;
- add logout and revocation behavior;
- keep any raw session token only on the client transport;
- store only a token digest in the database;
- provide a safe Mini App bootstrap flow.

## Explicit non-goals

The following are not part of Stage 4 unless separately approved:

- JWT or refresh-token architecture;
- roles, permissions, or an admin panel;
- payments;
- market providers, assets, quotes, candles, analytics, or any Stage 5 functionality.

## Recommended architecture — pending approval

**Recommended, not approved:** an opaque server-side session.

- Generate a cryptographically random opaque session token with at least 256 bits of entropy.
- Send that token in an `HttpOnly` cookie; do not return it in JSON or store it in browser storage.
- Store only a SHA-256 token digest and session metadata in PostgreSQL.
- Enable `Secure` in production.
- Use `SameSite=Lax` as a proposed starting point, pending an explicit cookie/CSRF decision.
- Reject expired and revoked sessions.
- Make logout set `revoked_at` and clear the client transport credential.

These details are recommendations. Cookie strategy, expiration, concurrency, metadata, and endpoint migration have not been approved.

## Alternatives

| Option | Security properties | Revocation complexity | Frontend storage risk | Telegram WebView compatibility | Implementation complexity | Operational complexity |
| --- | --- | --- | --- | --- | --- | --- |
| **Opaque server-side session in cookie** (recommended) | Raw credential can be `HttpOnly`; database retains only digest; server can enforce expiry/revocation | Low: revoke a database row | Low if `HttpOnly`; CSRF protections are still required | Good for same-origin Mini App/API deployment | Moderate | Moderate: session persistence and cleanup |
| **Access JWT + refresh token** | Stateless access JWT is exposed until expiry; refresh-token protection/design required | Higher: requires denylist/rotation or short expiries | Medium to high if any token is JavaScript-accessible; cookie use reintroduces CSRF concerns | Compatible, but more moving parts | High | High: signing keys, rotation, refresh lifecycle, denylist |
| **Opaque bearer token** | Can be hashed server-side and revoked, but client must present token explicitly | Low to moderate: revoke digest | High: Mini App must retain and read a bearer credential | Compatible but less safe for browser-like clients | Low to moderate | Moderate: token lifecycle and exposure monitoring |

## Proposed endpoints — pending approval

### Telegram session exchange

```http
POST /api/v1/auth/telegram/session
Content-Type: application/json

{"init_data":"..."}
```

**Proposed behavior:**

1. Verify Telegram HMAC.
2. Verify `auth_date` freshness.
3. Upsert the verified user.
4. Create a session.
5. Set a cookie or return a token only according to the mechanism approved by the user.
6. Do not persist raw `initData`.

### Authenticated profile

```http
GET /api/v1/users/me
```

**Proposed behavior:** authenticate using the approved session mechanism and return the persisted public user profile.

### Logout

```http
POST /api/v1/auth/logout
```

**Proposed behavior:** invalidate the current session according to the approved logout policy.

### Optional logout-all

```http
POST /api/v1/auth/logout-all
```

This endpoint is optional and requires a separate user decision about concurrent sessions and logout-all behavior.

## Proposed session schema — pending approval

A proposed `user_sessions` table contains:

- `id`: UUID;
- `user_id`: foreign key to `users.id`;
- `token_digest`: one-way digest only;
- `created_at`;
- `expires_at`;
- `last_seen_at`;
- `revoked_at`;
- optional `user_agent`;
- optional IP metadata only when a confirmed operational/security need exists.

It must not contain raw Telegram `initData` or raw session tokens. Exact indexes, retention, cleanup, metadata, and whether `last_seen_at` is written on each request remain pending approval.

## Security model — requirements to approve

The implementation proposal must be reviewed against these requirements before work begins:

- Generate tokens with a cryptographically secure random generator and at least 256 bits of entropy.
- Use constant-time digest comparison where direct digest comparison is applicable; database lookups must not disclose token state through response differences.
- For cookies, enable `Secure` in production and `HttpOnly` always; select `SameSite` only after approval.
- Choose and document CSRF protection for cookie-authenticated state changes.
- Define CORS and Origin/Referer verification behavior for the deployed Mini App origin.
- Prevent session fixation by issuing a new credential after successful login exchange; define any subsequent rotation policy.
- Define expiry, idle timeout, sliding expiration, and rotation policy.
- Define current-session logout, optional logout-all, and revocation semantics.
- Rate-limit login exchange without breaking Telegram WebView usage.
- Prohibit logging of cookie values, raw session tokens, token digests, and raw `initData`.

## Migration plan — pending approval

Current Stage 3 state:

```http
POST /api/v1/users/me
{"init_data":"..."}
```

Proposed Stage 4 target:

```http
POST /api/v1/auth/telegram/session
GET  /api/v1/users/me
POST /api/v1/auth/logout
```

`POST /api/v1/users/me` must not be removed without a migration period or an explicit user decision. The future of `POST /api/v1/auth/telegram/validate`, which currently validates initData and upserts a user, also requires an explicit decision: compatibility endpoint, pure validation endpoint, deprecation, or replacement by the exchange endpoint.

## Test plan

Before Stage 4 can be accepted, implementation tests should cover:

- valid login creates a session;
- repeated-login behavior;
- invalid or expired `initData` creates neither user nor session;
- missing Telegram token is handled safely;
- valid credential authenticates `GET /api/v1/users/me`;
- missing credential returns 401;
- unknown credential returns 401;
- expired session returns 401;
- revoked session returns 401;
- logout invalidates the current session;
- logout is idempotent according to the approved contract;
- raw tokens are absent from the database;
- raw tokens and raw `initData` are absent from logs;
- CSRF behavior;
- CORS behavior;
- concurrent-session behavior;
- migration upgrade and downgrade;
- PostgreSQL runtime integration tests.

## Required decisions — all pending user approval

| # | Decision | Options / questions | Recommendation |
| --- | --- | --- | --- |
| 1 | Session mechanism | Opaque server-side cookie session; JWT access + refresh; opaque bearer token | Opaque server-side session + `HttpOnly` cookie |
| 2 | Cookie policy | `HttpOnly`; `Secure` in production; `SameSite=Lax`, `Strict`, or `None`; path; domain; local-development behavior | `HttpOnly`, production `Secure`, host-only path `/`; exact SameSite pending |
| 3 | Session lifetime | Absolute lifetime; idle timeout; sliding expiration; rotation frequency | No value is proposed as approved; define explicitly |
| 4 | Concurrent sessions | One active session; one per device; multiple active sessions; fixed limit | Choose explicitly based on product/device needs |
| 5 | Logout | Current session only; separate logout-all; idempotency | Current-session logout plus optional logout-all endpoint |
| 6 | CSRF | SameSite + Origin/Referer verification; synchronizer token; double-submit token; another documented mechanism | Choose after deployment-origin/cookie policy is decided |
| 7 | Stage 3 endpoint migration | Keep temporary endpoint; deprecation period; remove in Stage 4; compatibility adapter | Keep `POST /api/v1/users/me` for one migration period and mark deprecated |
| 8 | Validation endpoint side effect | Keep compatibility behavior; make pure validation; deprecate after exchange; replace by exchange | Explicit product/API decision required |
| 9 | Session metadata | `user_agent`; IP; device name; `last_seen_at` | Do not add fingerprinting metadata without confirmed need |

## Implementation gate

```text
Stage 4 implementation MUST NOT begin until every required contract decision is explicitly approved by the user.
```

Until then, the following must not be created or changed: a Stage 4 feature branch, migration `003`, a session model/table, authentication middleware/dependency, frontend authentication flow, or a Stage 4 implementation PR.
