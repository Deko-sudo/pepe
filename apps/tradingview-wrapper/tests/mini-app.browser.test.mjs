import assert from "node:assert/strict";
import test from "node:test";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { chromium } from "playwright";

const parentOrigin = "http://127.0.0.1:4180";
const apiOrigin = "http://127.0.0.1:4181";
const wrapperOrigin = "http://127.0.0.1:4182";
const attackerOrigin = "http://127.0.0.1:4183";
const lifecycle = { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "wrapper-document-ready" };
const requests = [];
let apiServer;
let wrapperServer;
let attackerServer;
let vite;
let browser;

const assets = [
  { id: "00000000-0000-4000-8000-000000000001", slug: "btc-usdt", symbol: "BTC/USDT", display_name: "Bitcoin", asset_class: "crypto", market_type: "spot", base_asset: "BTC", quote_asset: "USDT", price_precision: 2, quantity_precision: 8, timezone: "UTC", calendar_kind: "continuous", trading_calendar: "24x7", metadata_version: 1, is_enabled: true },
  { id: "00000000-0000-4000-8000-000000000002", slug: "eth-usdt", symbol: "ETH/USDT", display_name: "Ethereum", asset_class: "crypto", market_type: "spot", base_asset: "ETH", quote_asset: "USDT", price_precision: 2, quantity_precision: 8, timezone: "UTC", calendar_kind: "continuous", trading_calendar: "24x7", metadata_version: 1, is_enabled: true },
];

function json(response, value, status = 200) {
  response.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  response.end(JSON.stringify(value));
}

function configuration(slug, timeframe) {
  return { version: 1, mode: "embedded", provider: "tradingview_isolated_wrapper", asset: slug, timeframe, wrapper_origin: wrapperOrigin, wrapper_path: `/chart/${slug}/${timeframe}`, wrapper_url: `${wrapperOrigin}/chart/${slug}/${timeframe}` };
}

function startApiServer() {
  return createServer((request, response) => {
    const url = new URL(request.url, apiOrigin);
    requests.push(url.pathname);
    if (url.pathname === "/api/v1/users/me") return json(response, { id: "00000000-0000-4000-8000-000000000010", telegram_id: 1, first_name: "Fixture", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" });
    if (url.pathname === "/api/v1/assets") return json(response, { items: assets, next_cursor: null });
    if (url.pathname === "/api/v1/market-data/capabilities") return json(response, { contract_version: "v1", mode: "embedded", status: "available", numeric_quotes_available: false, server_candles_available: false, embedded_chart_available: true, embedded_chart_provider: "tradingview_isolated_wrapper", embedded_chart_config_version: 1, analytics_available: false, quote_cards_visible: false, unavailable_reason_code: null });
    if (url.pathname === "/api/v1/market-data/embedded-chart-config") return json(response, configuration(url.searchParams.get("slug"), url.searchParams.get("timeframe")));
    return json(response, { detail: "not found" }, 404);
  }).listen(4181, "127.0.0.1");
}

function startLifecycleServer(port, origin) {
  return createServer((request, response) => {
    const payload = JSON.stringify(lifecycle).replaceAll("<", "\\u003c");
    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
    response.end(`<!doctype html><title>W4 fixture</title><script>const payload=${payload};window.emitLifecycle=(event=payload.event)=>parent.postMessage({...payload,event},${JSON.stringify(parentOrigin)});window.emitLifecycle();</script>`);
  }).listen(port, "127.0.0.1");
}

async function waitForVite() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try { const response = await fetch(parentOrigin); if (response.ok) return; } catch { /* server not ready */ }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Mini App Vite test server did not start");
}

test.before(async () => {
  apiServer = startApiServer();
  wrapperServer = startLifecycleServer(4182, wrapperOrigin);
  attackerServer = startLifecycleServer(4183, attackerOrigin);
  await Promise.all([once(apiServer, "listening"), once(wrapperServer, "listening"), once(attackerServer, "listening")]);
  vite = spawn("npm", ["--prefix", "../mini-app", "run", "dev", "--", "--config", "vite.w4-browser.config.ts"], { stdio: "ignore" });
  await waitForVite();
  browser = await chromium.launch({ headless: true });
});

test.after(async () => {
  await browser?.close();
  vite?.kill("SIGTERM");
  apiServer?.close(); wrapperServer?.close(); attackerServer?.close();
});

test("Mini App /markets uses a separate local wrapper and rejects attacker and stale-frame lifecycle messages", async () => {
  requests.length = 0;
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(`${parentOrigin}/markets`);
  const frame = page.locator("iframe");
  await frame.waitFor();
  assert.equal(await frame.getAttribute("src"), `${wrapperOrigin}/chart/btc-usdt/1h`);
  assert.equal(await frame.getAttribute("sandbox"), "allow-scripts allow-same-origin");
  assert.equal(await frame.getAttribute("referrerpolicy"), "no-referrer");
  assert.match(await frame.getAttribute("title"), /btc-usdt.*1h/i);
  assert.equal(await frame.getAttribute("allow"), null);
  assert.equal(await frame.getAttribute("srcdoc"), null);
  assert.ok(requests.includes("/api/v1/market-data/capabilities"));
  assert.ok(requests.includes("/api/v1/market-data/embedded-chart-config"));
  assert.ok(!requests.includes("/api/v1/assets/quotes"));
  assert.ok(!requests.some((path) => path.includes("/candles")));
  assert.match(await page.locator("body").innerText(), /готовность источника неизвестна|документ графика загружен/i);

  await page.evaluate(() => { window.__w4OldFrame = document.querySelector("iframe")?.contentWindow; });
  await page.evaluate((url) => { const attacker = document.createElement("iframe"); attacker.src = url; document.body.append(attacker); }, `${attackerOrigin}/attacker`);
  await page.waitForTimeout(100);
  assert.doesNotMatch(await page.locator("body").innerText(), /временно недоступен/i);

  await page.getByRole("combobox", { name: "Выбор инструмента" }).selectOption("eth-usdt");
  await page.waitForFunction((src) => document.querySelector("iframe")?.getAttribute("src") === src, `${wrapperOrigin}/chart/eth-usdt/1h`);
  await page.evaluate(({ origin, data }) => window.dispatchEvent(new MessageEvent("message", {
    origin,
    source: window.__w4OldFrame,
    data,
  })), { origin: wrapperOrigin, data: { ...lifecycle, event: "provider-frame-timeout" } });
  await page.waitForTimeout(50);
  assert.doesNotMatch(await page.locator("body").innerText(), /временно недоступен/i);
  assert.equal(await page.locator('iframe[title^="Встроенный график"]').count(), 1);
  await page.close();
});
