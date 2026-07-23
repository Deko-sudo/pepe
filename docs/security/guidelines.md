# Security Considerations

## Authentication

- Telegram initData HMAC-SHA-256 validation (implemented)
- `auth_date` freshness check with configurable max age
- `initDataUnsafe` is NOT trusted as identity source
- No session management yet (planned Stage 4)

## API Security

- CORS configuration
- Rate limiting
- Input validation with Pydantic
- SQL injection prevention with SQLAlchemy ORM
- Constant-time hash comparison via `hmac.compare_digest`
- Duplicate query key rejection
- Input length limit (16 KiB)

## Secrets Management

- Environment variables for sensitive data
- No hardcoded tokens or passwords
- Bot token never sent to frontend
- Bot token never logged
- Raw `initData` never stored in localStorage/sessionStorage

## Data Protection

- No logging of sensitive data (hash, secret key, full initData)
- Encrypted connections for PostgreSQL and Redis
- Secure headers via Caddy

## Network Security

- Internal network for service communication
- Caddy as reverse proxy
- Cloudflare for DDoS protection (production)

## Telegram Validation

- HMAC-SHA-256 verification against Telegram's bot token
- `auth_date` freshness check (default: 1 hour max age, 30s future skew)
- Server-side only validation — frontend cannot bypass
- Graceful degradation when bot token is not configured (503)
- Structured logging with only event/result metadata
