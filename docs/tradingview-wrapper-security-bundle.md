# Embedded-chart security bundle

The owner-approved W5 control plane is a generated immutable bundle, not a remote administration service. The secretless source manifest has schema version `1` and contains: `version`, `environment`, `market_data_mode`, `embedded_chart_enabled`, `embedded_chart_provider`, `embedded_chart_kill_switch`, `parent_origin`, and `wrapper_origin`.

The compiler rejects malformed values without repair. Only strict JSON booleans are accepted for the kill switch. Development/test can authorize only `embedded` + `tradingview_isolated_wrapper` with distinct exact HTTP(S) origins. Production and every invalid/missing value compile to a blocked bundle.

Compile with (the Compose deployment binds `APP_ENV` explicitly, so a production runtime compiles the production-blocked state rather than activating this development source manifest):

`python apps/api/scripts/compile_embedded_chart_security_bundle.py --manifest config/embedded-chart-security.development.json --output <bundle-dir>`

Publication writes a temporary sibling directory and atomically replaces the active directory only after all artifacts are complete. Security-effective contents deterministically produce `bundle.sha256`; metadata has no timestamp or secrets. The directory contains `api-settings.json`, Mini App and wrapper Nginx includes, metadata, and digest.

All three consumers mount the same bundle read-only and expose the identical non-sensitive digest. A missing include prevents Nginx startup; the API treats a missing, malformed, or mismatched bundle as unavailable. No browser, cookie, Telegram value, query parameter, storage value, or HTTP endpoint controls activation.
