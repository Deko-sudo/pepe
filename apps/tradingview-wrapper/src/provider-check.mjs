import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import https from "node:https";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const metadataPath = path.join(root, "provider", "tradingview-script.json");
const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);
const REQUIRED_METADATA_KEYS = [
  "accessDate",
  "lastValidationDate",
  "notes",
  "observedFinalUrl",
  "observedSha256",
  "officialDocumentationTitle",
  "officialDocumentationUrl",
  "officialUrl",
  "retrievalResult",
  "status",
];
const MAX_RESPONSE_BYTES = 10 * 1024 * 1024;

function metadataError(message) {
  return new Error(`Invalid provider metadata: ${message}`);
}

function requireHttpsUrl(value, field) {
  if (typeof value !== "string" || value.length === 0) throw metadataError(`${field} must be a non-empty string`);

  let url;
  try {
    url = new URL(value);
  } catch {
    throw metadataError(`${field} must be an absolute URL`);
  }
  if (url.protocol !== "https:" || url.username || url.password || url.hash || url.href !== value) {
    throw metadataError(`${field} must be a canonical credential-free HTTPS URL without a fragment`);
  }
  return url;
}

function requireDate(value, field) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw metadataError(`${field} must use YYYY-MM-DD`);
  const date = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== value) throw metadataError(`${field} must be a calendar date`);
}

export function validateMetadata(metadata) {
  if (metadata === null || typeof metadata !== "object" || Array.isArray(metadata)) throw metadataError("must be an object");
  const keys = Object.keys(metadata).sort();
  if (keys.length !== REQUIRED_METADATA_KEYS.length || keys.some((key, index) => key !== REQUIRED_METADATA_KEYS[index])) {
    throw metadataError("has an unexpected schema");
  }

  requireHttpsUrl(metadata.officialUrl, "officialUrl");
  requireHttpsUrl(metadata.officialDocumentationUrl, "officialDocumentationUrl");
  requireHttpsUrl(metadata.observedFinalUrl, "observedFinalUrl");
  requireDate(metadata.accessDate, "accessDate");
  requireDate(metadata.lastValidationDate, "lastValidationDate");
  if (!/^[a-f0-9]{64}$/.test(metadata.observedSha256)) throw metadataError("observedSha256 must be a lowercase SHA-256 hex digest");
  if (metadata.status !== "observed-not-pinned") throw metadataError("status must be observed-not-pinned");
  for (const field of ["officialDocumentationTitle", "retrievalResult", "notes"]) {
    if (typeof metadata[field] !== "string" || metadata[field].trim().length === 0) throw metadataError(`${field} must be a non-empty string`);
  }
  return metadata;
}

function validateResponseMetadata(response) {
  if (response === null || typeof response !== "object") throw new Error("Invalid provider response metadata");
  if (!Number.isInteger(response.statusCode) || response.statusCode < 100 || response.statusCode > 599) {
    throw new Error("Invalid provider response status metadata");
  }
  if (response.location !== undefined && typeof response.location !== "string") throw new Error("Invalid provider redirect Location metadata");
  if (!/^[a-f0-9]{64}$/.test(response.sha256)) throw new Error("Invalid provider response SHA-256 metadata");
  if (!Number.isSafeInteger(response.byteLength) || response.byteLength < 0) throw new Error("Invalid provider response byte-length metadata");
}

export function fetchExact(url, { httpsClient = https } = {}) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const settle = (callback, value) => {
      if (settled) return;
      settled = true;
      callback(value);
    };
    const request = httpsClient.get(url, { headers: { "User-Agent": "pepe-wrapper-provider-check/1" } }, (response) => {
      const hash = createHash("sha256");
      let byteLength = 0;
      response.on("data", (chunk) => {
        const data = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
        byteLength += data.length;
        if (byteLength > MAX_RESPONSE_BYTES) {
          request.destroy(new Error("Provider response exceeds maximum allowed size"));
          return;
        }
        hash.update(data);
      });
      response.on("error", (error) => settle(reject, error));
      response.on("end", () => settle(resolve, {
        statusCode: response.statusCode ?? 0,
        location: response.headers.location,
        sha256: hash.digest("hex"),
        byteLength,
      }));
    });
    request.setTimeout(30_000, () => request.destroy(new Error("Provider check timed out")));
    request.on("error", (error) => settle(reject, error));
  });
}

export async function runProviderCheck({ metadata, fetchResponse = fetchExact, log = console.log, error = console.error } = {}) {
  validateMetadata(metadata);
  let currentUrl = metadata.officialUrl;
  for (let redirects = 0; ; redirects += 1) {
    const response = await fetchResponse(currentUrl);
    validateResponseMetadata(response);
    if (REDIRECT_STATUSES.has(response.statusCode)) {
      if (redirects >= 3) throw new Error("Provider redirect limit exceeded");
      if (!response.location) throw new Error("Provider redirect has no Location header");
      const next = new URL(response.location, currentUrl);
      if (next.protocol !== "https:" || next.username || next.password) throw new Error(`Rejected non-HTTPS redirect: ${next.href}`);
      currentUrl = next.href;
      continue;
    }
    if (response.statusCode !== 200) throw new Error(`Unexpected provider status: ${response.statusCode}`);
    const hash = response.sha256;
    log(`final-url=${currentUrl}`);
    log(`sha256=${hash}`);
    if (currentUrl !== metadata.observedFinalUrl || hash !== metadata.observedSha256) {
      error("CHANGED: committed observed script metadata must be explicitly reviewed and subresources revalidated.");
      return false;
    }
    log("UNCHANGED: observed script hash matches committed W2 evidence.");
    return true;
  }
}

async function main() {
  const metadata = JSON.parse(await readFile(metadataPath, "utf8"));
  const unchanged = await runProviderCheck({ metadata });
  if (!unchanged) process.exitCode = 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
