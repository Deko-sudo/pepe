# Provider revalidation

The mutable-script verifier remains opt-in and excluded from ordinary CI. It requires HTTPS, uses bounded redirects, rejects unsafe redirect targets, records only final URL, status-derived result metadata, byte length, and SHA-256, stores no script body, and exits nonzero on a changed digest. A changed digest is never auto-approved.

Subresource revalidation is manual and must use a controlled browser session. Record only origins, resource classes, redirects, observable websocket origins, and CSP violations. Never retain response bodies, parse market content, inspect provider DOM, extract data, or capture market screenshots. Compare to the reviewed allowlist and fail on a new origin/class pending owner approval. Synthetic fixtures, not live TradingView, cover CI behavior.
