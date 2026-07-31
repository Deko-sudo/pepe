import { SCRIPT_URL } from "./config.mjs";

export function pageDocument(config) {
  const data = JSON.stringify({
    slug: config.slug,
    timeframe: config.timeframe,
    symbol: config.symbol,
    interval: config.interval,
    semantics: config.semantics,
    source: config.source,
    scriptUrl: SCRIPT_URL,
  }).replace(/</g, "\\u003c");
  const title = `${config.slug.toUpperCase()} ${config.timeframe} technical validation chart`;
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>${title}</title>
  <link rel="stylesheet" href="/assets/wrapper.css">
</head>
<body>
  <main class="wrapper" data-wrapper-root>
    <p class="banner" role="status">Technical validation build. Public production display is not approved.</p>
    <header>
      <h1>${config.slug.toUpperCase()} · ${config.timeframe}</h1>
      <p>${config.semantics}</p>
      <p>${config.source}</p>
    </header>
    <section class="chart-shell" aria-label="Provider chart technical validation">
      <p data-loading-state>Preparing provider chart without user data…</p>
      <p data-error-state hidden role="alert">Provider chart is unavailable for this technical validation route.</p>
      <div class="tradingview-widget-container" data-chart-container></div>
    </section>
    <p class="limitation">A provider frame document load does not prove chart readiness. Provider readiness remains unknown.</p>
  </main>
  <script id="wrapper-config" type="application/json">${data}</script>
  <script defer src="/assets/bootstrap.js"></script>
</body>
</html>`;
}

export function invalidDocument() {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>Invalid technical validation chart route</title><link rel="stylesheet" href="/assets/wrapper.css"></head><body><main class="wrapper"><p class="banner">Technical validation build. Public production display is not approved.</p><h1>Invalid chart route</h1><p role="alert">This local wrapper accepts only documented canonical chart routes.</p></main></body></html>`;
}
