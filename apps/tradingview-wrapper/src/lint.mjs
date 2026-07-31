import { routes, intervals, lifecycleEvents } from "./config.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bootstrap = await readFile(path.join(root, "public/assets/bootstrap.js"), "utf8");
const packageJson = JSON.parse(await readFile(path.join(root, "package.json"), "utf8"));
if (Object.keys(routes).length !== 3 || Object.keys(intervals).length !== 6) throw new Error("Canonical route set is incomplete");
if (lifecycleEvents.includes("provider-ready")) throw new Error("Provider-ready must not exist in W2");
for (const forbidden of [
  /localStorage/, /sessionStorage/, /document\.cookie/, /Authorization/, /initData/,
  /addEventListener\s*\(\s*["']message["']/, /\bonmessage\s*=/,
]) {
  if (forbidden.test(bootstrap)) throw new Error(`Forbidden wrapper behavior: ${forbidden}`);
}
if (Object.keys(packageJson.dependencies ?? {}).length !== 0) throw new Error("Wrapper must have zero production dependencies");
console.log("Static security contract checks passed.");
