import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { HARNESS_ORIGIN, WRAPPER_ORIGIN } from "./config.mjs";

export const WRAPPER_CSP = [
  "default-src 'none'",
  "base-uri 'none'",
  "object-src 'none'",
  "form-action 'none'",
  `frame-ancestors ${HARNESS_ORIGIN}`,
  "script-src 'self' https://s3.tradingview.com",
  "style-src 'self'",
  "img-src 'self'",
  "frame-src https://s.tradingview.com",
  "connect-src 'none'",
  "font-src 'none'",
  "media-src 'none'",
  "worker-src 'none'",
  "manifest-src 'none'",
].join("; ");

const securityHeaders = Object.freeze({
  "Content-Security-Policy": WRAPPER_CSP,
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), clipboard-read=(), clipboard-write=(), payment=(), fullscreen=()",
  "X-Robots-Tag": "noindex, nofollow, noarchive",
  "Cross-Origin-Resource-Policy": "same-origin",
});

const harnessHeaders = Object.freeze({
  ...securityHeaders,
  "Content-Security-Policy": [
    "default-src 'none'",
    "base-uri 'none'",
    "object-src 'none'",
    "form-action 'none'",
    "script-src 'self'",
    "style-src 'none'",
    "img-src 'none'",
    `frame-src ${WRAPPER_ORIGIN}`,
    "connect-src 'none'",
  ].join("; "),
});

function contentType(file) {
  if (file.endsWith(`${path.sep}health`)) return "text/plain; charset=utf-8";
  if (file.endsWith(".html") || !path.extname(file)) return "text/html; charset=utf-8";
  if (file.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (file.endsWith(".css")) return "text/css; charset=utf-8";
  return "application/octet-stream";
}

export function createStaticServer({ root, port, harness = false }) {
  return createServer(async (request, response) => {
    const rawPath = request.url?.split("?")[0] ?? "/";
    let target;
    if (harness) {
      target = rawPath === "/" ? "harness/index.html" : rawPath.replace(/^\//, "");
    } else if (rawPath === "/health") {
      target = "health";
    } else if (rawPath.includes("%") || rawPath.includes("..")) {
      target = "invalid.html";
    } else {
      target = rawPath.replace(/^\//, "") || "invalid.html";
    }
    const file = path.resolve(root, target);
    if (!file.startsWith(`${root}${path.sep}`) || !(await stat(file).catch(() => null))?.isFile()) {
      response.writeHead(404, { ...(harness ? harnessHeaders : securityHeaders), "Cache-Control": "no-store", "Content-Type": "text/html; charset=utf-8" });
      createReadStream(path.join(root, "invalid.html")).on("error", () => response.destroy()).pipe(response);
      return;
    }
    const cacheControl = target === "health" || target.endsWith(".html") || !path.extname(target) ? "no-store" : "public, max-age=300";
    response.writeHead(200, { ...(harness ? harnessHeaders : securityHeaders), "Cache-Control": cacheControl, "Content-Type": contentType(file) });
    createReadStream(file).on("error", () => response.destroy()).pipe(response);
  }).listen(port, "127.0.0.1");
}
