import assert from "node:assert/strict";
import test from "node:test";
import { loadAllowlist, redactUrl, revalidateSubresources } from "../src/subresource-revalidation.mjs";

const allowlist = await loadAllowlist();

test("synthetic metadata-only revalidation records approved resource, redirect, blocked, and CSP events", () => {
  const result = revalidateSubresources([
    { type: "resource", resourceClass: "script", url: "https://s3.tradingview.com/widget.js?session=private", status: 200 },
    { type: "redirect", resourceClass: "document", fromUrl: "https://s.tradingview.com/embed?token=one", toUrl: "https://s.tradingview.com/frame?token=two", status: 302 },
    { type: "blocked", resourceClass: "websocket", url: "wss://s.tradingview.com/socket?ticket=secret", reason: "network-policy" },
    { type: "csp-violation", resourceClass: "script", blockedUrl: "https://s3.tradingview.com/extra.js?auth=secret", effectiveDirective: "script-src", disposition: "enforce" },
  ], allowlist);

  assert.deepEqual(result.rejections, []);
  assert.equal(result.approved, true);
  assert.deepEqual(result.records, [
    { type: "resource", resourceClass: "script", url: "https://s3.tradingview.com/widget.js?session=%5BREDACTED%5D", status: 200 },
    { type: "redirect", resourceClass: "document", fromUrl: "https://s.tradingview.com/embed?token=%5BREDACTED%5D", toUrl: "https://s.tradingview.com/frame?token=%5BREDACTED%5D", status: 302 },
    { type: "blocked", resourceClass: "websocket", url: "wss://s.tradingview.com/socket?ticket=%5BREDACTED%5D", reason: "network-policy" },
    { type: "csp-violation", resourceClass: "script", blockedUrl: "https://s3.tradingview.com/extra.js?auth=%5BREDACTED%5D", effectiveDirective: "script-src", disposition: "enforce" },
  ]);
  assert.doesNotMatch(JSON.stringify(result), /private|secret|token=one|token=two/);
});

test("synthetic revalidation rejects unknown origins and resource classes without retaining them", () => {
  const result = revalidateSubresources([
    { type: "resource", resourceClass: "script", url: "https://attacker.invalid/script.js", status: 200 },
    { type: "resource", resourceClass: "wasm", url: "https://s3.tradingview.com/module.wasm", status: 200 },
  ], allowlist);

  assert.equal(result.approved, false);
  assert.deepEqual(result.records, []);
  assert.deepEqual(result.rejections.map(({ code }) => code), ["unapproved-subresource", "unknown-resource-class"]);
});

test("query values, fragments, and credentials never enter revalidation metadata", () => {
  assert.equal(
    redactUrl("https://s3.tradingview.com/a.js?z=last&token=super-secret&z=duplicate#fragment"),
    "https://s3.tradingview.com/a.js?token=%5BREDACTED%5D&z=%5BREDACTED%5D",
  );
  const result = revalidateSubresources([
    { type: "resource", resourceClass: "script", url: "https://user:password@s3.tradingview.com/a.js", status: 200 },
    { type: "resource", resourceClass: "script", url: "https://s3.tradingview.com/a.js", status: 200, body: "must-not-be-stored" },
  ], allowlist);
  assert.equal(result.approved, false);
  assert.deepEqual(result.records, []);
  assert.deepEqual(result.rejections.map(({ code }) => code), ["unsafe-url", "payload-forbidden"]);
  assert.doesNotMatch(JSON.stringify(result), /password|must-not-be-stored/);
});
