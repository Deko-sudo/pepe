# Stage 4 — Sessions and API Authorization

## Status

```text
Contract: APPROVED
Implementation: IN REVIEW
Feature branch: feat/stage-4-sessions-api-authorization
Base: d99820d2df9e5e4a31ddf7d962fb1b860430e6f8
Pull Request: https://github.com/Deko-sudo/pepe/pull/5
```

Stage 4 introduces server-side authorization only. It does not implement Stage 5 or later roadmap work.

## Session mechanism

- Opaque server-side sessions only; no JWT, access token, refresh token, bearer storage, `localStorage`, or `sessionStorage`.
- A 256-bit (`secrets.token_urlsafe(32)`) raw token exists only while setting or reading the cookie.
- PostgreSQL stores only a SHA-256 hexadecimal digest (`VARCHAR(64)`); no raw token, raw Telegram `initData`, IP, User-Agent, device name, or fingerprint is persisted or logged.

## Cookie policy

- Name is configurable (`pepe_session` by default).
- `HttpOnly`, `SameSite=Lax`, `Path=/`, host-only (no `Domain` attribute).
- `Secure=true` is required in production; local HTTP development uses `Secure=false`.
- `Max-Age=2592000`; `Expires` equals the session absolute expiry.
- Logout uses matching Path, Secure, HttpOnly, and SameSite attributes while deleting the cookie.

## Lifetime and revocation

- Absolute lifetime: 2,592,000 seconds (30 days), never extended.
- Idle timeout: 604,800 seconds (7 days), sliding on each authenticated request and clamped to absolute expiry.
- Authenticated refresh locks the session row and updates `last_seen_at` and `idle_expires_at` monotonically. A delayed request with an earlier captured time cannot regress either value; absolute expiry never changes.
- Repeated verified Telegram login revokes any presented active cookie session, then creates a new token/session with new absolute and idle lifetimes.
- Invalid, unknown, expired, malformed, and revoked credentials receive the same generic 401 response.

## Concurrent sessions and logout-all linearization

`user_sessions` permits at most five active sessions per user. Creation and logout-all both lock the corresponding `users` row with `SELECT ... FOR UPDATE`, making them linearizable relative to one another. When creation obtains the lock first, a following logout-all revokes the newly created active session. When logout-all obtains the lock first, a subsequent login is a later operation and may create a new session. Logout-all does not promise to prohibit future verified logins.

When creating the sixth active session, the deterministic oldest active session (`created_at ASC, id ASC`) is revoked. Expired and already revoked rows do not count.

## Schema and migration

Alembic revision `003_create_user_sessions.py` extends `001 -> 002 -> 003` with:

- `id UUID PRIMARY KEY`;
- `user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE` and a user lookup index;
- unique `token_digest VARCHAR(64)` lookup constraint;
- `created_at`, `expires_at`, `idle_expires_at`, `last_seen_at`, and nullable `revoked_at` timezone-aware timestamps.

Downgrade removes only `user_sessions` and its user index.

Docker Compose has a one-shot `migrate` service that uses the API image and the same settings mapping as API. It waits for PostgreSQL health, runs `alembic upgrade head`, and exits. API waits for `migrate` with `service_completed_successfully`, so it does not start after a migration failure. `make up` and `docker compose up -d` use this dependency graph.

## API

| Endpoint | Behavior |
| --- | --- |
| `POST /api/v1/auth/telegram/session` | Exact CSRF Origin/Referer check, Telegram HMAC/freshness validation, user upsert, presented-session rotation, session creation, HttpOnly cookie, and `UserProfile` response without a token. |
| `GET /api/v1/users/me` | Cookie-only authenticated profile; refreshes monotonic `last_seen_at` and idle expiry. |
| `POST /api/v1/auth/logout` | CSRF-protected, idempotent current-session revocation and cookie clearing; `204`. |
| `POST /api/v1/auth/logout-all` | CSRF-protected, requires an active session, serializes with session creation through the user-row lock, revokes active sessions for its user only, clears cookie; `204`. |
| `POST /api/v1/auth/telegram/validate` | Preserved Stage-3 validation and user-upsert compatibility behavior. |
| `POST /api/v1/users/me` | Preserved legacy body-based profile behavior and marked deprecated in OpenAPI. |

## CSRF

New session mutation endpoints require an exact allowlisted Origin. If Origin is absent, an exact origin extracted from Referer is allowed; `null`, missing, malformed, suffix, wrong-scheme, and wrong-port values are rejected. A disallowed Origin never falls back to Referer. Production refuses to start without Secure cookies and non-empty valid HTTP/HTTPS origins. Development allowlist is exactly `http://localhost:3000`, `http://localhost:4000`, and `http://localhost:8080`.

## Frontend bootstrap and logout

The Mini App first calls `GET /api/v1/users/me` with `credentials: "include"`. Only a 401 and available Telegram `initData` cause `POST /api/v1/auth/telegram/session`, also with `credentials: "include"`. An instance-local single-flight promise prevents React development StrictMode from performing duplicate concurrent bootstrap checks or exchanges; a true provider remount receives a new guard.

`TelegramAuthContext` exposes `logout()` and `logoutAll()` actions. After a successful `204`, each clears `user`, sets state to `idle`, and clears the UI error. On failure, the confirmed user/state remain intact and the error is exposed to UI. Raw `initData` and session tokens are never persisted or read by JavaScript; HttpOnly cookie removal remains server-side.

## Validation

The feature branch contains API security/schema/endpoint tests, Mini App client/bootstrap tests, rendered Compose deployment-contract validation, and real PostgreSQL concurrency tests gated by `PEPE_RUN_POSTGRES_INTEGRATION=1`. CI runs the PostgreSQL tests after `alembic upgrade head` and runs a disposable fresh-Compose smoke: migration completion, API health, Alembic head, `user_sessions` existence, session exchange, authenticated profile, logout-all, revoked-cookie 401, and logs without test credentials or cookie/digest material. Runtime validation uses PostgreSQL, never SQLite.

## Retention

Revoked and expired session rows are retained as Stage-4 audit records. Automatic cleanup and an exact retention duration are not approved. Retention policy and cleanup belong to Stage 12 production hardening; their absence does not affect the five-active-session limit because that limit counts only active rows.

## Explicit exclusions

No JWT, refresh tokens, bearer token persistence, roles, permissions, IP/device/fingerprint metadata, cleanup worker, scheduled deletion, hardcoded retention duration, market providers, assets, quotes, candles, analytics, or other Stage-5 functionality are included.
