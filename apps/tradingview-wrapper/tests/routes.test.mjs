import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { intervals, lifecycleEvents, parseCanonicalUrl, routeConfig, routes } from "../src/config.mjs";
import { invalidDocument, pageDocument } from "../src/template.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("all 18 canonical combinations resolve to immutable mappings", () => {
  let count = 0;
  for (const slug of Object.keys(routes)) for (const timeframe of Object.keys(intervals)) {
    const config = routeConfig(slug, timeframe);
    assert.ok(config);
    assert.equal(parseCanonicalUrl(`/chart/${slug}/${timeframe}`)?.symbol, config.symbol);
    assert.equal(parseCanonicalUrl(`/chart/${slug}/${timeframe}`)?.interval, config.interval);
    count += 1;
  }
  assert.equal(count, 18);
});

test("invalid, query, fragment, uppercase, encoded, and traversal route values are rejected", () => {
  for (const value of [
    "/chart/btc-usdt/2m", "/chart/btc-usdt", "/chart/btc-usdt/1m/extra", "/chart/BTC-USDT/1m",
    "/chart/btc-usdt/1m?symbol=OANDA:XAUUSD", "/chart/btc-usdt/1m#interval=D",
    "/chart/btc-usdt%2F1m", "/chart/../btc-usdt/1m", "https://evil.example/chart/btc-usdt/1m",
  ]) assert.equal(parseCanonicalUrl(value), null, value);
});

test("generated valid document contains fixed disclosure and no direct provider iframe URL", () => {
  const document = pageDocument(routeConfig("xau-usd", "1d"));
  assert.match(document, /OANDA XAU\/USD broker\/reference-style quote\. Not exchange-traded spot\./);
  assert.match(document, /Technical validation build\. Public production display is not approved\./);
  assert.match(document, /embed-widget-advanced-chart\.js/);
  assert.doesNotMatch(document, /<iframe[^>]+tradingview/i);
  assert.doesNotMatch(document, /provider-ready/);
});

test("invalid document is local, neutral, and has no provider request", () => {
  const document = invalidDocument();
  assert.match(document, /Invalid chart route/);
  assert.doesNotMatch(document, /tradingview\.com/i);
  assert.doesNotMatch(document, /bootstrap\.js/);
});

test("lifecycle schema has only fixed non-market events", () => {
  assert.deepEqual(lifecycleEvents, [
    "wrapper-document-ready", "provider-script-load-failed", "provider-frame-created",
    "provider-frame-document-loaded", "provider-frame-timeout", "wrapper-configuration-invalid",
  ]);
  assert.ok(!lifecycleEvents.includes("provider-ready"));
});

test("bootstrap has no parent command channel, data storage, credentials, or market extraction", async () => {
  const bootstrap = await readFile(path.join(root, "public/assets/bootstrap.js"), "utf8");
  for (const forbidden of ["localStorage", "sessionStorage", "document.cookie", "Authorization", "initData", "addEventListener(\"message\""]) {
    assert.ok(!bootstrap.includes(forbidden), forbidden);
  }
  assert.match(bootstrap, /window\.parent\.postMessage/);
});
