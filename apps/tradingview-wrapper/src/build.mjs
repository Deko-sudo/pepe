import { mkdir, rm, writeFile, cp } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { canonicalPath, intervals, routeConfig, routes } from "./config.mjs";
import { invalidDocument, pageDocument } from "./template.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(path.join(root, "public"), dist, { recursive: true });
await writeFile(path.join(dist, "invalid.html"), invalidDocument());
await writeFile(path.join(dist, "health"), "ok\n");

for (const slug of Object.keys(routes)) {
  for (const timeframe of Object.keys(intervals)) {
    const output = path.join(dist, canonicalPath(slug, timeframe));
    await mkdir(path.dirname(output), { recursive: true });
    await writeFile(output, pageDocument(routeConfig(slug, timeframe)));
  }
}

console.log(`Built ${Object.keys(routes).length * Object.keys(intervals).length} canonical wrapper routes.`);
