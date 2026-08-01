import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const defaultAllowlistPath = path.join(root, "provider", "subresource-allowlist.json");
const resourceClasses = new Set([
  "document", "script", "stylesheet", "image", "font", "media", "xhr", "fetch", "websocket",
]);
const redirectStatuses = new Set([301, 302, 303, 307, 308]);
const forbiddenPayloadFields = new Set(["body", "content", "dom", "html", "responseBody", "text"]);

export class RevalidationError extends Error {
  constructor(message, code = "invalid-record") {
    super(message);
    this.name = "RevalidationError";
    this.code = code;
  }
}

export async function loadAllowlist(allowlistPath = defaultAllowlistPath) {
  const parsed = JSON.parse(await readFile(allowlistPath, "utf8"));
  if (parsed.version !== 1 || !parsed.origins || Array.isArray(parsed.origins)) {
    throw new RevalidationError("Invalid subresource allowlist");
  }

  const origins = new Map();
  for (const [origin, classes] of Object.entries(parsed.origins)) {
    const url = parseNetworkUrl(origin, "allowlist origin");
    if (url.origin !== origin || !Array.isArray(classes) || classes.length === 0) {
      throw new RevalidationError(`Invalid allowlist entry: ${origin}`);
    }
    const approvedClasses = new Set();
    for (const resourceClass of classes) {
      assertResourceClass(resourceClass);
      approvedClasses.add(resourceClass);
    }
    origins.set(origin, approvedClasses);
  }
  return origins;
}

export function redactUrl(value) {
  const url = parseNetworkUrl(value, "subresource URL");
  const queryNames = [...new Set([...url.searchParams.keys()])].sort();
  const query = queryNames.length === 0
    ? ""
    : `?${queryNames.map((name) => `${encodeURIComponent(name)}=%5BREDACTED%5D`).join("&")}`;
  return `${url.origin}${url.pathname}${query}`;
}

export function revalidateSubresources(events, allowlist) {
  if (!Array.isArray(events)) throw new RevalidationError("Revalidation input must be an array");
  if (!(allowlist instanceof Map)) throw new RevalidationError("Allowlist must be loaded before revalidation");

  const records = [];
  const rejections = [];
  for (const event of events) {
    try {
      records.push(normalizeEvent(event, allowlist));
    } catch (error) {
      if (!(error instanceof RevalidationError)) throw error;
      rejections.push({ code: error.code, message: error.message });
    }
  }
  return { approved: rejections.length === 0, records, rejections };
}

function normalizeEvent(event, allowlist) {
  if (!event || typeof event !== "object" || Array.isArray(event)) {
    throw new RevalidationError("Revalidation event must be an object");
  }
  for (const field of Object.keys(event)) {
    if (forbiddenPayloadFields.has(field)) {
      throw new RevalidationError(`Payload field is forbidden: ${field}`, "payload-forbidden");
    }
  }

  switch (event.type) {
    case "resource":
      assertFields(event, ["type", "resourceClass", "url", "status"]);
      assertApproved(event.url, event.resourceClass, allowlist);
      return compact({ type: event.type, resourceClass: event.resourceClass, url: redactUrl(event.url), status: optionalStatus(event.status) });
    case "redirect":
      assertFields(event, ["type", "resourceClass", "fromUrl", "toUrl", "status"]);
      assertApproved(event.fromUrl, event.resourceClass, allowlist);
      assertApproved(event.toUrl, event.resourceClass, allowlist);
      if (!redirectStatuses.has(event.status)) throw new RevalidationError("Redirect status must be 301, 302, 303, 307, or 308");
      return { type: event.type, resourceClass: event.resourceClass, fromUrl: redactUrl(event.fromUrl), toUrl: redactUrl(event.toUrl), status: event.status };
    case "blocked":
      assertFields(event, ["type", "resourceClass", "url", "reason"]);
      assertApproved(event.url, event.resourceClass, allowlist);
      assertString(event.reason, "Blocked reason");
      return { type: event.type, resourceClass: event.resourceClass, url: redactUrl(event.url), reason: event.reason };
    case "csp-violation":
      assertFields(event, ["type", "resourceClass", "blockedUrl", "effectiveDirective", "disposition"]);
      assertApproved(event.blockedUrl, event.resourceClass, allowlist);
      assertString(event.effectiveDirective, "CSP directive");
      if (event.disposition !== "enforce" && event.disposition !== "report") throw new RevalidationError("CSP disposition must be enforce or report");
      return compact({ type: event.type, resourceClass: event.resourceClass, blockedUrl: redactUrl(event.blockedUrl), effectiveDirective: event.effectiveDirective, disposition: event.disposition });
    default:
      throw new RevalidationError(`Unknown revalidation event type: ${String(event.type)}`, "unknown-event");
  }
}

function assertFields(event, allowed) {
  for (const field of Object.keys(event)) {
    if (!allowed.includes(field)) throw new RevalidationError(`Unexpected metadata field: ${field}`);
  }
  for (const field of allowed.slice(0, 3)) {
    if (!(field in event)) throw new RevalidationError(`Missing metadata field: ${field}`);
  }
}

function assertApproved(value, resourceClass, allowlist) {
  assertResourceClass(resourceClass);
  const url = parseNetworkUrl(value, "subresource URL");
  if (!allowlist.get(url.origin)?.has(resourceClass)) {
    throw new RevalidationError(`Unapproved origin/resource class: ${url.origin} ${resourceClass}`, "unapproved-subresource");
  }
}

function assertResourceClass(resourceClass) {
  if (!resourceClasses.has(resourceClass)) throw new RevalidationError(`Unknown resource class: ${String(resourceClass)}`, "unknown-resource-class");
}

function parseNetworkUrl(value, label) {
  if (typeof value !== "string") throw new RevalidationError(`${label} must be a URL string`);
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new RevalidationError(`${label} is invalid`);
  }
  if (!["https:", "wss:"].includes(url.protocol) || url.username || url.password) {
    throw new RevalidationError(`${label} must be credential-free HTTPS or WSS`, "unsafe-url");
  }
  return url;
}

function optionalStatus(status) {
  if (status === undefined) return undefined;
  if (!Number.isInteger(status) || status < 0 || status > 599) throw new RevalidationError("Status must be an integer from 0 to 599");
  return status;
}

function assertString(value, label) {
  if (typeof value !== "string" || value.length === 0) throw new RevalidationError(`${label} must be a non-empty string`);
}

function compact(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined));
}

async function main() {
  const inputPath = process.argv[2];
  if (!inputPath) throw new RevalidationError("Usage: node src/subresource-revalidation.mjs <captured-metadata.json>");
  const events = JSON.parse(await readFile(path.resolve(process.cwd(), inputPath), "utf8"));
  const result = revalidateSubresources(events, await loadAllowlist());
  process.stdout.write(`${JSON.stringify(result)}\n`);
  if (!result.approved) process.exitCode = 1;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
