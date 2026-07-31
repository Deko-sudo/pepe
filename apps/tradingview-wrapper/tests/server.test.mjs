import assert from "node:assert/strict";
import test from "node:test";
import { once } from "node:events";
import { resolve } from "node:path";
import { createStaticServer, WRAPPER_CSP } from "../src/server.mjs";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");
let server;

test.before(async () => {
  server = createStaticServer({ root: dist, port: 4193 });
  await once(server, "listening");
});
test.after(() => server.close());

test("static server applies security headers to canonical and invalid documents", async () => {
  for (const path of ["/chart/btc-usdt/1m", "/chart/not-valid/1m"]) {
    const response = await fetch(`http://127.0.0.1:4193${path}`);
    assert.equal(response.headers.get("content-security-policy"), WRAPPER_CSP);
    assert.equal(response.headers.get("referrer-policy"), "no-referrer");
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("x-robots-tag"), "noindex, nofollow, noarchive");
  }
});
