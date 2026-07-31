import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { WRAPPER_CSP } from "../src/server.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("wrapper CSP is exact, explicit, and excludes unsafe provider sources", () => {
  for (const directive of ["default-src 'none'", "script-src 'self' https://s3.tradingview.com", "style-src 'self' 'unsafe-inline'", "frame-src https://s.tradingview.com", "frame-ancestors http://127.0.0.1:4174"]) {
    assert.ok(WRAPPER_CSP.includes(directive), directive);
  }
  assert.ok(!WRAPPER_CSP.replace("frame-ancestors http://127.0.0.1:4174", "").includes("http:"));
  for (const forbidden of ["*", "unsafe-eval"]) assert.ok(!WRAPPER_CSP.includes(forbidden), forbidden);
});

test("provider metadata records observed—not pinned—script change evidence", async () => {
  const metadata = JSON.parse(await readFile(path.join(root, "provider/tradingview-script.json"), "utf8"));
  assert.equal(metadata.officialUrl, "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js");
  assert.match(metadata.observedSha256, /^[a-f0-9]{64}$/);
  assert.equal(metadata.status, "observed-not-pinned");
});

test("origin inventory remains metadata-only and rejects HTTP and wildcard approval", async () => {
  const inventory = JSON.parse(await readFile(path.join(root, "provider/observed-origins.json"), "utf8"));
  assert.equal(inventory.httpRequestsObserved, false);
  assert.equal(inventory.mixedContentObserved, false);
  assert.equal(inventory.wildcardHostsNecessary, false);
  assert.deepEqual(inventory.nestedFrameOrigins, ["https://s.tradingview.com"]);
});

test("Nginx serves extensionless canonical documents as HTML without dropping inherited headers", async () => {
  const nginx = await readFile(path.join(root, "nginx.conf"), "utf8");
  assert.match(nginx, /location ~ \^\/chart[\s\S]*?default_type text\/html;[\s\S]*?try_files \$uri =404;/);
  assert.match(nginx, /add_header Content-Security-Policy[\s\S]*?add_header Cache-Control "no-store" always;/);
  assert.doesNotMatch(nginx, /location ~ \^\/chart[\s\S]*?add_header Cache-Control/);
});
