import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import https from "node:https";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const metadataPath = path.join(root, "provider", "tradingview-script.json");
const metadata = JSON.parse(await readFile(metadataPath, "utf8"));

function fetchExact(url) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, { headers: { "User-Agent": "pepe-wrapper-provider-check/1" } }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => resolve({
        statusCode: response.statusCode ?? 0,
        location: response.headers.location,
        body: Buffer.concat(chunks),
      }));
    });
    request.setTimeout(30_000, () => request.destroy(new Error("Provider check timed out")));
    request.on("error", reject);
  });
}

let currentUrl = metadata.officialUrl;
for (let redirects = 0; redirects <= 3; redirects += 1) {
  const response = await fetchExact(currentUrl);
  if ([301, 302, 303, 307, 308].includes(response.statusCode)) {
    const next = new URL(response.location ?? "", currentUrl);
    if (next.protocol !== "https:") throw new Error(`Rejected non-HTTPS redirect: ${next.href}`);
    currentUrl = next.href;
    continue;
  }
  if (response.statusCode !== 200) throw new Error(`Unexpected provider status: ${response.statusCode}`);
  const hash = createHash("sha256").update(response.body).digest("hex");
  console.log(`final-url=${currentUrl}`);
  console.log(`sha256=${hash}`);
  if (currentUrl !== metadata.observedFinalUrl || hash !== metadata.observedSha256) {
    console.error("CHANGED: committed observed script metadata must be explicitly reviewed and subresources revalidated.");
    process.exitCode = 1;
  } else {
    console.log("UNCHANGED: observed script hash matches committed W2 evidence.");
  }
  break;
}
