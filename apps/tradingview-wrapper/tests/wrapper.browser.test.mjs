import assert from "node:assert/strict";
import test from "node:test";

import { once } from "node:events";
import { resolve } from "node:path";
import { createStaticServer } from "../src/server.mjs";

import { chromium } from "playwright";
const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");
let wrapperServer;
let harnessServer;
let browser;

test.before(async () => {
  wrapperServer = createStaticServer({ root: dist, port: 4173 });
  harnessServer = createStaticServer({ root: dist, port: 4174, harness: true });
  await Promise.all([once(wrapperServer, "listening"), once(harnessServer, "listening")]);
  browser = await chromium.launch({ headless: true });
});
test.after(async () => {
  await browser?.close();
  wrapperServer?.close();
  harnessServer?.close();
});

test("all 18 routes emit only local document-ready before blocked provider request", async () => {
  for (const slug of ["btc-usdt", "eth-usdt", "xau-usd"]) for (const timeframe of ["1m", "5m", "15m", "1h", "4h", "1d"]) {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.route("https://s3.tradingview.com/**", (route) => route.abort());
    await page.goto(`http://127.0.0.1:4174/?test_private_marker=must_not_reach_wrapper`);
    await page.evaluate(() => {
      window.rawLifecycleEvents = [];
      window.rawLifecycleListener = (message) => {
        const frame = document.querySelector("iframe");
        if (message.origin === "http://127.0.0.1:4173" && message.source === frame?.contentWindow && message.data?.type === "pepe.tradingview-wrapper.lifecycle") window.rawLifecycleEvents.push(message.data.event);
      };
      window.addEventListener("message", window.rawLifecycleListener);
    });
    await page.evaluate((path) => window.wrapperHarness.mount(path), `/chart/${slug}/${timeframe}`);
    await page.waitForFunction(() => window.wrapperHarness.received.includes("wrapper-document-ready"));
    const events = await page.evaluate(() => window.wrapperHarness.received);
    assert.ok(events.includes("wrapper-document-ready"));
    assert.ok(!events.includes("provider-ready"));
    assert.ok(!(await page.evaluate(() => window.rawLifecycleEvents)).includes("provider-ready"));
    await page.evaluate(() => window.removeEventListener("message", window.rawLifecycleListener));
    await page.close();
  }
});

test("query, fragment, and invalid routes do not request TradingView", async () => {
  for (const routePath of ["/chart/btc-usdt/1m?symbol=OANDA:XAUUSD", "/chart/btc-usdt/1m#interval=D", "/chart/not-valid/1m"]) {
    const page = await browser.newPage();
    let providerRequests = 0;
    await page.route("https://s3.tradingview.com/**", (route) => { providerRequests += 1; return route.abort(); });
    await page.goto(`http://127.0.0.1:4174/?test_private_marker=must_not_reach_wrapper`);
    await page.evaluate((path) => window.wrapperHarness.mount(path), routePath);
    await page.waitForFunction(() => window.wrapperHarness.received.includes("wrapper-configuration-invalid"));
    assert.equal(providerRequests, 0, routePath);
    await page.close();
  }
});

test("harness rejects wrong origin, source, schema, event, payload, and opaque origin", async () => {
  const page = await browser.newPage();
  await page.goto("http://127.0.0.1:4174/");
  const accepted = await page.evaluate(() => {
    const accepts = window.wrapperHarness.acceptsLifecycle;
    const source = document.querySelector("iframe").contentWindow;
    const base = { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "wrapper-document-ready" };
    return [
      accepts({ origin: "http://wrong.test", source, data: base }),
      accepts({ origin: "null", source, data: base }),
      accepts({ origin: "http://127.0.0.1:4173", source: window, data: base }),
      accepts({ origin: "http://127.0.0.1:4173", source, data: { ...base, event: "provider-ready" } }),
      accepts({ origin: "http://127.0.0.1:4173", source, data: { ...base, extra: "no" } }),
    ];
  });
  assert.deepEqual(accepted, [false, false, false, false, false]);
  await page.close();
});

test("actual wrapper request receives no harness private marker and default sandbox stays narrow", async () => {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  let wrapperRequestUrl = "";
  page.on("request", (request) => { if (request.url().startsWith("http://127.0.0.1:4173/chart/")) wrapperRequestUrl = request.url(); });
  await page.route("https://s3.tradingview.com/**", (route) => route.abort());
  await page.goto("http://127.0.0.1:4174/?test_private_marker=must_not_reach_wrapper");
  await page.evaluate(() => window.wrapperHarness.mount("/chart/btc-usdt/1m"));
  await page.waitForFunction(() => window.wrapperHarness.received.includes("wrapper-document-ready"));
  assert.ok(!wrapperRequestUrl.includes("must_not_reach_wrapper"));
  assert.equal(await page.locator("iframe").getAttribute("sandbox"), "allow-scripts allow-same-origin");
  assert.equal(await page.locator("iframe").getAttribute("referrerpolicy"), "no-referrer");
  await page.close();
});
