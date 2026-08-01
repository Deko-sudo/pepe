# W5 isolated-wrapper security controls

> Status: W5 is implemented by the current pull request and awaits owner merge approval. W1–W4 are merged; W6 and W7 are not started. Provider activation, production origins, hosting, DNS, TLS, Telegram device validation, and Stage 9 remain out of scope.

## Authoritative immutable bundle

`config/embedded-chart-security.development.json` is a secretless local/development source manifest. The repository compiler, `apps/api/scripts/compile_embedded_chart_security_bundle.py`, validates it and atomically publishes one directory containing `api-settings.json`, `mini-app-security.conf`, `wrapper-security.conf`, `bundle-metadata.json`, and `bundle.sha256`.

The security digest is calculated from deterministic security-effective inputs; no wall-clock value affects it. Every generated Nginx response adds the non-sensitive `X-Pepe-Embedded-Chart-Bundle` digest. Consumers must mount the same published bundle read-only at `/run/pepe/embedded-chart-security`; a missing or malformed artifact fails closed.

The API reads only the generated `api-settings.json` for embedded-chart availability. Existing W3 environment inputs remain source compatibility inputs, not runtime provider activation decisions.

## Boundaries and headers

`apps/mini-app/nginx.conf` is the authoritative parent-header delivery point and includes `mini-app-security.conf`. When authorized in development/test, its CSP permits exactly the generated wrapper origin in `frame-src`; when blocked it is `frame-src 'none'`. The parent CSP never contains a TradingView source.

`apps/tradingview-wrapper/nginx.conf` is the authoritative wrapper-header delivery point and includes `wrapper-security.conf`. The generated policy has exact `frame-ancestors` for the generated parent origin, no wildcard source, and the W2-evidenced exact provider sources only inside the wrapper. It sends `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, restrictive `Permissions-Policy`, CORP, `Cache-Control: no-store`, and no contradictory X-Frame-Options.

The Mini App iframe remains exactly `sandbox="allow-scripts allow-same-origin"`, has `referrerpolicy="no-referrer"`, and has no `allow` attribute. No provider script, frame, API, websocket, image, worker, or asset is loaded by the parent document.

## Kill switch and coordinated rollback

The canonical manifest field is `embedded_chart_kill_switch`, strictly JSON boolean only. Missing, malformed, mixed-case string, whitespace string, unsupported environment, invalid origin, same origin, and production all fail closed. Production never activates, irrespective of inputs.

Emergency disable is a deployment-unit operation: set the source kill switch to `true`, compile and atomically publish a new bundle, then restart/reload the API, Mini App Nginx, and wrapper Nginx together. Confirm the same new digest on all three consumers. The API reports unavailable and returns no wrapper URL; parent CSP becomes `frame-src 'none'`; the Mini App removes the iframe after its fresh capability response; chart routes return static `503` before any provider script/frame can execute.

Code rollback reverts the W5 artifact/merge while deploying a blocked bundle. It has no database migration, deletion, or destructive operation. Re-enable only after root-cause review, explicit owner approval, a new authorized development/test bundle, coordinated restart/reload, and fresh capability/config/iframe identity checks.

## Provider revalidation

The W2 mutable-script verifier remains opt-in; ordinary CI does not contact TradingView. It records digest metadata only and never stores a third-party body. Changed digests require manual security review and owner approval. Provider-subresource revalidation remains manual, records only origins/resource classes/redirects/violations, stores no bodies, parses no provider content, and rejects a newly observed origin until manually approved.

Written TradingView confirmation for the intended embedding, Telegram Mini App, separate wrapper, public/commercial display, framing/script behavior, branding, and domain requirements remains mandatory before any production activation.

## Deterministic runtime coverage and cleanup

The root Docker CI smoke starts the API, Mini App, and wrapper with the development bundle, then requests only local Mini App and wrapper routes. It verifies the generated parent CSP has the exact wrapper `frame-src` and no provider source, verifies the wrapper's exact parent `frame-ancestors`, requests one local chart document, and requires matching non-sensitive bundle digests on both Nginx responses. It does not request the provider frame or any TradingView URL.

The compiler tests cover the complementary blocked bundle: a strict JSON kill switch, invalid input, unsupported environments, and production compile to `frame-src 'none'`, `frame-ancestors 'none'`, and local chart-route `503` handling. Test bundle directories are temporary and must not be retained in the repository; local Compose cleanup uses the non-destructive `docker compose down --remove-orphans` command and never removes volumes.
