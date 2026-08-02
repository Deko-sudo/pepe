import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { EventEmitter } from "node:events";
import { WRAPPER_CSP } from "../src/server.mjs";
import { fetchExact, runProviderCheck, validateMetadata } from "../src/provider-check.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("wrapper CSP is exact, explicit, and excludes unsafe provider sources", () => {
  const directives = Object.fromEntries(WRAPPER_CSP.split("; ").map((directive) => {
    const [name, ...sources] = directive.split(" ");
    return [name, sources];
  }));
  assert.deepEqual(directives, {
    "default-src": ["'none'"], "base-uri": ["'none'"], "object-src": ["'none'"], "form-action": ["'none'"],
    "frame-ancestors": ["http://127.0.0.1:4174"], "script-src": ["'self'", "https://s3.tradingview.com"],
    "style-src": ["'self'"], "img-src": ["'self'"], "frame-src": ["https://s.tradingview.com"],
    "connect-src": ["'none'"], "font-src": ["'none'"], "media-src": ["'none'"], "worker-src": ["'none'"], "manifest-src": ["'none'"],
  });
  for (const forbidden of ["*", "unsafe-eval", "'unsafe-inline'"]) assert.ok(!WRAPPER_CSP.includes(forbidden), forbidden);
});

test("provider metadata records observed—not pinned—script change evidence", async () => {
  const metadata = JSON.parse(await readFile(path.join(root, "provider/tradingview-script.json"), "utf8"));
  assert.deepEqual(Object.keys(metadata).sort(), ["accessDate", "lastValidationDate", "notes", "observedFinalUrl", "observedSha256", "officialDocumentationTitle", "officialDocumentationUrl", "officialUrl", "retrievalResult", "status"]);
  assert.equal(metadata.officialUrl, "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js");
  assert.equal(metadata.observedFinalUrl, metadata.officialUrl);
  assert.match(metadata.observedSha256, /^[a-f0-9]{64}$/);
  assert.equal(metadata.status, "observed-not-pinned");
  assert.match(metadata.accessDate, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(metadata.lastValidationDate, /^\d{4}-\d{2}-\d{2}$/);
});

test("provider-check keeps mutable-provider validation manual and fails closed", async () => {
  const source = await readFile(path.join(root, "src/provider-check.mjs"), "utf8");
  for (const policy of ["httpsClient.get", "redirects >= 3", "Provider redirect has no Location header", "Rejected non-HTTPS redirect", "Unexpected provider status", "currentUrl !== metadata.observedFinalUrl || hash !== metadata.observedSha256"]) assert.ok(source.includes(policy), policy);
  assert.doesNotMatch(source, /writeFile|rename|unlink/);
});

const providerMetadata = {
  officialUrl: "https://provider.example/script.js",
  officialDocumentationUrl: "https://provider.example/docs",
  officialDocumentationTitle: "Provider script documentation",
  accessDate: "2026-07-31",
  lastValidationDate: "2026-07-31",
  observedFinalUrl: "https://cdn.provider.example/script.js",
  observedSha256: "a".repeat(64),
  retrievalResult: "HTTP 200, synthetic test fixture",
  status: "observed-not-pinned",
  notes: "Synthetic metadata used only to test the manual verifier.",
};

test("provider-check deterministically follows HTTPS redirects and emits metadata only", async () => {
  const calls = [];
  const output = [];
  const errors = [];
  const responses = [
    { statusCode: 302, location: "https://cdn.provider.example/script.js", sha256: "b".repeat(64), byteLength: 0 },
    { statusCode: 200, sha256: providerMetadata.observedSha256, byteLength: 123 },
  ];
  const unchanged = await runProviderCheck({
    metadata: providerMetadata,
    fetchResponse: async (url) => {
      calls.push(url);
      return responses.shift();
    },
    log: (line) => output.push(line),
    error: (line) => errors.push(line),
  });

  assert.equal(unchanged, true);
  assert.deepEqual(calls, [providerMetadata.officialUrl, providerMetadata.observedFinalUrl]);
  assert.deepEqual(errors, []);
  assert.deepEqual(output, [
    `final-url=${providerMetadata.observedFinalUrl}`,
    `sha256=${providerMetadata.observedSha256}`,
    "UNCHANGED: observed script hash matches committed W2 evidence.",
  ]);
  assert.ok(output.every((line) => !line.includes("response-body-that-must-not-be-output")));
});

test("provider-check rejects invalid metadata before any request and fails closed on unsafe responses", async () => {
  const invalidMetadata = { ...providerMetadata, observedSha256: "not-a-digest" };
  let calls = 0;
  await assert.rejects(
    runProviderCheck({ metadata: invalidMetadata, fetchResponse: async () => { calls += 1; } }),
    /Invalid provider metadata: observedSha256/,
  );
  assert.equal(calls, 0);
  assert.throws(() => validateMetadata({ ...providerMetadata, accessDate: "2026-02-29" }), /calendar date/);

  await assert.rejects(
    runProviderCheck({
      metadata: providerMetadata,
      fetchResponse: async () => ({ statusCode: 302, location: "http://provider.example/script.js", sha256: "b".repeat(64), byteLength: 0 }),
    }),
    /Rejected non-HTTPS redirect/,
  );
  await assert.rejects(
    runProviderCheck({
      metadata: providerMetadata,
      fetchResponse: async () => ({ statusCode: 200, sha256: "A".repeat(64), byteLength: 1 }),
    }),
    /Invalid provider response SHA-256 metadata/,
  );

  const output = [];
  const errors = [];
  const unchanged = await runProviderCheck({
    metadata: providerMetadata,
    fetchResponse: async () => ({ statusCode: 200, sha256: "c".repeat(64), byteLength: 1 }),
    log: (line) => output.push(line),
    error: (line) => errors.push(line),
  });
  assert.equal(unchanged, false);
  assert.deepEqual(errors, ["CHANGED: committed observed script metadata must be explicitly reviewed and subresources revalidated."]);
  assert.deepEqual(output, [
    `final-url=${providerMetadata.officialUrl}`,
    `sha256=${"c".repeat(64)}`,
  ]);
});

test("provider-check hashes response data transiently without returning a response body", async () => {
  const payload = "response-body-that-must-not-be-output";
  const response = new EventEmitter();
  response.statusCode = 200;
  response.headers = {};
  const request = new EventEmitter();
  request.setTimeout = () => {};
  request.destroy = (error) => request.emit("error", error);
  const httpsClient = {
    get: (_url, _options, callback) => {
      callback(response);
      queueMicrotask(() => {
        response.emit("data", Buffer.from(payload));
        response.emit("end");
      });
      return request;
    },
  };

  const result = await fetchExact("https://provider.example/script.js", { httpsClient });
  assert.deepEqual(Object.keys(result).sort(), ["byteLength", "location", "sha256", "statusCode"]);
  assert.equal(result.statusCode, 200);
  assert.equal(result.byteLength, Buffer.byteLength(payload));
  assert.equal(result.sha256, "b7d6842ac517fbf45d4e4f63299f88e5c0b2d3f8ee1f164a04019e10244ffbee");
  assert.ok(!Object.values(result).includes(payload));
});

test("origin inventory remains metadata-only and rejects HTTP and wildcard approval", async () => {
  const inventory = JSON.parse(await readFile(path.join(root, "provider/observed-origins.json"), "utf8"));
  assert.equal(inventory.httpRequestsObserved, false);
  assert.equal(inventory.mixedContentObserved, false);
  assert.equal(inventory.wildcardHostsNecessary, false);
  assert.deepEqual(inventory.nestedFrameOrigins, ["https://s.tradingview.com"]);
  for (const origin of inventory.additionalObservedHttpsOrigins) {
    const url = new URL(origin);
    assert.equal(url.protocol, "https:");
    assert.ok(!url.hostname.includes("*"));
    assert.equal(url.origin, origin);
  }
});

test("Nginx serves extensionless canonical documents as HTML without dropping inherited headers", async () => {
  const nginx = await readFile(path.join(root, "nginx.conf"), "utf8");
  assert.match(nginx, /location ~ \^\/chart[\s\S]*?default_type text\/html;[\s\S]*?try_files \$uri =404;/);
  assert.match(nginx, /include \/run\/pepe\/embedded-chart-security\/wrapper-security\.conf;/);
  assert.doesNotMatch(nginx, /location ~ \^\/chart[\s\S]*?add_header Cache-Control/);
});
